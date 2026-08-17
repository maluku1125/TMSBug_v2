"""
API_RateLimiter.py
==================
Nexon Open API 的全域請求速率控制。

官方上限 500 req/s，此處預設 350 req/s 保留餘裕。
與 Semaphore 的差別：Semaphore 限制「同時在飛的請求數」，
本限制器控制「每秒發出的請求數」——高併發下才是真正的節流點。

注意：限制器是「每個行程」各自獨立。若 bot 與 admin 腳本同時執行，
兩邊會各自跑到 350/s（合計 700/s，超過官方上限）。
同時跑時請調降其中一邊，例如腳本用 --rate 150。
"""

import time
import asyncio

# 預設速率（每秒請求數）。API 官方上限 500，保留餘裕設 350。
DEFAULT_RATE = 350.0


class RateLimiter:
    """非同步速率限制器：確保每秒最多發出 rate 個請求。

    以「下一個可發送時刻」推進，天然平滑（不會出現整秒爆發後靜default）。
    """

    def __init__(self, rate: float = DEFAULT_RATE):
        self.set_rate(rate)
        self._next = 0.0
        self._lock = asyncio.Lock()

    def set_rate(self, rate: float):
        self.rate = max(1.0, float(rate))
        self._interval = 1.0 / self.rate

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            if self._next < now:
                self._next = now
            wait = self._next - now
            self._next += self._interval
        if wait > 0:
            await asyncio.sleep(wait)


# 全域限制器（同一行程內所有 API 請求共用）
_limiter = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(DEFAULT_RATE)
    return _limiter


def set_global_rate(rate: float):
    """調整全域速率（例如 bot 與腳本同時跑時各自降半）"""
    get_limiter().set_rate(rate)


async def acquire():
    """發送 API 請求前呼叫，必要時等待以符合速率上限"""
    await get_limiter().acquire()
