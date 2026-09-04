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
import re
import json
import sqlite3
import datetime
import threading
import atexit

EQUIP_DB = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Equip_Stat.db'

# 寶玉主屬性：含 max_hp（惡魔復仇者以 HP 為主屬性）
# 註：HP 數值量級遠大於一般屬性，做排行時建議依 gem_stat 分類比較
_MAIN_STATS = ['str', 'dex', 'int', 'luk', 'max_hp']
SAMSARA_NAME = '輪迴碑石'

# 裝備統計的等級門檻：只有 >= 此等級的角色才會抓裝備/萌獸/套裝/冠軍
# （寶玉、輪迴碑石等皆屬終局裝備，低等角色查了也是空的）
EQUIP_STAT_MIN_LEVEL = 260

_DDL = '''
    CREATE TABLE IF NOT EXISTS character_equip_stat (
        ocid TEXT PRIMARY KEY,
        character_name TEXT,
        gem_stat TEXT,          -- 例 'int' 或 'str+dex+luk'，無寶玉為 NULL
        gem_value INTEGER,      -- 寶玉數值（相等時只存一筆）
        has_samsara INTEGER DEFAULT 0,  -- 輪迴碑石 0/1
        refresh_time TIMESTAMP
    )
'''

_UPSERT = '''
    INSERT INTO character_equip_stat
        (ocid, character_name, gem_stat, gem_value, has_samsara, refresh_time)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(ocid) DO UPDATE SET
        character_name = excluded.character_name,
        gem_stat = excluded.gem_stat,
        gem_value = excluded.gem_value,
        has_samsara = excluded.has_samsara,
        refresh_time = excluded.refresh_time
'''

# 擴充欄位（既有 DB 以 ALTER TABLE 增補，舊資料為 NULL 直到下次刷新）
_EXTRA_COLUMNS = [
    ('character_level', 'INTEGER'),      # 角色等級
    ('character_class', 'TEXT'),         # 職業
    ('hat_name', 'TEXT'),                # 帽子名稱（供各職業帽子分布統計）
    ('hat_cd', 'INTEGER'),               # 帽子技能冷卻總秒數（正數，例 6 表示 -6秒）
    ('glove_crit_lines', 'INTEGER'),     # 手套主潛能爆擊傷害排數 0~3
    ('has_control_core', 'INTEGER'),     # 全面控制核心 0/1
    ('has_genesis_badge', 'INTEGER'),    # 創世的胸章 0/1
    ('has_nightmare', 'INTEGER'),        # 恍惚的惡夢（戒指）0/1
    ('has_whisper', 'INTEGER'),          # 根源的耳語（戒指）0/1
    ('has_death_oath', 'INTEGER'),       # 死亡之誓（墜飾）0/1
    ('has_immortal_legacy', 'INTEGER'),  # 不朽的遺產（勳章）0/1
    ('has_pride_sin', 'INTEGER'),        # 傲慢的原罪 0/1
    ('fam_option', 'TEXT'),              # 召喚中萌獸的三排組合：3final/2final_atk/2final_other/NULL
    ('fam_special', 'INTEGER'),          # 召喚中萌獸是否為特殊萌獸 0/1
    ('link1', 'INTEGER'),                # 連結槽1 啟用 0/1
    ('link2', 'INTEGER'),                # 連結槽2 啟用 0/1
    ('link3', 'INTEGER'),                # 連結槽3 啟用 0/1
    ('link_vip', 'INTEGER'),             # VIP連結槽 啟用 0/1
    ('set_effects', 'TEXT'),             # JSON: [["套裝名", 件數], ...]
    ('character_exp_rate', 'REAL'),      # 角色經驗%（裝備刷新當下的快照）
    ('champion_grade', 'TEXT'),          # 聯盟冠軍等級 B/A/S/SS/SSS，非冠軍為 'none'
    ('total_starforce', 'INTEGER'),      # 全身裝備星力總和
    ('soul_weapon_level', 'INTEGER'),    # 武器魂武等級（無魂武為 0）
    ('cp_current', 'INTEGER'),           # 本次取樣的戰鬥力
    ('cp_max30', 'INTEGER'),             # 近 30 天最高戰力（由 cp_slots 算出，供排序）
    ('cp_max30_at', 'TEXT'),             # 該最高值的取樣日 YYYY-MM-DD
    ('cp_slots', 'TEXT'),                # JSON {ISO週: [最高值, 日期]}，保留最近 5 週
]

_upsert_cache = {}


def _get_upsert(cols: tuple) -> str:
    """依「本次要更新的欄位組合」產生並快取 UPSERT SQL。

    只更新有成功取得資料的欄位——若某端點（萌獸/套裝）暫時失敗，
    對應欄位不會被寫成 NULL 而清掉既有資料。
    cols 皆來自程式內建常數，非使用者輸入。
    """
    sql = _upsert_cache.get(cols)
    if sql is None:
        allcols = ('ocid',) + cols
        sql = (f"INSERT INTO character_equip_stat ({', '.join(allcols)}) "
               f"VALUES ({', '.join('?' * len(allcols))}) "
               f"ON CONFLICT(ocid) DO UPDATE SET "
               + ', '.join(f'{c} = excluded.{c}' for c in cols))
        _upsert_cache[cols] = sql
    return sql

# 批次寫入：舊版每筆都 connect+CREATE TABLE+commit(fsync)，實測 4.6ms/筆
# （50 萬筆需 38 分鐘）。改為共用連線 + 緩衝 executemany 後為 0.004ms/筆。
BATCH_SIZE = 500
_buffer = []
_lock = threading.RLock()   # 保護 _buffer 與共用連線（寫入在背景執行緒、查詢在主執行緒）
_conn_cache = None


def _conn():
    """取得共用連線（WAL 模式）。所有存取都必須在 _lock 保護下進行。"""
    global _conn_cache
    if _conn_cache is None:
        os.makedirs(os.path.dirname(EQUIP_DB), exist_ok=True)
        # check_same_thread=False：連線跨執行緒共用，並發由 _lock 序列化
        conn = sqlite3.connect(EQUIP_DB, check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute(_DDL)
        # 欄位遷移：既有 DB 補上擴充欄位（重複執行安全）
        existing = {r[1] for r in conn.execute('PRAGMA table_info(character_equip_stat)')}
        for col, coltype in _EXTRA_COLUMNS:
            if col not in existing:
                conn.execute(f'ALTER TABLE character_equip_stat ADD COLUMN {col} {coltype}')
        conn.commit()
        _conn_cache = conn
    return _conn_cache


def flush_equip_stat() -> int:
    """把緩衝中的資料一次寫入 DB。回傳實際寫入筆數。批次結束或查詢前應呼叫。"""
    global _buffer
    with _lock:
        if not _buffer:
            return 0
        rows, _buffer = _buffer, []
        try:
            conn = _conn()
            grouped = {}
            for cols, values in rows:
                grouped.setdefault(cols, []).append(values)
            for cols, items in grouped.items():
                conn.executemany(_get_upsert(cols), items)
            conn.commit()
            return len(rows)
        except Exception as e:
            print(f"[EquipStat] flush 失敗，{len(rows)} 筆未寫入: {e}")
            return 0


# 程式結束時寫出最後一批未滿 BATCH_SIZE 的資料
atexit.register(flush_equip_stat)


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


# 追蹤的特殊裝備：(DB欄位, 顯示名稱)；以 item_name 精確比對
TRACKED_ITEMS = [
    ('has_samsara', '輪迴碑石'),
    ('has_control_core', '全面控制核心'),
    ('has_genesis_badge', '創世的胸章'),
    ('has_nightmare', '恍惚的惡夢'),
    ('has_whisper', '根源的耳語'),
    ('has_death_oath', '死亡之誓'),
    ('has_immortal_legacy', '不朽的遺產'),
    ('has_pride_sin', '傲慢的原罪'),
]
_ITEM_TO_COL = {name: col for col, name in TRACKED_ITEMS}
_CD_RE = re.compile(r'技能冷卻時間\s*-\s*(\d+)\s*秒')
_MAIN_POT = ('potential_option_1', 'potential_option_2', 'potential_option_3')
_ADD_POT = ('additional_potential_option_1', 'additional_potential_option_2',
            'additional_potential_option_3')


def extract_equip_extra(item_equipment: list) -> dict:
    """從 item_equipment 抽取擴充統計項目。

    hat_cd            帽子「技能冷卻時間 -N秒」總和（潛能+附加潛能，回傳正數）
    glove_crit_lines  手套主潛能中「爆擊傷害」排數 0~3
    has_control_core  是否裝備全面控制核心
    has_genesis_badge 是否裝備創世的胸章
    """
    out = {'hat_name': None, 'hat_cd': 0, 'glove_crit_lines': 0,
           'total_starforce': 0, 'soul_weapon_level': 0}
    # has_samsara 由 extract_equip_stat 負責，此處只處理其餘追蹤裝備
    out.update({col: 0 for col, _ in TRACKED_ITEMS if col != 'has_samsara'})
    for it in (item_equipment or []):
        slot = it.get('item_equipment_slot') or ''
        name = (it.get('item_name') or '').strip()
        col = _ITEM_TO_COL.get(name)
        if col and col != 'has_samsara':
            out[col] = 1
        # 全身星力總和
        try:
            out['total_starforce'] += int(it.get('starforce') or 0)
        except (TypeError, ValueError):
            pass
        if slot == '武器':
            try:
                out['soul_weapon_level'] = int(it.get('soul_weapon_level') or 0)
            except (TypeError, ValueError):
                out['soul_weapon_level'] = 0
        if slot == '帽子':
            out['hat_name'] = name or None
            total = 0
            for k in _MAIN_POT + _ADD_POT:
                m = _CD_RE.search(it.get(k) or '')
                if m:
                    total += int(m.group(1))
            out['hat_cd'] = total
        elif slot == '手套':
            out['glove_crit_lines'] = sum(1 for k in _MAIN_POT if '爆擊傷害' in (it.get(k) or ''))
    return out


_FINAL_DMG = '最終傷害'
_ATK_NAMES = ('物理攻擊力', '魔法攻擊力')


# ---------- 戰鬥力（30 日最高，週桶環形緩衝）----------

# 保留最近幾個 ISO 週。5 週足以涵蓋 30 天，且每週一格自動過期，
# 不需要另外的清理排程，儲存量也固定。
CP_SLOT_WEEKS = 5


def extract_combat_power(stat_data: dict):
    """從 /character/stat 的 final_stat 取出「戰鬥力」。取不到回 None。"""
    if not stat_data:
        return None
    for item in (stat_data.get('final_stat') or []):
        if item.get('stat_name') == '戰鬥力':
            try:
                return int(float(item.get('stat_value')))
            except (TypeError, ValueError):
                return None
    return None


def _iso_week(dt) -> str:
    y, w, _ = dt.isocalendar()
    return f'{y}-W{w:02d}'


def _recent_weeks(now) -> set:
    return {_iso_week(now - datetime.timedelta(weeks=i)) for i in range(CP_SLOT_WEEKS)}


def merge_cp_slots(old_json, cp, now=None):
    """把本次戰力併入週桶，回傳 (slots_json, cp_max30, cp_max30_at)。

    同一週內取最大值——角色脫裝期間剛好被取樣時，不會壓低該週的紀錄。
    超過 CP_SLOT_WEEKS 週的桶直接丟棄，達成滑動視窗。
    """
    now = now or datetime.datetime.now()
    try:
        slots = json.loads(old_json) if old_json else {}
        if not isinstance(slots, dict):
            slots = {}
    except (ValueError, TypeError):
        slots = {}

    keep = _recent_weeks(now)
    slots = {k: v for k, v in slots.items()
             if k in keep and isinstance(v, list) and len(v) == 2}

    if cp and cp > 0:
        wk = _iso_week(now)
        cur = slots.get(wk)
        if not cur or cp > cur[0]:
            slots[wk] = [int(cp), now.strftime('%Y-%m-%d')]

    if not slots:
        return json.dumps({}), None, None
    best = max(slots.values(), key=lambda v: v[0])
    return json.dumps(slots, separators=(',', ':')), best[0], best[1]


def cp_fields(ocid: str, stat_data: dict, now=None) -> dict:
    """由 /character/stat 算出戰力相關欄位。取不到戰力時回空 dict（呼叫端不會寫入）。

    每日刷新與 admin 全量腳本共用這一份，避免兩邊邏輯走鐘。
    """
    cp = extract_combat_power(stat_data)
    if cp is None:
        return {}
    slots, mx, at = merge_cp_slots(_read_cp_slots(ocid), cp, now)
    return {'cp_current': cp, 'cp_slots': slots, 'cp_max30': mx, 'cp_max30_at': at}


def sample_and_get_cp(ocid: str, character_name: str, stat_data: dict = None,
                     character_level=None, character_class=None):
    """回傳 (cp_max30, cp_max30_at, 週桶數)，供 /character 之類的查詢顯示。

    若 stat_data 可用且等級達門檻，順便把這次查詢當成一次取樣併入週桶——
    /character 本來就會打 /character/stat，所以這是零 API 成本的額外樣本。

    低於 EQUIP_STAT_MIN_LEVEL 者只讀不寫：否則 UPSERT 會在 Equip_Stat 插入一列
    character_level 為 NULL 的殘缺資料，破壞該表「只收高等角色」的契約。
    """
    try:
        lv = int(character_level or 0)
    except (TypeError, ValueError):
        lv = 0

    if stat_data is not None and lv >= EQUIP_STAT_MIN_LEVEL:
        f = cp_fields(ocid, stat_data)
        if f:
            f['character_level'] = lv
            if character_class:
                f['character_class'] = character_class
            save_character_stat(ocid, character_name, f)
            # 直接用剛算好的結果，省去 flush + 重讀
            try:
                n = len(json.loads(f['cp_slots']) or {})
            except (ValueError, TypeError):
                n = 0
            return f['cp_max30'], f['cp_max30_at'], n

    # 只讀路徑（等級不足、端點失敗、或本來就沒有 stat）
    try:
        flush_equip_stat()
        with _lock:
            row = _conn().execute(
                'SELECT cp_max30, cp_max30_at, cp_slots FROM character_equip_stat '
                'WHERE ocid = ?', (ocid,)).fetchone()
        if not row or row[0] is None:
            return None, None, 0
        try:
            n = len(json.loads(row[2]) or {}) if row[2] else 0
        except (ValueError, TypeError):
            n = 0
        return row[0], row[1], n
    except Exception:
        return None, None, 0


def _read_cp_slots(ocid: str):
    """讀取既有的週桶。注意：讀的是已寫入 DB 的內容，同一輪若同一 ocid
    被處理兩次（實際不會發生），第二次會讀到舊值。"""
    try:
        with _lock:
            row = _conn().execute(
                'SELECT cp_slots FROM character_equip_stat WHERE ocid = ?', (ocid,)).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def classify_familiar(options: list) -> str:
    """依三排選項分類萌獸（順序不影響）：
    '3final' 三排終傷 / '2final_atk' 雙終傷+物攻或魔攻 / '2final_other' 雙終傷+其他 / '' 其他
    """
    names = [(o.get('option_name') or '') for o in (options or [])]
    finals = sum(1 for n in names if n.startswith(_FINAL_DMG))
    if finals >= 3:
        return '3final'
    if finals == 2:
        rest = [n for n in names if not n.startswith(_FINAL_DMG)]
        if any(n.startswith(_ATK_NAMES) for n in rest):
            return '2final_atk'
        return '2final_other'
    return ''


def extract_familiar_stat(familiar_data: dict) -> dict:
    """抽取萌獸統計。

    fam_option / fam_special 只取「召喚中」(summoned_flag=true) 的那一隻——
    召喚中的萌獸才是實際生效的屬性來源，且不一定在連結槽內（可能是 registered）。
    link1/2/3/link_vip 為 4 個連結槽的啟用狀態。
    """
    out = {'fam_option': None, 'fam_special': 0,
           'link1': 0, 'link2': 0, 'link3': 0, 'link_vip': 0}
    if not familiar_data:
        return out
    slot_key = {'1': 'link1', '2': 'link2', '3': 'link3', 'vip': 'link_vip'}
    for s in (familiar_data.get('familiar_link_slot') or []):
        key = slot_key.get(str(s.get('slot_id') or '').lower())
        if key and str(s.get('active_flag')).lower() == 'true':
            out[key] = 1
    for f in (familiar_data.get('familiar_info') or []):
        if str(f.get('summoned_flag')).lower() != 'true':
            continue
        out['fam_option'] = classify_familiar(f.get('option')) or None
        out['fam_special'] = 1 if str(f.get('familiar_special_flag')).lower() == 'true' else 0
        break   # 召喚中僅一隻
    return out


CHAMPION_GRADES = ('B', 'A', 'S', 'SS', 'SSS')


def extract_champion_grade(champion_data: dict, character_name: str) -> str:
    """從帳號冠軍名單中找出「該角色本人」的冠軍等級。

    union-champion 回的是整個帳號的冠軍名單（最多 6 人），
    因此需比對角色名字；不在名單中回 'none'。
    """
    if not champion_data:
        return 'none'
    for c in (champion_data.get('union_champion') or []):
        if (c.get('champion_name') or '') == character_name:
            return c.get('champion_grade') or 'none'
    return 'none'


def extract_set_effects(set_effect_data: dict):
    """抽取套裝清單 [[套裝名, 件數], ...]，存成 JSON 字串；無資料回 None。"""
    if not set_effect_data:
        return None
    rows = [[s.get('set_name'), s.get('total_set_count')]
            for s in (set_effect_data.get('set_effect') or [])
            if s.get('set_name')]
    return json.dumps(rows, ensure_ascii=False) if rows else None


def save_character_stat(ocid: str, character_name: str, fields: dict):
    """排入緩衝。只寫入 fields 中實際提供的欄位，未提供者保留 DB 既有值。"""
    try:
        data = {'character_name': character_name, 'refresh_time': datetime.datetime.now()}
        data.update(fields)
        cols = tuple(data.keys())
        values = tuple([ocid] + [data[c] for c in cols])
        with _lock:
            _buffer.append((cols, values))
            need_flush = len(_buffer) >= BATCH_SIZE
        if need_flush:
            flush_equip_stat()
    except Exception:
        pass


def save_equip_stat(ocid: str, character_name: str, gem_stat, gem_value: int, has_samsara: int):
    """將單筆（僅基本欄位）排入緩衝，滿 BATCH_SIZE 才實際寫入。失敗不拋例外。"""
    save_character_stat(ocid, character_name, {
        'gem_stat': gem_stat, 'gem_value': gem_value, 'has_samsara': has_samsara})


def update_from_equipment(ocid: str, character_name: str, item_equipment: list):
    """便利函式：抽取頂層 item_equipment 後直接存。回傳 (gem_stat, gem_value, has_samsara)。"""
    gs, gv, hs = extract_equip_stat(item_equipment)
    save_equip_stat(ocid, character_name, gs, gv, hs)
    return gs, gv, hs


def update_full_stat(ocid: str, character_name: str, item_equipment: list,
                     character_level=None, character_class=None,
                     familiar_data: dict = None, set_effect_data: dict = None,
                     character_exp_rate=None, champion_data: dict = None,
                     stat_data: dict = None):
    """完整更新一筆：裝備（寶玉/輪迴/CD帽/手套爆傷/核心/胸章）＋萌獸＋套裝＋等級職業。

    回傳寫入用的欄位 dict（供呼叫端統計）。
    """
    gs, gv, hs = extract_equip_stat(item_equipment)
    fields = {'gem_stat': gs, 'gem_value': gv, 'has_samsara': hs}
    fields.update(extract_equip_extra(item_equipment))
    if character_level is not None:
        fields['character_level'] = character_level
    if character_class is not None:
        fields['character_class'] = character_class
    if character_exp_rate is not None:
        try:
            fields['character_exp_rate'] = float(character_exp_rate)
        except (TypeError, ValueError):
            pass
    # 冠軍端點失敗時（None）不寫入，避免清掉既有資料
    if champion_data is not None:
        fields['champion_grade'] = extract_champion_grade(champion_data, character_name)
    # familiar / set-effect 端點失敗時（None）不寫入對應欄位，
    # 避免把先前抓到的好資料清成 NULL/0
    if familiar_data is not None:
        fields.update(extract_familiar_stat(familiar_data))
    if set_effect_data is not None:
        fields['set_effects'] = extract_set_effects(set_effect_data)
    # 戰鬥力：端點失敗時（None）完全不動這幾個欄位
    if stat_data is not None:
        fields.update(cp_fields(ocid, stat_data))
    save_character_stat(ocid, character_name, fields)
    return fields


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
        flush_equip_stat()   # 先寫出緩衝，確保查得到最新資料
        with _lock:
            rows = _conn().execute(
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
        flush_equip_stat()   # 先寫出緩衝，確保查得到最新資料
        with _lock:
            return _conn().execute(
                'SELECT character_name, gem_stat, gem_value FROM character_equip_stat '
                'WHERE gem_value > 0 ORDER BY gem_value DESC LIMIT ?', (limit,)
            ).fetchall()
    except Exception:
        return []


def _query(sql: str, params=()) -> list:
    """統計查詢共用：先寫出緩衝再讀，失敗回空list。"""
    try:
        flush_equip_stat()
        with _lock:
            return _conn().execute(sql, params).fetchall()
    except Exception as e:
        print(f"[EquipStat] 查詢失敗: {e}")
        return []


def get_analysed_total(min_level: int = 0) -> int:
    """已完成擴充統計（character_level 非 NULL）的角色數，作為佔比分母。"""
    rows = _query('SELECT COUNT(*) FROM character_equip_stat '
                  'WHERE character_level IS NOT NULL AND character_level >= ?', (min_level,))
    return rows[0][0] if rows else 0


def get_hat_cd_distribution(min_level: int = 290, character_class: str = None) -> dict:
    """LV min_level 以上的帽子技能冷卻秒數分布，可指定職業。
    回傳 {'total': n, 'counts': {秒數: 人數, ...}}（秒數為正整數，0 表示無CD）
    """
    sql = ('SELECT COALESCE(hat_cd, 0), COUNT(*) FROM character_equip_stat '
           'WHERE character_level IS NOT NULL AND character_level >= ?')
    params = [min_level]
    if character_class:
        sql += ' AND character_class = ?'
        params.append(character_class)
    sql += ' GROUP BY COALESCE(hat_cd, 0) ORDER BY 1 DESC'
    rows = _query(sql, tuple(params))
    counts = {int(cd): cnt for cd, cnt in rows}
    return {'total': sum(counts.values()), 'counts': counts}


def get_classes_with_stats(min_level: int = 290) -> list:
    """有統計資料的職業清單 [(職業, 人數), ...]，依人數降冪。"""
    return [(c, n) for c, n in _query(
        'SELECT character_class, COUNT(*) FROM character_equip_stat '
        'WHERE character_level IS NOT NULL AND character_level >= ? '
        'AND character_class IS NOT NULL '
        'GROUP BY character_class ORDER BY COUNT(*) DESC', (min_level,))]


def get_equipment_ownership() -> dict:
    """全服特殊裝備持有人數（分母為已完成統計的角色數）。
    回傳 {'total': n, 'items': [(顯示名稱, 人數), ...]}
    """
    cols = [col for col, _ in TRACKED_ITEMS]
    sums = ', '.join(f'SUM(COALESCE({c}, 0))' for c in cols)
    rows = _query(f'SELECT COUNT(*), {sums} FROM character_equip_stat '
                  'WHERE character_level IS NOT NULL')
    if not rows or not rows[0][0]:
        return {'total': 0, 'items': [(name, 0) for _, name in TRACKED_ITEMS]}
    total = rows[0][0]
    values = rows[0][1:]
    items = [(name, values[i] or 0) for i, (_, name) in enumerate(TRACKED_ITEMS)]
    return {'total': total, 'items': items}


def get_glove_crit_distribution(levels=(285, 290, 295)) -> dict:
    """各等級門檻的手套爆傷排數分布。
    回傳 {門檻等級: {'total': n, 0: n, 1: n, 2: n, 3: n}}
    """
    out = {}
    for lv in levels:
        rows = _query(
            'SELECT COALESCE(glove_crit_lines, 0), COUNT(*) FROM character_equip_stat '
            'WHERE character_level >= ? AND character_level IS NOT NULL '
            'GROUP BY COALESCE(glove_crit_lines, 0)', (lv,))
        d = {0: 0, 1: 0, 2: 0, 3: 0}
        for lines, cnt in rows:
            if lines in d:
                d[lines] = cnt
        d['total'] = sum(d[k] for k in (0, 1, 2, 3))
        out[lv] = d
    return out


# 魂武等級 0~100，每 10 等一組（最後一組吃到 999 以防上限調高）
SOUL_BUCKETS = [
    (0, 9, 'LV 0~9'),
    (10, 19, 'LV 10~19'),
    (20, 29, 'LV 20~29'),
    (30, 39, 'LV 30~39'),
    (40, 49, 'LV 40~49'),
    (50, 59, 'LV 50~59'),
    (60, 69, 'LV 60~69'),
    (70, 79, 'LV 70~79'),
    (80, 89, 'LV 80~89'),
    (90, 999, 'LV 90~100'),
]

# 由低到高的冠軍等級（顯示時反轉成高→低）
CHAMPION_ORDER = ['none', 'C', 'B', 'A', 'S', 'SS', 'SSS']


def get_soul_weapon_distribution(min_level: int = 0) -> dict:
    """魂武等級分布（依 SOUL_BUCKETS 分組）。
    回傳 {'total': n, 'buckets': [(標籤, 人數), ...], 'has_soul': n}
    """
    rows = _query(
        'SELECT COALESCE(soul_weapon_level, 0), COUNT(*) FROM character_equip_stat '
        'WHERE soul_weapon_level IS NOT NULL AND COALESCE(character_level, 0) >= ? '
        'GROUP BY COALESCE(soul_weapon_level, 0)', (min_level,))
    counts = {}
    total = 0
    has_soul = 0
    for lv, n in rows:
        lv = int(lv)
        total += n
        if lv > 0:
            has_soul += n
        for lo, hi, label in SOUL_BUCKETS:
            if lo <= lv <= hi:
                counts[label] = counts.get(label, 0) + n
                break
    buckets = [(label, counts.get(label, 0)) for _, _, label in SOUL_BUCKETS]
    return {'total': total, 'buckets': buckets, 'has_soul': has_soul}


def get_champion_grade_distribution(min_level: int = 0, character_class: str = None) -> dict:
    """聯盟冠軍等級分布，可指定職業。
    回傳 {'total': n, 'grades': [(等級, 人數), ...高→低], 'is_champion': n}
    """
    sql = ('SELECT champion_grade, COUNT(*) FROM character_equip_stat '
           'WHERE champion_grade IS NOT NULL AND COALESCE(character_level, 0) >= ?')
    params = [min_level]
    if character_class:
        sql += ' AND character_class = ?'
        params.append(character_class)
    sql += ' GROUP BY champion_grade'
    rows = _query(sql, tuple(params))
    raw = {g: n for g, n in rows}
    total = sum(raw.values())
    ordered = [(g, raw.get(g, 0)) for g in reversed(CHAMPION_ORDER)]
    # 保留 API 可能新增、不在預設清單中的等級
    for g, n in raw.items():
        if g not in CHAMPION_ORDER:
            ordered.insert(0, (g, n))
    return {'total': total, 'grades': ordered,
            'is_champion': total - raw.get('none', 0)}


def get_familiar_distribution(min_level: int = 0) -> dict:
    """召喚中萌獸的三排組合分布、特殊萌獸數，以及連結槽啟用人數。"""
    total = get_analysed_total(min_level)
    rows = _query(
        'SELECT COALESCE(fam_option, "none"), COUNT(*) FROM character_equip_stat '
        'WHERE character_level IS NOT NULL AND character_level >= ? '
        'GROUP BY COALESCE(fam_option, "none")', (min_level,))
    options = {'3final': 0, '2final_atk': 0, '2final_other': 0, 'none': 0}
    for k, cnt in rows:
        options[k] = options.get(k, 0) + cnt
    link_rows = _query(
        'SELECT SUM(link1), SUM(link2), SUM(link3), SUM(link_vip), SUM(fam_special) '
        'FROM character_equip_stat WHERE character_level IS NOT NULL AND character_level >= ?',
        (min_level,))
    l1, l2, l3, lv_, sp = (link_rows[0] if link_rows else (0, 0, 0, 0, 0))
    return {'total': total, 'options': options,
            'links': {'1': l1 or 0, '2': l2 or 0, '3': l3 or 0, 'VIP': lv_ or 0},
            'special': sp or 0}


def get_samsara_count() -> int:
    """擁有輪迴碑石的角色數量"""
    try:
        flush_equip_stat()   # 先寫出緩衝，確保查得到最新資料
        with _lock:
            return _conn().execute(
                'SELECT COUNT(*) FROM character_equip_stat WHERE has_samsara = 1'
            ).fetchone()[0]
    except Exception:
        return 0
