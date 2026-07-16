"""
API_EquipStat.py
================
儲存角色裝備的兩個追蹤項目（供後續排行 / 統計）：
  - 伊妮絲的寶玉：item_total_option 中非零的主屬性與數值。
    傑諾等職業 STR/DEX/LUK 三者相等，合併標籤為 "str+dex+luk" 只存一筆數值。
  - 輪迴碑石（怪物裝備）：有/無，用來統計數量。

裝備端點沒有角色暱稱，但呼叫端握有 ocid + 暱稱，直接一起存。
DB：C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Equip_Stat.db
"""

import os
import sqlite3
import datetime

EQUIP_DB = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Equip_Stat.db'

# 寶玉主屬性：含 max_hp（惡魔復仇者以 HP 為主屬性）
# 註：HP 數值量級遠大於一般屬性，做排行時建議依 gem_stat 分類比較
_MAIN_STATS = ['str', 'dex', 'int', 'luk', 'max_hp']
SAMSARA_NAME = '輪迴碑石'


def _conn():
    os.makedirs(os.path.dirname(EQUIP_DB), exist_ok=True)
    conn = sqlite3.connect(EQUIP_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS character_equip_stat (
            ocid TEXT PRIMARY KEY,
            character_name TEXT,
            gem_stat TEXT,          -- 例 'int' 或 'str+dex+luk'，無寶玉為 NULL
            gem_value INTEGER,      -- 寶玉數值（相等時只存一筆）
            has_samsara INTEGER DEFAULT 0,  -- 輪迴碑石 0/1
            refresh_time TIMESTAMP
        )
    ''')
    return conn


def extract_equip_stat(item_equipment: list):
    """從頂層 item_equipment 取出 (gem_stat, gem_value, has_samsara)"""
    gem_stat, gem_value, has_samsara = None, 0, 0
    for it in (item_equipment or []):
        name = it.get('item_name') or ''
        if '寶玉' in name and gem_stat is None:
            opt = it.get('item_total_option') or {}
            nonzero = []
            for s in _MAIN_STATS:
                try:
                    v = int(opt.get(s, 0) or 0)
                except (ValueError, TypeError):
                    v = 0
                if v != 0:
                    nonzero.append((s, v))
            if nonzero:
                # 三者相等時合併標籤、只存一筆數值
                gem_stat = '+'.join(s for s, _ in nonzero)
                gem_value = nonzero[0][1]
        if name == SAMSARA_NAME:
            has_samsara = 1
    return gem_stat, gem_value, has_samsara


def save_equip_stat(ocid: str, character_name: str, gem_stat, gem_value: int, has_samsara: int):
    """寫入/更新單筆（以 ocid 為 key）。失敗不拋例外。"""
    try:
        with _conn() as conn:
            conn.execute(
                '''
                INSERT INTO character_equip_stat
                    (ocid, character_name, gem_stat, gem_value, has_samsara, refresh_time)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(ocid) DO UPDATE SET
                    character_name = excluded.character_name,
                    gem_stat = excluded.gem_stat,
                    gem_value = excluded.gem_value,
                    has_samsara = excluded.has_samsara,
                    refresh_time = excluded.refresh_time
                ''',
                (ocid, character_name, gem_stat, gem_value, has_samsara, datetime.datetime.now())
            )
            conn.commit()
    except Exception:
        pass


def update_from_equipment(ocid: str, character_name: str, item_equipment: list):
    """便利函式：抽取頂層 item_equipment 後直接存。回傳 (gem_stat, gem_value, has_samsara)。"""
    gs, gv, hs = extract_equip_stat(item_equipment)
    save_equip_stat(ocid, character_name, gs, gv, hs)
    return gs, gv, hs


# ---------- 查詢（供後續排行 / 統計）----------

# 跨職業正規化：換算成「等效主屬」（固定常數）
XENON_RATIO = 25 / 12     # 傑諾 S+D+L 每點 ≈ 等效主屬
DA_RATIO = 25 / 525       # 惡魔復仇者 HP ≈ 等效主屬


def equiv_main_stat(gem_stat: str, gem_value: int) -> float:
    """把寶玉原值換算成等效主屬（供跨職業公平排序）"""
    if gem_stat == 'str+dex+luk':
        return gem_value * XENON_RATIO
    if gem_stat == 'max_hp':
        return gem_value * DA_RATIO
    return float(gem_value)


def get_gem_ranking_normalized(limit: int = 100) -> list:
    """寶玉排行（依等效主屬降冪）。回傳 [(character_name, gem_stat, gem_value, equiv), ...]"""
    result = []
    try:
        with _conn() as conn:
            rows = conn.execute(
                'SELECT character_name, gem_stat, gem_value FROM character_equip_stat '
                'WHERE gem_value > 0'
            ).fetchall()
        for name, stat, val in rows:
            result.append((name, stat, val, round(equiv_main_stat(stat, val))))
        result.sort(key=lambda r: r[3], reverse=True)
        return result[:limit]
    except Exception:
        return []


def get_gem_ranking(limit: int = 50) -> list:
    """寶玉數值排行（高→低），回傳 [(character_name, gem_stat, gem_value), ...]"""
    try:
        with _conn() as conn:
            return conn.execute(
                'SELECT character_name, gem_stat, gem_value FROM character_equip_stat '
                'WHERE gem_value > 0 ORDER BY gem_value DESC LIMIT ?', (limit,)
            ).fetchall()
    except Exception:
        return []


def get_samsara_count() -> int:
    """擁有輪迴碑石的角色數量"""
    try:
        with _conn() as conn:
            return conn.execute(
                'SELECT COUNT(*) FROM character_equip_stat WHERE has_samsara = 1'
            ).fetchone()[0]
    except Exception:
        return 0
