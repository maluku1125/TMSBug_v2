import asyncio
import datetime


def _now():
    return datetime.datetime.now().strftime('%H:%M:%S')


async def broadcast_to_channels(bot, targets, make_payload, concurrency=20, retry=True, retry_delay=2):
    """並發廣播訊息到多個頻道。

    targets: [(guild_id, channel_id), ...]
    make_payload: callable(guild_id, channel_id) -> dict，展開傳給 channel.send(**kwargs)
    concurrency: 同時發送上限（discord.py 內建全域限速 50req/s，20 併發留有餘裕）
    retry: 發送失敗時延遲 retry_delay 秒後重試一次

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

    if not targets:
        return 0, []

    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[send_one(g, c) for g, c in targets])
    elapsed = asyncio.get_event_loop().time() - start

    failures = [r for r in results if r[2] is not None]
    success = len(results) - len(failures)
    print(f"{_now()}, broadcast: {success} sent, {len(failures)} failed, {len(targets)} total in {elapsed:.1f}s")
    return success, failures
