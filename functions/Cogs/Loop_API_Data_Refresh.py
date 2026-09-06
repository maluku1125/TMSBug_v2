import configparser
import datetime
import asyncio
import os
import sqlite3
from discord.ext import commands, tasks
from tmsapi.request import refresh_all_expired_character_data
from tmsapi.store.character import character_basic_info_path

# ── 管線獨立的切換旗標（ARCHITECTURE.md §14.9）──────────────
#
# 刷新管線已搬到 TMSAnalysis/pipeline/ + server.py。這個旗標決定「誰來跑」：
#
#     true  （預設）Bot 自己跑，行為與過去完全相同
#     false          Bot 不跑，交給 TMSAnalysis/server.py 的排程
#
# 切換是可逆的：改回 true 重啟 Bot 就回到原狀，資料庫一個 byte 都不用動。
# ⚠️ 改成 false 之前，請先確認 server.py 已經在跑，否則沒有任何東西會刷新。

_CONFIG = os.environ.get(
    'TMSBOT_CONFIG', r'C:\Users\User\Desktop\DiscordBot\Config\TMSBug_v2_config.ini')


def _refresh_enabled() -> bool:
    try:
        c = configparser.ConfigParser()
        c.read(_CONFIG, encoding='utf-8')
        return c.getboolean('api', 'enable_refresh_loop', fallback=True)
    except Exception:                      # noqa: BLE001 —— 讀不到就維持原行為
        return True

# ── 管線獨立的切換旗標（ARCHITECTURE.md §14.9）──────────────
#
# 刷新管線已搬到 TMSAnalysis/pipeline/ + server.py。這個旗標決定「誰來跑」：
#
#     true  （預設）Bot 自己跑，行為與過去完全相同
#     false          Bot 不跑，交給 TMSAnalysis/server.py 的排程
#
# 切換是可逆的：改回 true 重啟 Bot 就回到原狀，資料庫一個 byte 都不用動。
# ⚠️ 改成 false 之前，請先確認 server.py 已經在跑，否則沒有任何東西會刷新。

_CONFIG = os.environ.get(
    'TMSBOT_CONFIG', r'C:\Users\User\Desktop\DiscordBot\Config\TMSBug_v2_config.ini')


def _refresh_enabled() -> bool:
    try:
        c = configparser.ConfigParser()
        c.read(_CONFIG, encoding='utf-8')
        return c.getboolean('api', 'enable_refresh_loop', fallback=True)
    except Exception:                      # noqa: BLE001 —— 讀不到就維持原行為
        return True

# 幾天輪完全部角色（每日刷新 1/N）
REFRESH_CYCLE_DAYS = 7

# bot 內刷新的 API 速率上限（官方 500/s）。刻意低於 admin 腳本的 350，
# 讓 bot 保留餘裕回應指令；若同時手動跑腳本，兩邊相加也不會超過上限。
REFRESH_RATE = 150


def get_character_count() -> int:
    """角色總數，用來換算每日配額"""
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            return conn.execute('SELECT COUNT(*) FROM character_basic_info').fetchone()[0]
    except Exception as e:
        print(f"取得角色總數失敗: {e}")
        return 0

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def get_now_YMDHMS():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

timezone = datetime.timezone(datetime.timedelta(hours=8))


class Loop_API_Data_Refresh(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = _refresh_enabled()
        if not self.enabled:
            print(f"{get_now_YMDHMS()}, Data Refresh Loop 已停用"
                  f"（enable_refresh_loop=false，由 TMSAnalysis/server.py 負責）")
            return
        print(f"{get_now_YMDHMS()}, Data Refresh Loop initializing...")
        self.API_AllData_Refresh.start()

    def cog_unload(self):
        if not getattr(self, 'enabled', True):
            return
        self.API_AllData_Refresh.cancel()
        print(f"{get_now_YMDHMS()}, API Data Refresh Loop stopped")
    
    # Official use - Execute at specific time daily
    @tasks.loop(time=datetime.time(hour=2, minute=15, tzinfo=timezone))  # Set to 2:15 for testing

    async def API_AllData_Refresh(self):
        """每日 02:15 執行：刷新「最舊的 1/REFRESH_CYCLE_DAYS」筆資料。

        舊版是「刷新所有超過 7 天者」，同一天刷到的角色 7 天後又同一天到期，
        造成群聚（實測單日 46k、隔日 1.7k）。改為每日固定取最舊的 N 筆後，
        負載自動均分，且族群成長時 N 會跟著調整。
        """
        print(f"{get_now_YMDHMS()}, 🚀 Starting API daily rolling refresh...")

        try:
            total = await asyncio.to_thread(get_character_count)
            daily_quota = max(1, -(-total // REFRESH_CYCLE_DAYS)) if total else None  # 無條件進位
            if daily_quota:
                print(f"{get_now_YMDHMS()}, 總計 {total:,} 筆，"
                      f"本次配額 {daily_quota:,} 筆（{REFRESH_CYCLE_DAYS} 天輪完一輪）")

            # 刷新期間關閉逐筆 print：主控台輸出是同步 I/O，數萬筆會癱瘓 event loop
            # （實測會出現 discord.gateway "heartbeat blocked for more than N seconds"）
            import tmsapi.request as _rc
            from tmsapi.ratelimit import set_global_rate
            _prev_quiet = _rc.QUIET
            _rc.QUIET = True
            set_global_rate(REFRESH_RATE)
            try:
                # Execute refresh task in a separate thread to avoid blocking the event loop
                stats = await asyncio.to_thread(
                    refresh_all_expired_character_data,
                    refresh_days=REFRESH_CYCLE_DAYS,
                    max_count=daily_quota,
                )
            finally:
                _rc.QUIET = _prev_quiet

            # Output statistics
            print(f"{get_now_YMDHMS()}, 🎉 API all data refresh completed!")
            print(f"Total records: {stats['total_records']}")
            print(f"Fresh records: {stats['fresh_records']}")
            print(f"Expired records: {stats['expired_records']}")
            print(f"Successfully refreshed: {stats['successfully_refreshed']}")
            print(f"Failed refreshes: {stats['failed_refreshes']}")
            print(f"Deleted invalid records: {stats['deleted_invalid_records']}")
            print(f"Error records: {stats['error_records']}")
            print("-" * 50)
            
        except Exception as e:
            print(f"{get_now_YMDHMS()}, 💥 Error during API all data refresh: {e}")
            import traceback
            traceback.print_exc()
            print("-" * 50)

