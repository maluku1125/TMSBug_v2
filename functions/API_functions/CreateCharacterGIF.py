"""
CreateCharacterGIF.py
=====================
抓取角色外型圖的多張影格並合成透明 GIF。

特性：
  - 透明背景（GIF 1-bit 透明，alpha 門檻 128）
  - 懶快取：第一次產生後存檔，之後直接讀；以 look-code 當 key，換裝自動失效
  - 影格圖來自靜態 CDN（不需 API key、不計 /v1 額度），故不寫 API log
  - 下載用 aiohttp 併發；PIL 合成丟到 thread，不卡事件迴圈
  - 只動 action 影格，emotion / wmotion 固定
"""

import os
import io
import hashlib
import asyncio
import aiohttp
from PIL import Image
from urllib.parse import urlparse

from functions.API_functions.CreateCharacterEmbed import apply_look_params

CACHE_DIR = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\gifcache'

# 各動作的「最大影格 index」（幀數 = index + 1）；0 代表單幀、無法動畫
ACTION_FRAMES = {
    'A00': 2, 'A01': 2, 'A02': 3, 'A03': 3, 'A04': 0, 'A05': 1, 'A06': 0,
    'A07': 0, 'A08': 1, 'A09': 1, 'A10': 2, 'A11': 2, 'A12': 1, 'A13': 2,
    'A14': 2, 'A15': 2, 'A16': 3, 'A17': 2, 'A18': 2, 'A19': 3, 'A20': 2,
    'A21': 2, 'A22': 2, 'A23': 3, 'A24': 1, 'A25': 1, 'A26': 2, 'A27': 2,
    'A28': 2, 'A29': 3, 'A30': 2, 'A31': 4, 'A32': 2, 'A33': 0, 'A34': 3,
    'A35': 2, 'A36': 0, 'A37': 1, 'A38': 1, 'A39': 1, 'A40': 1, 'A41': 0,
}

# 各表情的最大影格 index（v1 不用於動畫，保留供日後擴充）
EMOTION_FRAMES = {
    'E00': 0, 'E01': 0, 'E02': 0, 'E03': 0, 'E04': 0, 'E05': 0, 'E06': 2,
    'E07': 1, 'E08': 1, 'E09': 0, 'E10': 0, 'E11': 1, 'E12': 1, 'E13': 1,
    'E14': 0, 'E15': 1, 'E16': 1, 'E17': 1, 'E18': 0, 'E19': 0, 'E20': 0,
    'E21': 0, 'E22': 0, 'E23': 0, 'E24': 1,
}


def _look_code(url: str) -> str:
    try:
        return urlparse(url).path.rstrip('/').split('/')[-1] or 'unknown'
    except Exception:
        return 'unknown'


def _strip_frame(action: str) -> str:
    """'A02.3' -> 'A02'"""
    return (action or 'A00').split('.')[0]


def _cache_path(look_code: str, action_code: str, emotion: str, wmotion: str) -> str:
    # look-code 長達 256 字元，直接當檔名會超過 Windows 路徑上限，故取雜湊；動作/表情保留可讀
    look_hash = hashlib.md5(look_code.encode('utf-8')).hexdigest()[:16]
    name = f"{look_hash}_{action_code}_{emotion or 'E00'}_{wmotion or 'W00'}.gif"
    return os.path.join(CACHE_DIR, name)


def _compose_gif(imgs, duration: int) -> io.BytesIO:
    """把多張 RGBA 影格合成透明 GIF（共用畫布、置中、1-bit alpha）"""
    W = max(i.width for i in imgs)
    H = max(i.height for i in imgs)
    processed = []
    for im in imgs:
        canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        canvas.paste(im, ((W - im.width) // 2, (H - im.height) // 2), im)
        alpha = canvas.split()[3]
        p = canvas.convert('RGB').convert('P', palette=Image.ADAPTIVE, colors=255)
        # alpha < 128 的像素設為透明色 index 255
        mask = alpha.point(lambda a: 255 if a < 128 else 0)
        p.paste(255, mask)
        processed.append(p)

    buf = io.BytesIO()
    processed[0].save(
        buf, format='GIF', save_all=True, append_images=processed[1:],
        duration=duration, loop=0, disposal=2, transparency=255,
    )
    buf.seek(0)
    return buf


async def build_character_gif(image_url: str, action: str = 'A00',
                              emotion: str = 'E00', wmotion: str = None,
                              duration: int = 180):
    """
    產生角色動作的透明 GIF，回傳 BytesIO；無法動畫（單幀/失敗）時回傳 None。
    懶快取：命中則直接回傳快取內容。
    """
    if not image_url:
        return None

    code = _strip_frame(action)
    max_frame = ACTION_FRAMES.get(code, 0)
    if max_frame <= 0:
        return None  # 單幀動作無法做成動畫

    emotion = emotion or 'E00'
    look = _look_code(image_url)
    cache = _cache_path(look, code, emotion, wmotion)

    # 1) 命中快取
    try:
        if os.path.exists(cache):
            with open(cache, 'rb') as f:
                return io.BytesIO(f.read())
    except Exception:
        pass

    # 2) 併發下載各影格（靜態 CDN，不記 log）
    urls = [
        apply_look_params(image_url, action=f"{code}.{n}", emotion=emotion, wmotion=wmotion)
        for n in range(max_frame + 1)
    ]
    frames_data = [None] * len(urls)
    try:
        async with aiohttp.ClientSession() as session:
            async def fetch(i, u):
                try:
                    async with session.get(u) as r:
                        if r.status == 200:
                            frames_data[i] = await r.read()
                except Exception:
                    pass
            await asyncio.gather(*(fetch(i, u) for i, u in enumerate(urls)))
    except Exception:
        return None

    imgs = []
    for d in frames_data:
        if d:
            try:
                imgs.append(Image.open(io.BytesIO(d)).convert('RGBA'))
            except Exception:
                pass
    if len(imgs) < 2:
        return None

    # 3) 合成（丟到 thread，不卡事件迴圈）
    try:
        buf = await asyncio.to_thread(_compose_gif, imgs, duration)
    except Exception:
        return None

    # 4) 寫快取
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache, 'wb') as f:
            f.write(buf.getvalue())
    except Exception:
        pass

    buf.seek(0)
    return buf
