import discord
from discord import app_commands
from discord.errors import NotFound
from discord.ext import commands
import datetime
from discord.app_commands import Choice

from functions.tinyfunctions import probably

from functions.CreateBossDataEmbed import Create_Boss_Data_Embed, get_difficulty_value, boss_data
from functions.SlashCommandManager import UseSlashCommand

# 一個指令一份 BOSS 清單。slash 指令的 Choice 與面板的下拉選單共用同一份 ——
# 各寫一份的話，加一隻王一定有一邊忘了加。順序沿用原本 Choice 的順序。
EASY_BOSSES = [
    '巴洛古', '殘暴炎魔', '梅格耐斯', '希拉', '卡翁', '拉圖斯', '森蘭丸',
    '比艾樂', '斑斑', '血腥皇后', '貝倫', '凡雷恩', '闇黑龍王', '阿卡伊農',
    '皮卡啾', '西格諾斯', '培羅德', '濃姬',
]
ARC_BOSSES = [
    '史烏', '戴米安', '露希妲', '威爾', '戴斯克', '真希拉', '頓凱爾',
    '黑魔法師', '守護天使綠水靈', '瑪麗西亞',
]
AUT_BOSSES = [
    '受選的賽蓮', '監視者卡洛斯', '咖凌', '林波', '巴德利斯',
    '最初的敵對者', '璀璨的凶星', '尤比太',
]

# 難度參數的四個選項。easy/normal/hard/extreme 對到哪些中文難度名稱是
# CreateBossDataEmbed.translate_difficulty 在管，這裡只留顯示用的文字。
DIFFICULTY_PARAM = [('簡單', 'easy'), ('普通', 'normal'),
                    ('困難/混沌', 'hard'), ('極限', 'extreme')]
DIFFICULTY_LABELS = {value: name for name, value in DIFFICULTY_PARAM}

# 沒給難度時的預設。沒有「普通」的是巴洛古（只有簡單）、培羅德（初級～頂級
# 模式）、黑魔法師（困難／終極），那幾隻取最低難度
DEFAULT_DIFFICULTIES = ('普通', '中級模式')

VIEW_TIMEOUT = 300          # 面板活 5 分鐘，逾時把元件變灰（同 RankingView）


def _choices(names):
    """每次生一份新的 Choice 清單：三支指令不要共用同一個 list 物件。"""
    return [Choice(name=n, value=n) for n in names]


def _difficulty_choices():
    return [Choice(name=name, value=value) for name, value in DIFFICULTY_PARAM]


def _difficulties(boss_name):
    """這隻王有哪幾個難度，由低到高 —— BossData.json 的 key 本來就這樣排。"""
    return list(boss_data[boss_name].keys())


def _default_difficulty(boss_name):
    ds = _difficulties(boss_name)
    for d in DEFAULT_DIFFICULTIES:
        if d in ds:
            return d
    return ds[0]


def _resolve_difficulty(boss_name, difficulty):
    """指令參數的 easy/normal/hard/extreme → 這隻王真的有的難度名稱。

    回 (難度名稱, 要附在訊息上的說明或 None)。對不上難度時原本是直接回
    「{王} 沒有這個難度」就結束，使用者得重打一次指令；現在面板上就看得到
    有哪幾個難度，不如先把資料給他，按鈕點一下就到位。
    """
    if difficulty is None:
        return _default_difficulty(boss_name), None
    index, indexerror = get_difficulty_value(boss_name, difficulty)
    if indexerror == "False":
        return _difficulties(boss_name)[index], None
    fallback = _default_difficulty(boss_name)
    label = DIFFICULTY_LABELS.get(difficulty, difficulty)
    return fallback, f"ℹ️ {boss_name} 沒有「{label}」難度，已顯示「{fallback}」"


class BossDataView(discord.ui.View):
    """BOSS 資料面板：按鈕換難度、下拉選單換王（2026-11-01）。

    難度按鈕只畫這隻王真的有的那幾個（直接讀 BossData.json 的 key），
    所以培羅德（初級～頂級模式）、黑魔法師（只有困難／終極）也都點得到 ——
    指令參數那套 easy/normal/hard/extreme 對照表碰到這兩隻會回「沒有這個難度」。

    誰都可以按，不限發指令的人：BOSS 資料是公開的靜態資料，一桌人輪流翻
    比各自打一次指令省事（同 RankingView、SolErdaSelectView 的做法）。
    """

    def __init__(self, bosses, boss_name, difficulty):
        super().__init__(timeout=VIEW_TIMEOUT)
        self.bosses = bosses
        self.boss_name = boss_name
        self.difficulty = difficulty
        self.message = None         # 逾時要把元件變灰，得留著訊息參照
        self._build()

    def embed(self):
        index = _difficulties(self.boss_name).index(self.difficulty)
        return Create_Boss_Data_Embed(self.boss_name, index)

    def _build(self):
        """難度按鈕會跟著王一起換，所以每次重畫整組元件。

        custom_id 用「第幾個難度」而不是難度名稱：discord.py 的 ViewStore
        是用 (訊息, custom_id) 記住每個元件的，名稱當 id 的話每換一隻王
        就多留一組對不到任何按鈕的舊紀錄。
        """
        self.clear_items()
        for position, d in enumerate(_difficulties(self.boss_name)):
            current = d == self.difficulty
            button = discord.ui.Button(
                label=d, custom_id=f"bossdiff:{position}", row=0,
                style=(discord.ButtonStyle.primary if current
                       else discord.ButtonStyle.secondary),
                disabled=current)   # 現在這個難度不給按，順便當「你在這」
            button.callback = self._on_difficulty
            self.add_item(button)

        select = discord.ui.Select(
            placeholder="切換BOSS…", custom_id="bossselect", row=1,
            options=[discord.SelectOption(label=n, value=n,
                                          default=n == self.boss_name)
                     for n in self.bosses],
        )
        select.callback = self._on_boss
        self.add_item(select)

    async def _on_difficulty(self, interaction: discord.Interaction):
        # 別人先換過王的話，手上這份畫面可能已經過期（按鈕比現在這隻王多），
        # 所以位置要夾在範圍內
        position = int(interaction.data['custom_id'].split(':', 1)[1])
        ds = _difficulties(self.boss_name)
        self.difficulty = ds[min(position, len(ds) - 1)]
        await self._refresh(interaction)

    async def _on_boss(self, interaction: discord.Interaction):
        self._switch_boss(interaction.data['values'][0])
        await self._refresh(interaction)

    def _switch_boss(self, new_name):
        """換王時盡量留在同一個難度。

        同名難度優先；沒有同名的就留在同一個順位（清單由低到高），超出
        就取最高 —— 從咖凌「極限」換到林波（普通／困難）會落在困難，
        而不是掉回最低難度。
        """
        old = _difficulties(self.boss_name)
        position = old.index(self.difficulty) if self.difficulty in old else 0
        new = _difficulties(new_name)
        self.boss_name = new_name
        if self.difficulty not in new:
            self.difficulty = new[min(position, len(new) - 1)]

    async def _refresh(self, interaction: discord.Interaction):
        self._build()
        try:
            await interaction.response.edit_message(embed=self.embed(), view=self)
        except NotFound:        # 互動已逾時（10062），面板留在原狀就好
            pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # 只改 view 物件畫面上不會變 —— 要把訊息本身也改掉元件才真的變灰
        if self.message is None:
            return
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass


async def send_boss_panel(interaction, bosses, bossname, log_as,
                          difficulty=None, joke=False):
    """送出 BOSS 面板。三支指令只差在下拉選單裡的王清單。"""
    # 蟲蟲彩蛋照原樣送，但不掛面板：面板上的王會跟圖上的王對不起來
    if joke:
        await interaction.response.send_message(embed=Create_Boss_Data_Embed("蟲蟲", 0))
        UseSlashCommand(log_as, interaction)
        return

    difficulty_name, note = _resolve_difficulty(bossname, difficulty)
    view = BossDataView(bosses, bossname, difficulty_name)
    await interaction.response.send_message(content=note, embed=view.embed(), view=view)
    try:
        view.message = await interaction.original_response()
    except discord.HTTPException:
        pass
    # 記錄是同步寫 sqlite，放在回覆之後才不會吃掉互動的 3 秒
    UseSlashCommand(log_as, interaction)


class Slash_CreateBossDataEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------BOSS-----------------
    @app_commands.command(name="easyboss里程周王", description="查詢史烏、戴米安以前的BOSS資料")
    @app_commands.describe(bossname = "哪一隻", difficulty = "難度（不選就用普通，之後按下方按鈕切換）")
    @app_commands.choices(
        bossname = _choices(EASY_BOSSES),
        difficulty = _difficulty_choices(),
    )
    async def easybossinfo(self, interaction: discord.Interaction, bossname: str, difficulty: str = None):
        await send_boss_panel(interaction, EASY_BOSSES, bossname,
                              'easybossinfo', difficulty)

    @app_commands.command(name="bossarc困王", description="查詢ARC區的BOSS資料")
    @app_commands.describe(bossname = "哪一隻", difficulty = "難度（不選就用普通，之後按下方按鈕切換）")
    @app_commands.choices(
        bossname = _choices(ARC_BOSSES),
        difficulty = _difficulty_choices(),
    )
    async def arcbossinfo(self, interaction: discord.Interaction, bossname: str, difficulty: str = None):
        await send_boss_panel(interaction, ARC_BOSSES, bossname,
                              'arcbossinfo', difficulty, joke=probably(0.001))

    @app_commands.command(name="bossaut困王", description="查詢AUT區的BOSS資料")
    @app_commands.describe(bossname = "哪一隻", difficulty = "難度（不選就用普通，之後按下方按鈕切換）")
    @app_commands.choices(
        bossname = _choices(AUT_BOSSES),
        difficulty = _difficulty_choices(),
    )
    async def autbossinfo(self, interaction: discord.Interaction, bossname: str, difficulty: str = None):
        await send_boss_panel(interaction, AUT_BOSSES, bossname,
                              'autbossinfo', difficulty, joke=probably(0.001))


# 讓這支可以被 load_extension／reload_extension 熱抽換（2026-09-20）。
# setup_hook 改用 load_extension 之後，後台就能單獨重載這一個 cog，
# 不必為了改一行文案重啟整台 Bot（5 個 shard、近 5,000 個伺服器要重連）。
async def setup(client: commands.Bot):
    await client.add_cog(Slash_CreateBossDataEmbed(client))
