import sqlite3
import aiohttp
import io
from PIL import Image
from typing import Optional, Dict

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
