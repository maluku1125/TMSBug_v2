import re
import os
import json
import asyncio
import datetime
import requests
import discord
from discord.ext import commands, tasks
from concurrent.futures import ThreadPoolExecutor

from functions.database_manager import GuildFunctionDB
from functions.ConcurrentBroadcast import broadcast_to_channels

# 命中任一關鍵字即通知（維護公告 涵蓋 臨時維護公告/分段分流維護公告 等）
KEYWORDS = ("維護公告", "開機公告", "關機公告", "手動更新下載開放通知")

TMS_MAIN_URL = "https://maplestory.beanfun.com/main"
TMS_BULLETIN_PROXY_URL = "https://maplestory.beanfun.com/main?handler=BulletinProxy"
TMS_BULLETIN_URL = "https://maplestory.beanfun.com/bulletin?bid={bid}"

CSRF_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')

# 已通知公告 ID 存本專案自己的 Data 目錄（beta/v2 各自獨立，避免互搶）
_SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Data', 'ServerAnnounce_seen.json')
_SEEN_LIMIT = 300  # 保留最近 N 筆，避免無限成長


def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')


def fetch_bulletins():
    """同步抓取官網公告列表（在執行緒中跑）。回傳 list 或 None。"""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    resp = session.get(TMS_MAIN_URL, timeout=15)
    resp.raise_for_status()
    match = CSRF_RE.search(resp.text)
    if not match:
        print(f"{get_now_HMS()}, ServerAnnounce: CSRF token not found")
        return None

    resp2 = session.post(
        TMS_BULLETIN_PROXY_URL,
        data="Kind=0&Page=1&method=0&PageSize=10",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": match.group(1),
        },
        timeout=15,
    )
    resp2.raise_for_status()
    return resp2.json()["data"]["myDataSet"]["table"]


def bulletin_link(item):
    """官方 JS 的組法：有 urlLink 用 urlLink，否則 bulletin?bid={id}"""
    url_link = item.get("urlLink")
    if url_link:
        # urlLink 為官網 href，可能是相對路徑；非 http 開頭時補上官網域名，避免 embed URL 無效
        if not url_link.startswith("http"):
            url_link = "https://maplestory.beanfun.com/" + url_link.lstrip("/")
        return url_link
    return TMS_BULLETIN_URL.format(bid=item.get("bullentinId"))


class Loop_ServerAnnounce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = GuildFunctionDB()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.seen_ids = self._load_seen()
        self.check_announcements.start()

    def cog_unload(self):
        self.check_announcements.cancel()
        self.executor.shutdown(wait=False)

    # ---------- 已通知 ID 持久化 ----------
    def _load_seen(self):
        try:
            with open(_SEEN_PATH, 'r', encoding='utf-8') as f:
                return list(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return None  # None = 首次啟動，之後以當前公告為基準

    def _save_seen(self):
        try:
            with open(_SEEN_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.seen_ids[-_SEEN_LIMIT:], f)
        except Exception as e:
            print(f"{get_now_HMS()}, ServerAnnounce: save seen failed: {e}")

    # ---------- 主迴圈 ----------
    @tasks.loop(minutes=30)
    async def check_announcements(self):
        loop = asyncio.get_event_loop()
        try:
            table = await loop.run_in_executor(self.executor, fetch_bulletins)
        except Exception as e:
            print(f"{get_now_HMS()}, ServerAnnounce: fetch failed: {e}")
            return
        if not table:
            return

        # tasks.loop 遇未捕捉例外會停止，此處整段保護以確保 30 分鐘循環持續運作
        try:
            current_ids = [item.get("bullentinId") for item in table]

            # 首次啟動：以當前公告為基準，不回放舊公告
            if self.seen_ids is None:
                self.seen_ids = current_ids
                self._save_seen()
                print(f"{get_now_HMS()}, ServerAnnounce: baseline set ({len(current_ids)} bulletins)")
                return

            new_items = [
                item for item in table
                if item.get("bullentinId") not in self.seen_ids
                and any(k in (item.get("title") or "") for k in KEYWORDS)
            ]

            # 全部現有 ID 標記為已看（含不符關鍵字的，避免下輪重比）
            self.seen_ids += [i for i in current_ids if i not in self.seen_ids]
            self.seen_ids = self.seen_ids[-_SEEN_LIMIT:]
            self._save_seen()

            if not new_items:
                return

            # 列表由新到舊，發送時反轉成由舊到新
            for item in reversed(new_items):
                await self._broadcast(item)
        except Exception as e:
            print(f"{get_now_HMS()}, ServerAnnounce: cycle error: {e}")

    @check_announcements.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ---------- 發送 ----------
    async def _broadcast(self, item):
        title = item.get("title") or "官方公告"
        link = bulletin_link(item)
        embed = discord.Embed(
            title=f"📢 {title}",
            url=link,
            color=0xff9900,
        )
        embed.set_footer(text="新楓之谷官方公告")

        configs = self.db.get_all_announce_configs()
        targets = list(configs.items())

        # 並發廣播（含每頻道一次重試）
        success, failures = await broadcast_to_channels(
            self.bot, targets, lambda g, c: {'embed': embed}, concurrency=20
        )

        print(f"{get_now_HMS()}, ServerAnnounce: '{title}' sent to {success} channels, {len(failures)} failed")
