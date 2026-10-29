"""帳號追蹤 —— 列出同一個帳號底下所有角色的職業／等級／經驗／戰力／近 7 日成長。

## 帳號是怎麼認出來的

`/user/union-champion` 回的是**整個帳號**的冠軍名單，管線把這些觀測累積在
`Champion_roster.db`。同一次觀測裡的角色必定同帳號，`roster.account_of()`
就從目標角色往外擴散出整組。詳見 `tmsapi/store/roster.py` 的模組說明。

兩個無法消除的限制，呼叫端要讓使用者知道：
  * 沒啟用過聯盟冠軍的帳號推不出連結 —— 實測約四分之一的角色只查得到自己。
  * 看到的是**下限**：從沒上過冠軍榜、也沒被爬到的角色不會出現。

## 資料來源與成本

職業、等級、經驗%、世界、以及**沒升等者**的 7 日成長全部來自本機
`Ocid_CharacterBasicInfo.db`，零 API。呼叫端逐頁補兩種東西（見 Slash_API）：

  * 戰力 —— 本機 `Equip_Stat.db` 只收 LV260 以上（`EQUIP_STAT_MIN_LEVEL = 260`），
    實測帳號角色有一半在那之下，所以每頁 12 隻一律現打。
  * **升等者**的七天前經驗% —— 見 `row_growth()` 的說明。實測只有 5.7% 的角色
    七天內有升等，一頁平均多打不到一次。

## 版面

一個角色一個 embed field（`inline=True`），由 Discord 自己排版 ——
手機會自動改成一欄，不會像等寬表格那樣橫捲。碼塊裡只放
「欄位名：值」，欄位名一律兩個中文字，所以中文字數固定、不會歪
（Discord 碼塊的中文字不是剛好兩個半形字寬，補空白對齊那套在這裡行不通）。
"""
import json
import sqlite3

import discord

from tmsapi.config import CHARACTER_BASIC_DB
from tmsapi.store import roster
from functions import ansi
from functions.API_functions.CreateEXPTrackingEmbed import calculate_exp_growth

PER_PAGE = 12
MAX_PAGES = 5
MAX_CHARS = PER_PAGE * MAX_PAGES

_conn_cache = None


def _conn():
    """唯讀開基本資料庫。快取住，每次翻頁都要用。"""
    global _conn_cache
    if _conn_cache is None:
        _conn_cache = sqlite3.connect(
            'file:' + CHARACTER_BASIC_DB + '?mode=ro', uri=True,
            check_same_thread=False, timeout=30)
    return _conn_cache


def fmt_cp(n):
    """戰力以 兆/億/萬 顯示（沿用 Slash_Battle._format_num 的寫法）。"""
    if not n:
        return '—'
    n = int(n)
    if n >= 10 ** 12:
        return '%.2f兆' % (n / 10 ** 12)
    if n >= 10 ** 8:
        return '%.2f億' % (n / 10 ** 8)
    if n >= 10 ** 4:
        return '%.1f萬' % (n / 10 ** 4)
    return '{:,}'.format(n)


def extract_cp(stat_data):
    """從 character/stat 的回應裡挑出戰鬥力。"""
    for item in ((stat_data or {}).get('final_stat') or []):
        if item.get('stat_name') == '戰鬥力':
            try:
                return int(item.get('stat_value', 0))
            except (TypeError, ValueError):
                return None
    return None


# 戰力分段配色，由冷到暖。門檻是 5/10/20/40 億。
#
# 沒有真正的漸層可用：Discord 碼塊只保證吃得到 30-37／90-97 這十六色
# （24 位元全彩實測會動，但那是未公開、分批推送的功能，公開的 bot 不能賭 ——
# 吃不到的客戶端會看到一整串裸控制碼）。所以做成分段。
#
# 刻意避開藍色：藍色在這裡已經是「會變的那個數字」（經驗%、成長量）的顏色。
CP_TIERS = (
    (40 * 10 ** 8, ansi.RED),
    (20 * 10 ** 8, ansi.YELLOW),
    (10 * 10 ** 8, ansi.CYAN),
    (5 * 10 ** 8, ansi.GREEN),
)


def short_class(cls):
    """職業名正規化。

    `大魔導士(火、毒)` 這類在這個版面是整個碼塊最寬的一行（18 欄），而火毒／冰雷
    本來就是玩家慣用的叫法，直接用它就好 —— 轉職階級從等級看得出來，不必再寫
    一次「大魔導士」。

    認括號裡的內容而不是硬寫六個字串：實測全部 93 個職業裡只有 6 個帶括號
    （魔導士／大魔導士／巫師各兩種），都是這兩系的，所以這條規則是完備的。
    """
    if not cls:
        return '—'
    if '火、毒' in cls:
        return '火毒'
    if '冰、雷' in cls:
        return '冰雷'
    return cls


def cp_color(n):
    """戰力對應的顏色；未達最低門檻回 None（維持碼塊預設色）。"""
    if not n:
        return None
    for floor, color in CP_TIERS:
        if n >= floor:
            return color
    return None


def _parse_hist(lh, level, exp, rate):
    """從 lvl_hist 算出七天前的狀態。

    回傳 (升了幾級, 七天前日期, 同級時的成長%, 最後一筆的日期)；
    算不出來的部分給 None。

    `lvl_hist` 是 [["YYYY-MM-DD", 等級, 本級累積經驗], ...]，多數是 8 天的
    滾動視窗（剛納入追蹤的角色會短一截），最後一筆實測等於當前值
    （抽查 5000 筆全部一致），所以頭尾相比就是這七天的成長。

    ⚠️ `character_exp` 升級會歸零（實測升級當天 3,959 次下降 vs 653 次上升），
    跨等級不能直接相減。**同一級之內**可以用該角色自己的資料反推本級需求經驗
    （`需求 = exp ÷ (rate/100)`），所以同級的百分比在這裡就能算得精確：

        成長% = Δexp ÷ 需求 × 100 = Δexp × rate ÷ exp

    跨等級就得知道**舊等級**的需求經驗。本來想從全站資料反推一張表，實測
    Lv.210~259 每一級都有**兩條不同的經驗曲線**（例如 Lv.250 是 1.87e11 與
    4.42e11 兩群，各佔四成；260 以上才合流），而世界、職業、職業階級都分不開
    這兩群 —— 原因不明，所以不用那張表。改成跟 API 要七天前那一天的資料，
    那裡直接就有 `character_exp_rate`，精確且不必猜（見 row_growth）。
    """
    try:
        hist = json.loads(lh) if lh else []
    except (TypeError, ValueError):
        hist = []
    if len(hist) < 2:
        return None, None, None, None
    old_date, old_lv, old_exp = hist[0][0], hist[0][1], hist[0][2]
    end = hist[-1][0]
    d_lv = level - old_lv
    if d_lv < 0:
        return None, None, None, end
    if d_lv > 0:
        return d_lv, old_date, None, end
    if exp == old_exp:
        return 0, old_date, 0.0, end
    if not exp or not rate:
        return None, None, None, end
    return 0, old_date, (exp - old_exp) * float(rate) / exp, end


def row_growth(r, old_rates=None):
    """近七日成長的數值，例如 `0.37%`、`1Lv`；算不出來回 `—`。

    不加方括號、不加正號、升等也不加星星 —— 成長自成一行、前面有「7日」帶頭，
    那些裝飾都是多的。（原本的方括號是為了讓 ansi 的 _DELTA 正則自動上粉，
    現在改由呼叫端明確上色。）

    沒升等的直接用本機算好的值。升等的要靠 `old_rates`（{ocid: 七天前的經驗%}）
    才能套 /exptracking 的 `calculate_exp_growth`；拿不到就退回「升了幾級」，
    至少那個一定是對的。

    （不能寫成 `>100%` 那種下限：升一級不代表成長超過 100%，
    99.9% 升到 0.1% 只成長 0.2%。）
    """
    d_lv = r['d_lv']
    if d_lv is None:
        return '—'
    if d_lv == 0:
        return '%.2f%%' % r['growth_pct']
    old_rate = (old_rates or {}).get(r['ocid'])
    if old_rate is None:
        return '%dLv' % d_lv
    pct = calculate_exp_growth(r['level'], r['exp_rate'], r['level'] - d_lv, old_rate)
    return '%.2f%%' % pct


def collect_account(character_name):
    """撈出同帳號角色，依等級排序。全程本機，零 API。

    回傳 {'success', 'rows', 'total', 'world', 'window', 'truncated'}。
    查不到時回 {'success': False, 'reason': 'nolocal'}。
    """
    names = roster.account_of(character_name)
    if not names:
        return {'success': False, 'reason': 'nolocal'}

    q = ','.join('?' * len(names))
    raw = _conn().execute(
        'SELECT ocid, character_name, world_name, character_class, '
        '       character_level, character_exp_rate, character_exp, lvl_hist, '
        '       character_image, access_flag '
        'FROM character_basic_info WHERE character_name IN (%s)' % q,
        tuple(names)).fetchall()
    if not raw:
        return {'success': False, 'reason': 'nolocal'}

    # 聯盟是每個世界各自獨立的，所以一個「帳號」在這份資料裡必定同世界。
    # 照查詢者的世界過濾，順便擋掉同名角色把兩個人併在一起的情況
    # （實測 490,608 個角色裡只有 6 個名字重複，而且都同世界，所以這主要是保險）。
    me = next((r for r in raw if r[1] == character_name), None)
    world = me[2] if me else None
    if world:
        raw = [r for r in raw if r[2] == world]

    # 成長區間取全體的涵蓋範圍，不能拿第一筆充數：各角色被納入追蹤的時間不同，
    # 多數是 8 天的視窗，但也有只有 6 天的。
    rows, starts, ends = [], [], []
    for ocid, nm, wd, cls, lv, rate, exp, lh, img, af in raw:
        lv = int(lv or 0)
        rate = float(rate or 0)
        d_lv, old_date, pct, end_date = _parse_hist(lh, lv, exp, rate)
        if old_date:
            starts.append(old_date)
        if end_date:
            ends.append(end_date)
        rows.append({
            'ocid': ocid,
            'name': nm,
            'world': wd,
            'cls': short_class(cls),
            'level': lv,
            'exp_rate': rate,
            'd_lv': d_lv,
            'old_date': old_date,
            'growth_pct': pct,
            'image': img,
            # access_flag 是官方的「近 7 日是否登入」旗標，存成字串 'true'/'false'。
            # 交叉驗證過：flag 為 true 的有 80% 這七天長了經驗，false 的只有 1.7%，
            # 所以它確實就是登入與否，不是別的意思。
            'online': str(af or '').lower() == 'true',
        })
    rows.sort(key=lambda r: (-r['level'], -r['exp_rate'], r['name']))
    return {
        'success': True,
        'rows': rows[:MAX_CHARS],
        'total': len(rows),
        'world': world,
        'window': (min(starts), max(ends)) if starts and ends else None,
        'truncated': len(rows) > MAX_CHARS,
    }


def page_count(rows):
    return max(1, (len(rows) + PER_PAGE - 1) // PER_PAGE)


def page_rows(rows, page):
    return rows[page * PER_PAGE:(page + 1) * PER_PAGE]


def needs_old_rate(rows):
    """這一頁有哪些角色得跟 API 要七天前的資料。回傳 [(ocid, 日期), ...]。"""
    return [(r['ocid'], r['old_date']) for r in rows
            if r['d_lv'] and r['old_date']]


def look_entries(rows):
    """這一頁要合成的造型，順序跟 field 一致（圖上的名字就是靠這個對位）。"""
    return [(r['name'], r.get('image')) for r in rows]


def build_embed(character_name, data, page, cp_map=None, old_rates=None,
                image_name=None):
    """組出第 page 頁（0-based）。

    一個角色一個 field，`inline=True` 交給 Discord 排版（桌機一列三個、
    手機自動收成一欄）。碼塊裡的欄位名一律兩個中文字，中文字數固定才不會歪。

    `image_name` 是同時上傳的合成造型圖檔名；Discord 會把它排在所有 field
    底下，所以圖上每格都寫了角色名，不然對不出是哪一隻。
    """
    rows = data['rows']
    npage = page_count(rows)
    page = max(0, min(page, npage - 1))

    embed = discord.Embed(title='📒 %s 的帳號角色' % character_name, color=0x00bfff)
    # 只找到自己的情況實測佔 26.5%，使用者多半會以為是壞了，直接寫明原因。
    if data['total'] == 1:
        embed.description = (
            '只找到這一隻。同帳號角色是靠**聯盟冠軍名單**推出來的'
            '（同一份名單上的角色必定同帳號），沒啟用過冠軍就推不出連結。')

    for r in page_rows(rows, page):
        cp = cp_map.get(r['ocid']) if cp_map else None
        # 四行、不加欄位名：一行一件事，行首的圖示就是標題，省下來的寬度很有感
        # （欄位只有 embed 的三分之一寬）。因為沒有「：」可切，用不上 ansi.block，
        # 顏色在這裡自己上 —— 上藍的是「會變的那個數字」：經驗% 與成長量。
        # 等級、戰力、「7日」這些不會一直跳的維持預設色，職業用粗體當標頭。
        embed.add_field(
            # 燈號取代流水號：編號只是用來跟造型圖對位，但圖上本來就寫了名字，
            # 那個位置拿來放「近 7 日有沒有上線」更有用。
            name='%s %s' % ('🟢' if r['online'] else '🔴', r['name']),
            value=ansi.plain_block('\n'.join([
                ansi.bold(r['cls']),
                '🎖️%d(%s)' % (r['level'],
                               ansi.paint('%.1f%%' % r['exp_rate'],
                                          ansi.BRIGHT_BLUE)),
                '⬆️7日' + ansi.paint(row_growth(r, old_rates), ansi.BRIGHT_BLUE),
                '⚔️' + (ansi.paint(fmt_cp(cp), cp_color(cp))
                        if cp_map and r['ocid'] in cp_map else '...'),
            ])),
            inline=True)

    if image_name:
        embed.set_image(url='attachment://' + image_name)

    # 把燈號的人數寫進 footer，順便當圖例 —— 不然沒人知道紅綠是什麼意思
    online = sum(1 for r in rows if r['online'])
    foot = ['%d 隻角色' % data['total'],
            '🟢 %d 隻近 7 日登入' % online]
    if data.get('world'):
        foot.append(data['world'])
    if data.get('window'):
        foot.append('成長期間 %s ~ %s' % data['window'])
    foot.append('第 %d/%d 頁' % (page + 1, npage))
    if data.get('truncated'):
        foot.append('只顯示前 %d 隻' % MAX_CHARS)
    embed.set_footer(text='　|　'.join(foot))
    return embed
