import asyncio
import hashlib
import os
import sqlite3
import aiohttp
import io
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict, List, Tuple

# 資料庫路徑
CHARACTER_OCID_DB = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Character_ocid.db'
CHARACTER_BASIC_INFO_DB = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Ocid_CharacterBasicInfo.db'


def get_character_image_urls(character_names: Dict[int, Optional[str]]) -> Dict[int, Optional[str]]:
    """
    從資料庫查詢每個角色的圖片 URL
    流程：character_name → Character_ocid.db 取 ocid → Ocid_CharacterBasicInfo.db 取 character_image

    Args:
        character_names: {slot: character_name or None}

    Returns:
        {slot: image_url or None}
    """
    result = {}
    for slot, name in character_names.items():
        if name is None:
            result[slot] = None
            continue

        try:
            # 查 ocid
            with sqlite3.connect(CHARACTER_OCID_DB) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT ocid FROM character_ocid WHERE character_id = ?',
                    (name,)
                )
                row = cursor.fetchone()
                if not row:
                    result[slot] = None
                    continue
                ocid = row[0]

            # 用 ocid 查 character_image
            with sqlite3.connect(CHARACTER_BASIC_INFO_DB) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT character_image FROM character_basic_info WHERE ocid = ?',
                    (ocid,)
                )
                row = cursor.fetchone()
                result[slot] = row[0] if row else None

        except Exception as e:
            print(f"[CombineCharacter] 查詢 slot {slot} ({name}) 失敗: {e}")
            result[slot] = None

    return result


async def combine_character_images(character_names: Dict[int, Optional[str]]) -> Optional[io.BytesIO]:
    """
    依據角色名查詢圖片並合成為 3×2 排列的單張圖片。

    排列方式：
        1  2  3
        4  5  6

    Args:
        character_names: {1: name, 2: name, ..., 6: name}  (None 代表該 slot 沒設定)

    Returns:
        合成後的 PNG 圖片 BytesIO，若完全沒有圖片則回傳 None
    """
    image_urls = get_character_image_urls(character_names)

    # 篩選有效 URL
    valid_slots = {slot: url for slot, url in image_urls.items() if url}
    if not valid_slots:
        return None

    # 非同步下載所有圖片
    images: Dict[int, Image.Image] = {}
    async with aiohttp.ClientSession() as session:
        for slot, url in valid_slots.items():
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        img = Image.open(io.BytesIO(data)).convert('RGBA')
                        images[slot] = img
            except Exception as e:
                print(f"[CombineCharacter] 下載 slot {slot} 圖片失敗: {e}")

    if not images:
        return None

    # 以最大尺寸作為每格大小
    max_w = max(img.width for img in images.values())
    max_h = max(img.height for img in images.values())

    # 畫布：3 欄 × 2 列
    cols, rows = 3, 2
    canvas = Image.new('RGBA', (max_w * cols, max_h * rows), (0, 0, 0, 0))

    for slot, img in images.items():
        col = (slot - 1) % 3
        row = (slot - 1) // 3
        # 置中貼上
        x = col * max_w + (max_w - img.width) // 2
        y = row * max_h + (max_h - img.height) // 2
        canvas.paste(img, (x, y), img)

    buf = io.BytesIO()
    canvas.save(buf, format='PNG')
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────
# 帳號角色一覽的造型合成（/accounttracking 用）
#
# 跟上面那個 3x2 的差別：格數不固定、併發下載、有磁碟快取、每格底下寫名字。
# 名字一定要寫 —— 一個 embed 只能放一張圖，12 個小人排在 12 個 field 下面，
# 沒有名字對不起來。
# ─────────────────────────────────────────────────────────────────────

LOOK_CACHE_DIR = r'C:\Users\User\Desktop\DiscordBotlog\API\lookcache'
FONT_PATH = r'C:\Windows\Fonts\msjh.ttc'      # 微軟正黑體，系統字型

_font_cache = {}


def _look_cache_path(url: str) -> str:
    """造型圖的磁碟快取路徑。

    URL 最後一段是**造型本身的雜湊**（換裝才會變），所以快取可以永久有效、
    不必設過期。那一段長達 256 字元，直接當檔名會超過 Windows 路徑上限，
    所以再取一次 md5 —— 跟 CreateCharacterGIF._cache_path 同一套做法。
    """
    try:
        code = urlparse(url).path.rstrip('/').split('/')[-1] or 'unknown'
    except Exception:
        code = 'unknown'
    return os.path.join(LOOK_CACHE_DIR,
                        hashlib.md5(code.encode('utf-8')).hexdigest()[:16] + '.png')


def _font(size: int):
    """字型載入失敗就回 None，呼叫端會改成不寫名字（總比畫出一排豆腐好）。"""
    if size not in _font_cache:
        try:
            _font_cache[size] = ImageFont.truetype(FONT_PATH, size)
        except Exception as e:
            print(f"[CombineCharacter] 載入字型失敗: {e}")
            _font_cache[size] = None
    return _font_cache[size]


async def fetch_look_images(urls) -> Dict[str, bytes]:
    """併發下載造型圖，先問磁碟快取。回傳 {url: png bytes}。

    實測 12 張冷啟動約 1.4 秒、熱的約 0.2 秒 —— 快取命中就完全不連外。
    """
    out, todo = {}, []
    for u in {u for u in urls if u}:
        try:
            with open(_look_cache_path(u), 'rb') as f:
                out[u] = f.read()
        except OSError:
            todo.append(u)
    if not todo:
        return out

    sem = asyncio.Semaphore(12)

    async def one(session, u):
        async with sem:
            try:
                async with session.get(u) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.read()
            except Exception as e:
                print(f"[CombineCharacter] 下載造型失敗: {e}")
                return
        out[u] = data
        try:
            os.makedirs(LOOK_CACHE_DIR, exist_ok=True)
            with open(_look_cache_path(u), 'wb') as f:
                f.write(data)
        except OSError as e:
            print(f"[CombineCharacter] 寫入造型快取失敗: {e}")

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[one(session, u) for u in todo])
    return out


def compose_roster(entries: List[Tuple[str, str]], blobs: Dict[str, bytes],
                   cols: int = 6, scale: int = 2,
                   font_size: int = 28) -> Optional[io.BytesIO]:
    """把 [(角色名, 造型URL), ...] 排成格狀並在每格底下寫名字。

    **同步函式**（PIL 是 CPU 工作），呼叫端要丟 asyncio.to_thread，
    否則會卡住事件迴圈、Discord 會噴 heartbeat blocked。

    ## ⚠️ 圖的長寬比會決定整個 embed 的寬度

    Discord 把 embed 圖的**高度**壓在約 300px。圖太高就會被高度卡住，
    縮完的寬度比 embed 的最大寬度還窄 —— 然後**整個 embed 跟著縮到那個寬度**，
    上面的 inline 欄位全部被擠扁（2026-10-27 實測：4 欄版 768x666、比例 1.15，
    被壓成約 346px 寬，三欄並排的碼塊就從字中間硬斷）。

    所以長寬比必須大於「embed 最大寬度 ÷ 300」≈ 1.73，才會先撞到寬度上限。

        6 欄 × 2 列 = 1152x436，比例 2.64  ✓
        4 欄 × 3 列 =  768x666，比例 1.15  ✗ 會把 embed 縮窄

    一頁最多 12 個、每列 6 個，所以永遠是 1~2 列，比例永遠 ≥ 2.64。
    改 cols 之前先算一下這個比例。

    ## 字級

    1152px 的圖顯示成約 520px，等於縮到 0.45 倍，所以字級要開到 28
    才有 12~13px 可讀。每格 192px 寬，28 級放得下 6 個中文字或 12 個半形字 ——
    角色名最長就是 12 欄寬，剛好放得下。

    ## 背景與對比

    背景透明：Discord 深色與淺色主題底色不同，寫死任一種在另一種下就是
    一個突兀的方塊。名字底下墊一條半透明黑，白字壓在上面 —— 描邊在縮放後
    會糊成一團灰（實測過），墊底條才穩。

    原圖只有 96x96，用 NEAREST 放大（點陣圖用雙線性會糊掉）。
    """
    imgs = []
    for name, url in entries:
        im = None
        if url and url in blobs:
            try:
                im = Image.open(io.BytesIO(blobs[url])).convert('RGBA')
            except Exception as e:
                print(f"[CombineCharacter] 解碼造型失敗 {name}: {e}")
        imgs.append((name, im))
    if not any(im for _n, im in imgs):
        return None

    base = max((im.width for _n, im in imgs if im), default=96)
    baseh = max((im.height for _n, im in imgs if im), default=96)
    font = _font(font_size)
    bar = font_size + 11 if font else 0
    cw, ch = base * scale, baseh * scale + bar
    nrow = (len(imgs) + cols - 1) // cols

    canvas = Image.new('RGBA', (cw * cols, ch * nrow), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    for i, (name, im) in enumerate(imgs):
        x0, y0 = (i % cols) * cw, (i // cols) * ch
        if im:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
            canvas.paste(im, (x0 + (cw - im.width) // 2,
                              y0 + (baseh * scale - im.height) // 2), im)
        if not font:
            continue
        label, clipped = name or '', False
        while label and draw.textlength(label + ('…' if clipped else ''),
                                        font=font) > cw - 10:
            label, clipped = label[:-1], True
        if clipped:
            label += '…'
        if not label:
            continue
        tw = draw.textlength(label, font=font)
        cx, ty = x0 + cw / 2, y0 + baseh * scale + 3
        draw.rounded_rectangle(
            (cx - tw / 2 - 5, ty - 1, cx + tw / 2 + 5, ty + font_size + 5),
            radius=5, fill=(0, 0, 0, 150))
        draw.text((cx, ty), label, font=font, fill=(255, 255, 255, 255),
                  anchor='ma')

    buf = io.BytesIO()
    canvas.save(buf, format='PNG')
    buf.seek(0)
    return buf
