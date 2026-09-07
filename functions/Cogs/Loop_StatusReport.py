"""
Loop_StatusReport —— 每 30 秒把 Bot 的內部狀態寫成一個 JSON 檔，供後台讀取。

## 為什麼是「寫檔」而不是「開端點」或「主動推送」

1. **不在 Bot 的 event loop 上再加一個 HTTP server。** 這個 loop 的敏感度
   已經被證明過（heartbeat blocked 那一串事故），能不加就不加。
2. **推送失敗是靜音的，檔案變舊是會說話的。** 如果 loop 被卡住 —— 正是這支
   要偵測的失效模式 —— 主動推送只是沒送出去，後台什麼也看不到；而檔案的
   `reported_at` 會停在原地，後台就能顯示「最後回報 3 分鐘前 ⚠」。
3. server.py 重啟、Bot 重啟，兩邊互不影響，沒有連線狀態要管。

## 這裡面最有價值的兩個欄位

* `loop_drift` —— 自己量的 event loop 落後秒數。`tasks.loop(seconds=30)`
  實際隔了 42 秒，就表示有東西把 loop 佔住了 12 秒。這比 `bot.latency`
  誠實：延遲高可能是網路，drift 高一定是自己的問題。
* `warnings` —— 攔 discord.py 自己發的 WARNING（含 heartbeat blocked）。
  以前這些只會滑過主控台，沒盯著就錯過了。

## 兩個檔案

* `status/<專案>.json` —— **當下狀態**，每 30 秒整個覆蓋
* `status/events_<專案>.jsonl` —— **事件歷史**，一行一筆，永久累積

分開的理由：狀態檔要能被無腦覆蓋（後台只關心最新一份），
事件則必須留著 —— 「昨天半夜 shard 2 斷過三次」這種問題，
快照答不出來。一天大概數十行，一年也才幾 MB。

事件來源有三個：Bot 啟動、`discord` logger（gateway 斷線／RESUMED／
heartbeat blocked）、以及 `Loop_ServerCheck` 的 online↔offline 轉換。

## 成本

一次約 1-2KB 的檔案寫入，丟到執行緒去做，不佔 loop。`SaveSystemStats`
每 30 分鐘才寫一列 DB（每 30 秒寫的話一年就 100 萬列，不值得）。
"""

import asyncio
import collections
import datetime
import json
import logging
import os
import re
import time

import psutil
from discord.ext import commands, tasks

from ..SlashCommandManager import SaveSystemStats
from .Loop_ServerCheck import DOWN_ROUNDS

# 與 Loop_ServerAnnounce 相同的做法：檔名帶專案名，讓 v2 與 beta 各自獨立
_STATUS_DIR = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\status'
_PROJECT_NAME = os.path.basename(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
_STATUS_PATH = os.path.join(_STATUS_DIR, f'{_PROJECT_NAME}.json')
_EVENTS_PATH = os.path.join(_STATUS_DIR, f'events_{_PROJECT_NAME}.jsonl')

REPORT_SECONDS = 30
SYSTEM_STATS_EVERY = 60          # 60 × 30 秒 = 30 分鐘寫一列 system_stats
WARNING_KEEP = 30

# discord.py 在 INFO 等級記連線生命週期（斷線、RESUMED、IDENTIFY），
# WARNING 才記 heartbeat blocked。想看「有沒有斷過」就得收到 INFO ——
# 但這不會讓主控台變吵：SlashCommandManager 已經 basicConfig(INFO)，
# 這些訊息本來就在印，這裡只是多攔一份存起來。
_EVENT_RE = re.compile(
    r'RESUMED|connected to Gateway|IDENTIFY|RECONNECT|reconnect'
    r'|disconnect|closed|heartbeat|stopped responding|rate limit',
    re.I)
_SHARD_RE = re.compile(r'Shard ID (\d+)')

_warnings = collections.deque(maxlen=WARNING_KEEP)
_pending = collections.deque(maxlen=500)     # 待寫入的事件，由迴圈批次落地
_handler_installed = False


def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')


class _EventCollector(logging.Handler):
    """收 discord.py 的警告與連線生命週期事件。

    **不在這裡寫檔。** emit 會在任意執行緒（含 event loop）被呼叫，
    寫檔是阻塞 syscall；改成丟進佇列，由 30 秒的迴圈批次落地。
    """

    def emit(self, record):
        try:
            msg = record.getMessage()
            warn = record.levelno >= logging.WARNING
            if not warn and not _EVENT_RE.search(msg):
                return
            m = _SHARD_RE.search(msg)
            ev = {
                'at': datetime.datetime.fromtimestamp(
                    record.created).strftime('%Y-%m-%d %H:%M:%S'),
                'kind': 'warning' if warn else 'gateway',
                'level': record.levelname,
                'shard': int(m.group(1)) if m else None,
                'text': msg[:300],
            }
            _pending.append(ev)
            if warn:
                _warnings.append(ev)
        except Exception:            # 蒐集狀態失敗絕不能影響 Bot 本身
            pass


def _install_handler():
    global _handler_installed
    if _handler_installed:
        return
    h = _EventCollector()
    h.setLevel(logging.INFO)
    logging.getLogger('discord').addHandler(h)
    _handler_installed = True


def _write_both(payload: dict, events: list):
    """一次執行緒切換做完兩件事。"""
    _write_atomic(payload)
    _flush_events(events)


def _write_atomic(payload: dict):
    """先寫暫存檔再 os.replace —— 後台永遠讀到完整的 JSON，不會讀到寫到一半的。"""
    os.makedirs(_STATUS_DIR, exist_ok=True)
    tmp = _STATUS_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, _STATUS_PATH)


def _flush_events(events: list):
    """附加寫入 JSONL。單純 append，不必原子操作 —— 讀取端會跳過壞行。"""
    if not events:
        return
    os.makedirs(_STATUS_DIR, exist_ok=True)
    with open(_EVENTS_PATH, 'a', encoding='utf-8') as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + '\n')


def _event(kind, text, **extra):
    _pending.append(dict(
        at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        kind=kind, text=text, **extra))


class Loop_StatusReport(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.proc = psutil.Process()
        self.started_at = datetime.datetime.now()
        self.started_mono = time.monotonic()
        self.last_mono = None
        self.max_drift = 0.0
        self.ticks = 0
        self.prev_server = None      # 上一輪的 servercheck 結論，用來偵測轉換
        _install_handler()
        self.report.start()

    def cog_unload(self):
        self.report.cancel()

    @tasks.loop(seconds=REPORT_SECONDS)
    async def report(self):
        # tasks.loop 遇未捕捉例外會停止，整段保護以確保回報不會默默斷掉
        try:
            now_mono = time.monotonic()
            drift = 0.0
            if self.last_mono is not None:
                # 只有「慢了」才有意義；提早觸發是排程抖動，夾成 0
                drift = max(0.0, (now_mono - self.last_mono) - REPORT_SECONDS)
                self.max_drift = max(self.max_drift, drift)
            self.last_mono = now_mono
            self.ticks += 1

            c = self.client
            guilds = list(c.guilds)
            lat = c.latency                 # 未連線時是 NaN，NaN != NaN
            payload = {
                'project': _PROJECT_NAME,
                'pid': os.getpid(),
                'started_at': self.started_at.isoformat(timespec='seconds'),
                'reported_at': datetime.datetime.now().isoformat(timespec='seconds'),
                'uptime_sec': int(now_mono - self.started_mono),
                'ready': c.is_ready(),
                'closed': c.is_closed(),
                'latency_ms': round(lat * 1000) if lat == lat else None,
                'shards': [{'id': i, 'latency_ms': round(l * 1000)}
                           for i, l in (c.latencies or ())
                           if l == l],
                'shard_count': c.shard_count,
                'guilds': len(guilds),
                'users': sum(g.member_count or 0 for g in guilds
                             if not g.unavailable),
                'cogs': sorted(c.cogs),
                'commands': len(c.tree.get_commands()),
                'loop_drift': round(drift, 2),
                'loop_drift_max': round(self.max_drift, 2),
                'memory_mb': round(self.proc.memory_info().rss / 1048576, 1),
                'threads': self.proc.num_threads(),
                'warnings': list(_warnings),
                'report_interval': REPORT_SECONDS,
            }

            payload['servercheck'] = self._servercheck()

            if self.ticks == 1:
                _event('start', f'Bot 啟動（{len(guilds)} 個伺服器，'
                                f'{c.shard_count or 1} shard）')

            # 事件先湊齊再一起寫，兩個檔案在同一個執行緒切換裡完成
            batch = list(_pending)
            _pending.clear()
            await asyncio.to_thread(_write_both, payload, batch)

            # 公會／使用者數的長期曲線。原本只有跑 dashboard 指令時才寫一筆，
            # 所以 11 個月只有 51 列 —— 這裡補上週期性寫入。
            if self.ticks % SYSTEM_STATS_EVERY == 1:
                await asyncio.to_thread(SaveSystemStats,
                                        payload['guilds'], payload['users'])
        except Exception as e:                              # noqa: BLE001
            print(f'{get_now_HMS()}, StatusReport: {type(e).__name__}: {e}')

    def _servercheck(self) -> dict:
        """把 Loop_ServerCheck 的現況抄一份出來。

        全部走 getattr —— 那支 cog 沒載入、或欄位改名時，狀態回報不該跟著死。
        順便偵測 online↔offline 轉換並記成事件（在這裡做，就不必動到
        原本的通知流程）。
        """
        sc = self.client.get_cog('Loop_ServerCheck')
        if sc is None:
            return {'available': False}

        hosts = dict(getattr(sc, 'ret', None) or {})
        at = getattr(sc, 'last_check_at', None)
        verdict = getattr(sc, 'last_verdict', None)
        out = {
            'available': True,
            'status': getattr(sc, 'server_status', '') or None,
            'hosts': hosts,
            'online': sum(1 for v in hosts.values() if v == 'online'),
            'total': len(hosts),
            'down_rounds': getattr(sc, 'down_rounds', 0),
            'down_rounds_max': DOWN_ROUNDS,
            'verdict': verdict,
            'congested': getattr(sc, 'last_congested', None),
            'pressure': list(getattr(sc, 'last_pressure', None) or ()),
            'last_check_at': at.strftime('%Y-%m-%d %H:%M:%S') if at else None,
        }

        # 狀態轉換 → 事件。壅塞期間的結論不採信，也就不記。
        if verdict in ('online', 'offline'):
            if self.prev_server is not None and verdict != self.prev_server:
                _event('server',
                       f'登入口 {self.prev_server} → {verdict}'
                       f'（{out["online"]}/{out["total"]} 台可連）',
                       level='INFO')
            self.prev_server = verdict
        return out

    @report.before_loop
    async def before_report(self):
        await self.client.wait_until_ready()
