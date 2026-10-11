import re
import os
import json
import asyncio
import datetime
import urllib.parse
import requests
import discord
from discord.ext import commands, tasks
from concurrent.futures import ThreadPoolExecutor

from functions.database_manager import GuildFunctionDB
from functions.ConcurrentBroadcast import broadcast_to_channels

# 命中任一關鍵字即視為「維護類」。
#
# ⚠️ 用詞根而不是完整詞。原本是「維護公告 / 開機公告 / 關機公告 /
# 手動更新下載開放通知」四個完整詞，結果 2026-10-05 的
# 《1007(三) 例行維護時間調整公告》一個都不命中 —— 它是「維護時間調整公告」，
# 不是「維護公告」。那則在舊版是直接被丟掉、連紀錄都沒有的。
# 改成詞根之後，同一份 150 筆實測樣本多收 4 筆（都是改版維護時間調整、
# 登入服務維護），而商城分類(72)的 74 筆**零誤判**。
KEYWORDS = ("維護", "開機", "關機", "更新下載", "停機", "延後")

# 官網公告的分類（回應欄位 bullentinCatId）。2026-10-04 抓 150 筆實測：
#   67  例行維護開機／關機公告            29/29 是維護類
#   68  異常說明、制裁、已知問題、更新下載   25/45 是維護類
#   72  皇家美容院、黃金蘋果、閃亮彗星…    0/74  是維護類（純商城活動）
# 所以「維護類」的判準是 catId=67 或標題命中關鍵字 —— 兩個都看，因為 68
# 裡面混了維護也混了非維護，單看分類會漏掉「手動更新下載開放通知」。
CAT_LABEL = {"67": "維護", "68": "公告", "72": "商城／活動"}
CAT_COLOR = {"67": 0xff9900, "68": 0x3498db, "72": 0x9b59b6}

# 只有這些分類會附圖。維護類貼一張大圖只會把「幾點關幾點開」洗到下面去，
# 而且官方本來就不放圖（2026-10-08 抽樣：72 類 6/6 有圖、68 類 1/6、67 類 0/6）。
# 這個清單同時也是「要不要多打一支 API」的開關 —— 不在清單裡的根本不去抓。
IMAGE_CATS = ("72",)

# 一次抓幾筆。原本是 10 —— 只挑維護類時夠用，但改版日的商城公告常常
# 一次上十幾筆，10 筆會在兩輪之間被擠掉而且**不會有任何錯誤**。
PAGE_SIZE = 30

# 一輪最多發幾則。超過就視為「離線太久／第一次看到這麼後面的清單」，
# 只把 ID 記起來、不發 —— 否則 Bot 停機一天回來會對 40 個頻道連噴十幾則。
# （PageSize 從 10 改成 30 的那一次實測是 0 筆，但那是運氣，不是保證。）
BURST_LIMIT = 10

TMS_MAIN_URL = "https://maplestory.beanfun.com/main"
TMS_BULLETIN_PROXY_URL = "https://maplestory.beanfun.com/main?handler=BulletinProxy"
TMS_BULLETIN_URL = "https://maplestory.beanfun.com/bulletin?bid={bid}"
TMS_BULLETIN_DETAIL_URL = "https://maplestory.beanfun.com/bulletin?handler=BulletinDetail"

CSRF_RE = re.compile(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"')
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

# 已通知公告 ID 存放於專案外的 log 目錄（避免污染 git），檔名帶專案名使 beta/v2 各自獨立
_LOG_DIR = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function'
_PROJECT_NAME = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_SEEN_PATH = os.path.join(_LOG_DIR, f'ServerAnnounce_seen_{_PROJECT_NAME}.json')
_SEEN_LIMIT = 300  # 保留最近 N 筆，避免無限成長


def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')


def _session():
    """帶誠實 UA 的 session。

    冒充瀏覽器是一回事，對方擋不擋得住是另一回事。
    2026-10-04 實測官網照收，拿得到 CSRF token 也拿得到公告清單。
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "TMSBug/2.0 (Discord bot for MapleStory TW; +https://maple-cube.com)"})
    return session


def _csrf(session):
    """從首頁挖 CSRF token。公告清單與公告內文兩支 handler 都吃這一個。"""
    resp = session.get(TMS_MAIN_URL, timeout=15)
    resp.raise_for_status()
    match = CSRF_RE.search(resp.text)
    return match.group(1) if match else None


def _valid_image_url(url) -> bool:
    """能不能安全地塞進 embed。

    ⚠️ 這個檢查不是潔癖：格式壞掉的網址會讓 Discord 回 400，而那是在
    `channel.send` 的時候爆 —— 一張圖的網址有問題，整則公告對**所有**
    頻道都發不出去。圖是附加價值，不值得拿整則公告去賭。
    （404 的網址沒關係，Discord 只會不顯示圖，不會報錯。）
    """
    if not url or len(url) > 1900:
        return False
    try:
        p = urllib.parse.urlparse(url)
    except ValueError:
        return False
    return p.scheme in ('http', 'https') and '.' in p.netloc


def fetch_bulletin_images(bids):
    """抓每則公告內文裡的第一張圖。回 {bid: 圖片網址}，拿不到就不放那個鍵。

    清單 API **不回圖**（mainPicture / thumbnail 實測 150 筆全是 null），
    公告內頁又是 JS 算出來的空殼（整頁只有一張 logo），圖只在
    `bulletin?handler=BulletinDetail` 回的 content HTML 裡。

    2026-10-08 抽樣實測：商城／活動(72) 6/6 有圖、一般公告(68) 1/6、
    維護(67) 0/6 —— 所以維護類幾乎都不會有圖，這是正常的。
    """
    out = {}
    if not bids:
        return out
    try:
        session = _session()
        token = _csrf(session)
        if not token:
            return out
    except Exception as e:                                  # noqa: BLE001
        print(f'{get_now_HMS()}, ServerAnnounce: 取圖時拿不到 token：{e}')
        return out

    for bid in bids:
        try:
            r = session.post(TMS_BULLETIN_DETAIL_URL, data={'Bid': bid},
                             headers={'X-CSRF-TOKEN': token}, timeout=15)
            r.raise_for_status()
            content = r.json()['data']['myDataSet']['table'].get('content') or ''
        except Exception as e:                              # noqa: BLE001
            print(f'{get_now_HMS()}, ServerAnnounce: 公告 {bid} 取內文失敗：{e}')
            continue
        for url in IMG_RE.findall(content):
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://maplestory.beanfun.com' + url
            if _valid_image_url(url):
                out[bid] = url
                break
    return out


def fetch_bulletins():
    """同步抓取官網公告列表（在執行緒中跑）。回傳 list 或 None。"""
    session = _session()
    token = _csrf(session)
    if not token:
        print(f"{get_now_HMS()}, ServerAnnounce: CSRF token not found")
        return None

    # ⚠️ Kind 這個參數**沒有作用**（2026-10-04 實測 Kind=0~5 回完全一樣的清單），
    # 分類要看回應裡的 bullentinCatId。留著是因為官網自己的 JS 也這樣送。
    resp2 = session.post(
        TMS_BULLETIN_PROXY_URL,
        data=f"Kind=0&Page=1&method=0&PageSize={PAGE_SIZE}",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": token,
        },
        timeout=15,
    )
    resp2.raise_for_status()
    return resp2.json()["data"]["myDataSet"]["table"]


def is_maintenance(item) -> bool:
    """這則是不是「開關機／維護」類。

    兩個判準取聯集：分類 67 全部都是維護類，而 68 裡面混了維護與非維護
    （「手動更新下載開放通知」就在 68），所以標題關鍵字不能省。
    """
    if str(item.get("bullentinCatId") or "") == "67":
        return True
    return any(k in (item.get("title") or "") for k in KEYWORDS)


def bulletin_link(item):
    """官方 JS 的組法：有 urlLink 用 urlLink，否則 bulletin?bid={id}"""
    url_link = item.get("urlLink")
    if url_link:
        # urlLink 為官網 href，可能是相對路徑；非 http 開頭時補上官網域名，避免 embed URL 無效
        if not url_link.startswith("http"):
            url_link = "https://maplestory.beanfun.com/" + url_link.lstrip("/")
        return url_link
    return TMS_BULLETIN_URL.format(bid=item.get("bullentinId"))


class Loop_ServerAnnounce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = GuildFunctionDB()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.seen_ids = self._load_seen()
        self.check_announcements.start()

    def cog_unload(self):
        self.check_announcements.cancel()
        self.executor.shutdown(wait=False)

    # ---------- 已通知 ID 持久化 ----------
    def _load_seen(self):
        try:
            with open(_SEEN_PATH, 'r', encoding='utf-8') as f:
                return list(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return None  # None = 首次啟動，之後以當前公告為基準

    def _save_seen(self):
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
            with open(_SEEN_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.seen_ids[-_SEEN_LIMIT:], f)
        except Exception as e:
            print(f"{get_now_HMS()}, ServerAnnounce: save seen failed: {e}")

    # ---------- 主迴圈 ----------
    @tasks.loop(minutes=30)
    async def check_announcements(self):
        loop = asyncio.get_event_loop()
        try:
            table = await loop.run_in_executor(self.executor, fetch_bulletins)
        except Exception as e:
            print(f"{get_now_HMS()}, ServerAnnounce: fetch failed: {e}")
            return
        if not table:
            return

        # tasks.loop 遇未捕捉例外會停止，此處整段保護以確保 30 分鐘循環持續運作
        try:
            current_ids = [item.get("bullentinId") for item in table]

            # 首次啟動：以當前公告為基準，不回放舊公告
            if self.seen_ids is None:
                self.seen_ids = current_ids
                self._save_seen()
                print(f"{get_now_HMS()}, ServerAnnounce: baseline set ({len(current_ids)} bulletins)")
                return

            # 不再在這裡過濾：全部的新公告都往下走，由 _broadcast 依分類
            # 決定送給誰（只訂維護的 vs 全收的）
            new_items = [item for item in table
                         if item.get("bullentinId") not in self.seen_ids]

            # 全部現有 ID 標記為已看（含不符關鍵字的，避免下輪重比）
            self.seen_ids += [i for i in current_ids if i not in self.seen_ids]
            self.seen_ids = self.seen_ids[-_SEEN_LIMIT:]
            self._save_seen()

            if not new_items:
                return

            if len(new_items) > BURST_LIMIT:
                print(f'{get_now_HMS()}, ServerAnnounce: 一次冒出 {len(new_items)} 則新公告，'
                      f'判定為離線太久，只記錄不發送')
                return

            # 圖要另外打一支 handler，所以只對「要發、而且是會附圖的分類」去抓
            images = await loop.run_in_executor(
                self.executor, fetch_bulletin_images,
                [i.get("bullentinId") for i in new_items
                 if str(i.get("bullentinCatId") or "") in IMAGE_CATS])

            # 列表由新到舊，發送時反轉成由舊到新
            for item in reversed(new_items):
                await self._broadcast(item, images.get(item.get("bullentinId")))
        except Exception as e:
            print(f"{get_now_HMS()}, ServerAnnounce: cycle error: {e}")

    @check_announcements.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """被踢出伺服器就把該台的訂閱清掉 —— 這是最乾淨的「確定死了」訊號，
        比等推播失敗再猜準得多。"""
        if self.db.remove_announce_channel(str(guild.id)):
            print(f'{get_now_HMS()}, ServerAnnounce: 已離開 {guild.name}'
                  f'（{guild.id}），移除其公告訂閱')

    # ---------- 發送 ----------
    async def _broadcast(self, item, image_url=None):
        title = item.get("title") or "官方公告"
        link = bulletin_link(item)
        cat = str(item.get("bullentinCatId") or "")
        maint = is_maintenance(item)

        embed = discord.Embed(
            title=f"{'🔧' if maint else '📢'} {title}",
            url=link,
            color=CAT_COLOR.get(cat, 0x95a5a6),
        )
        label = CAT_LABEL.get(cat, "其他")
        start = item.get("startDate") or ""
        embed.set_footer(text=f"新楓之谷官方公告・{label}" + (f"・{start}" if start else ""))
        if image_url and _valid_image_url(image_url):
            embed.set_image(url=image_url)

        # 維護類：所有訂閱者都收。其他：只給選了「全收」的伺服器。
        configs = self.db.get_announce_targets("maint" if maint else cat)
        targets = list(configs.items())
        if not targets:
            print(f"{get_now_HMS()}, ServerAnnounce: '{title[:40]}'（{label}）沒有訂閱者，略過")
            return

        # 並發廣播（含每頻道一次重試）
        success, failures = await broadcast_to_channels(
            self.bot, targets, lambda g, c: {'embed': embed}, concurrency=20,
            kind='announce', label=title[:80]
        )

        print(f"{get_now_HMS()}, ServerAnnounce: '{title}' sent to {success} channels, {len(failures)} failed")

        # 只有「確定死了」才自動退訂。
        # channel_deleted 是向 API 問過之後拿到的 404（Discord 的 ID 不會重用，
        # 所以那個頻道永遠不會回來）。**不要**拿 channel_not_found 當依據 ——
        # 那只是本地快取沒命中，頻道其實還在，照那個刪會把好端端的伺服器退訂。
        for gid, cid, err in failures:
            if err == 'channel_deleted' and self.db.remove_announce_channel(gid):
                print(f'{get_now_HMS()}, ServerAnnounce: 頻道 {cid} 已不存在，'
                      f'自動移除伺服器 {gid} 的公告訂閱')
