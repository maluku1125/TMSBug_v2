"""並發廣播，以及它的紀錄。

## 為什麼紀錄寫在這裡，不寫在三個呼叫點

群發總共有三處：登入口開啟、登入口關閉、官網公告。三個地方各抄一份
寫檔的程式，遲早會有一處忘了改（或漏了失敗原因）。它們都會經過
`broadcast_to_channels`，所以在這裡收一次就好。

## 為什麼是 JSONL 而不是資料庫

一天大概三五行，一年也才幾千行。要的是「上次公告發給幾個頻道、失敗幾個、
為什麼失敗」—— 這種只往後追加、只讀尾巴的東西，JSONL 比開一張表省事，
而且 Bot 掛了也不會鎖住檔案。

檔名帶專案名，v2 與 beta 各自一份（跟 status 回報、公告 seen 檔同一個做法）。
"""

import asyncio
import datetime
import json
import os

# 與 Loop_ServerAnnounce／Loop_StatusReport 一致：紀錄放專案外的 log 目錄
_LOG_DIR = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function'
_PROJECT_NAME = os.path.basename(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_PATH = os.path.join(_LOG_DIR, f'broadcast_{_PROJECT_NAME}.jsonl')


def _now():
    return datetime.datetime.now().strftime('%H:%M:%S')


def _reason(err):
    """失敗原因正規化成一個短字串。

    ConcurrentBroadcast 自己回的是 'channel_not_found' / 'no_permission'
    這種字串，discord.py 丟出來的則是例外物件 —— 統計時要能混在一起數。
    """
    if isinstance(err, str):
        return err
    return type(err).__name__


def _write_log(row: dict):
    """附加一行。寫檔失敗絕不能影響群發本身 —— 訊息已經送出去了。"""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        with open(_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except Exception:
        pass


async def broadcast_to_channels(bot, targets, make_payload, concurrency=20,
                                retry=True, retry_delay=2,
                                kind=None, label=None):
    """並發廣播訊息到多個頻道。

    targets: [(guild_id, channel_id), ...]
    make_payload: callable(guild_id, channel_id) -> dict，展開傳給 channel.send(**kwargs)
    concurrency: 同時發送上限（discord.py 內建全域限速 50req/s，20 併發留有餘裕）
    retry: 發送失敗時延遲 retry_delay 秒後重試一次
    kind/label: 寫進紀錄用的識別（例如 'servercheck_up' / '登入口已開啟'）

    回傳 (success_count, failures)
    failures = [(guild_id, channel_id, reason), ...]
    reason 為 'channel_not_found' / 'no_permission' / Exception
    """
    sem = asyncio.Semaphore(concurrency)

    async def send_one(guild_id, channel_id):
        async with sem:
            channel = bot.get_channel(channel_id)
            if channel is None:
                return (guild_id, channel_id, 'channel_not_found')
            try:
                if not channel.permissions_for(channel.guild.me).send_messages:
                    return (guild_id, channel_id, 'no_permission')
            except Exception:
                pass  # 非一般文字頻道沒有 permissions_for，直接嘗試發送
            try:
                await channel.send(**make_payload(guild_id, channel_id))
                return (guild_id, channel_id, None)
            except Exception as e:
                if not retry:
                    return (guild_id, channel_id, e)
                await asyncio.sleep(retry_delay)
                try:
                    await channel.send(**make_payload(guild_id, channel_id))
                    return (guild_id, channel_id, None)
                except Exception as e2:
                    return (guild_id, channel_id, e2)

    at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 沒有目標也要記一筆：「公告觸發了但一個訂閱者都沒有」跟「沒觸發」
    # 是兩件事，只看有沒有紀錄分不出來
    if not targets:
        await asyncio.to_thread(_write_log, {
            'at': at, 'kind': kind, 'label': label,
            'targets': 0, 'success': 0, 'failed': 0,
            'elapsed': 0.0, 'reasons': {}})
        return 0, []

    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[send_one(g, c) for g, c in targets])
    elapsed = asyncio.get_event_loop().time() - start

    failures = [r for r in results if r[2] is not None]
    success = len(results) - len(failures)
    print(f"{_now()}, broadcast: {success} sent, {len(failures)} failed, {len(targets)} total in {elapsed:.1f}s")

    reasons = {}
    for _g, _c, err in failures:
        r = _reason(err)
        reasons[r] = reasons.get(r, 0) + 1
    # 丟到執行緒寫檔：這裡還在 event loop 上，而 loop 的敏感度是這個專案
    # 付過學費的（heartbeat blocked 那一串）
    await asyncio.to_thread(_write_log, {
        'at': at, 'kind': kind, 'label': label,
        'targets': len(targets), 'success': success, 'failed': len(failures),
        'elapsed': round(elapsed, 2), 'reasons': reasons})

    return success, failures
