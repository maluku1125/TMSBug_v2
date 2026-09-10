import discord
from discord import app_commands
from discord.ext import commands
from discord.errors import NotFound
import datetime
import json
import os
from functions.tinyfunctions import probably
from functions.SlashCommandManager import UseSlashCommand
from tmsapi.request import get_character_ocid, request_character_hexamatrix
from functions.database_manager import UserDataDB
from functions.CombineCharacter import combine_character_images

user_db = UserDataDB()

# 偷走的數量
stolen_fragments = 0


# 動態讀取「本專案自己」的 Data/HexaNodesCost.json（原本寫死 v2 路徑）
_HEXA_COST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Data', 'HexaNodesCost.json')
with open(_HEXA_COST_PATH, 'r', encoding='utf-8-sig') as f:
    HexaNodesCost = json.load(f)

# 核心對映：API 依序回傳，前2共用核心用 CommonNodes(6268)、第3顆(職業共通)用 CommonNodes3(4035)
# 技能x2、精通x4、強化x4、共用x2、職業共通x1


def build_solerda_embed(name, solerda, solerdafragment):
    """查詢角色六轉資料並產生進度 embed（查無角色/無六轉時回錯誤 embed）。"""
    ocid = get_character_ocid(name)
    if not ocid:
        return discord.Embed(title="查無角色", description=f"找不到角色「{name}」", color=0xff0000)

    hexa_data = request_character_hexamatrix(ocid)
    hexa_equipment = (hexa_data or {}).get('character_hexa_core_equipment')
    if not hexa_equipment:
        return discord.Embed(title="無六轉資料", description=f"角色「{name}」尚無 HEXA 核心資料", color=0xff0000)

    return CreateSolErdaProgress(name, hexa_equipment, solerda, solerdafragment)


class SolErdaSelectView(discord.ui.View):
    """多角色選擇畫面：顯示合成圖 + 下拉選單讓使用者選擇要查詢的角色"""
    def __init__(self, registered_characters: dict, solerda: int, solerdafragment: int):
        super().__init__(timeout=120)
        self.solerda = solerda
        self.solerdafragment = solerdafragment

        options = []
        for slot, char_name in sorted(registered_characters.items()):
            options.append(discord.SelectOption(label=char_name, value=char_name))

        select = discord.ui.Select(
            placeholder="選擇要查詢的角色...",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        selected_name = interaction.data['values'][0]
        try:
            await interaction.response.defer()
        except NotFound:
            return

        try:
            embed = build_solerda_embed(selected_name, self.solerda, self.solerdafragment)
            await interaction.edit_original_response(embed=embed, view=None, attachments=[])
            UseSlashCommand('calculatefragment', interaction)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"查詢碎片進度時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            try:
                await interaction.edit_original_response(embed=error_embed, view=None, attachments=[])
            except NotFound:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Slash_CreateSolErdaFragmentEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------碎碎-----------------
    @app_commands.command(name="solerda碎片進度", description="查詢角色六轉核心進度與距離全滿所需材料")
    @app_commands.describe(
            name = "角色名稱 (不輸入則使用已登錄的角色)",
            solerda = "目前持有的靈魂艾爾達（預設0）",
            solerdafragment = "目前持有的靈魂艾爾達碎片（預設0）"
        )
    async def calculatefragment(
        self, interaction: discord.Interaction,
        name: str = None,
        solerda: int = 0,
        solerdafragment: int = 0
        ):

        if name is None:
            user_id = str(interaction.user.id)
            all_chars = user_db.get_all_user_characters(user_id)
            registered = {slot: n for slot, n in all_chars.items() if n}

            # 無登錄角色 → 要求輸入
            if len(registered) == 0:
                await interaction.response.send_message(
                    "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                    ephemeral=True
                )
                return

            # 只有 1 個角色 → 直接查詢
            if len(registered) == 1:
                name = list(registered.values())[0]
            else:
                # 多個角色 → 顯示合成圖 + 下拉選單
                try:
                    await interaction.response.defer()
                except NotFound:
                    return

                select_view = SolErdaSelectView(registered, solerda, solerdafragment)
                combined_image = await combine_character_images(all_chars)

                embed = discord.Embed(
                    title="🎮 請選擇要查詢的角色",
                    color=0x00bfff
                )

                if combined_image:
                    file = discord.File(combined_image, filename="characters.png")
                    embed.set_image(url="attachment://characters.png")
                    await interaction.followup.send(embed=embed, view=select_view, file=file)
                else:
                    await interaction.followup.send(embed=embed, view=select_view)
                return

        try:
            await interaction.response.defer()
        except NotFound:
            return

        embed = build_solerda_embed(name, solerda, solerdafragment)
        UseSlashCommand('calculatefragment', interaction)
        await interaction.followup.send(embed=embed)


def extract_hexa_cores(hexa_equipment):
    """依 API 列舉順序，回傳各類型核心的 (等級, 名稱) 清單。"""
    cores = {'技能核心': [], '精通核心': [], '強化核心': [], '共用核心': []}
    for core in hexa_equipment or []:
        core_type = core.get('hexa_core_type')
        if core_type in cores:
            cores[core_type].append((core.get('hexa_core_level', 0) or 0, core.get('hexa_core_name', '') or ''))
    return cores


def extract_hexa_levels(hexa_equipment):
    """依 API 列舉順序，回傳各類型核心的等級清單。"""
    return {t: [lv for lv, _ in cs] for t, cs in extract_hexa_cores(hexa_equipment).items()}


def _pad(seq, n):
    seq = list(seq)[:n]
    return seq + [0] * (n - len(seq))


def _pad_cores(seq, n):
    seq = list(seq)[:n]
    return seq + [(0, '')] * (n - len(seq))


def _core_name_lines(cores, force_zero=False):
    """每行『等級：核心名稱』，數字右對齊寬2避免跑版。"""
    return '\n'.join(f"{(0 if force_zero else lv):>2}：{name or '—'}" for lv, name in cores)


# 共用核心開放日：未達開放日先隱藏（顯示與計算都不列入）
# 開放日移到 tmsapi.config，Bot 與網站共用同一份 —— 各寫一份的話，
# 開放當天一定有一邊忘了改，而且不會報錯，只會看到兩邊的完成度對不起來。
from tmsapi.config import hexa_common_open as common_cores_open   # noqa: E402


def build_core_pairs(levels, c2_open=True, c3_open=True):
    """把各類型等級對映到 (成本表key, 等級) 清單；未開放的共用核心不列入。"""
    skill   = _pad(levels['技能核心'], 2)
    mastery = _pad(levels['精通核心'], 4)
    boost   = _pad(levels['強化核心'], 4)
    common  = _pad(levels['共用核心'], 3)  # 共用1、共用2、共通核心3
    common_pairs = [("CommonNodes", common[0])]
    if c2_open:
        common_pairs.append(("CommonNodes", common[1]))
    if c3_open:
        common_pairs.append(("CommonNodes3", common[2]))
    pairs = (
        [("SkillNodes", l)   for l in skill] +
        [("MasteryNodes", l) for l in mastery] +
        [("BoostNodes", l)   for l in boost] +
        common_pairs
    )
    return pairs, skill, mastery, boost, common


def CalculateHexaMaterials(core_pairs):
    """回傳 (已花靈魂, 全滿靈魂, 已花碎片, 全滿碎片)。"""
    spent_sol = max_sol = spent_frag = max_frag = 0
    for table_key, level in core_pairs:
        sol  = HexaNodesCost[table_key]["solerda"]
        frag = HexaNodesCost[table_key]["solerdafragment"]
        lvl = max(0, min(int(level), 30))
        spent_sol  += sum(sol[:lvl])
        spent_frag += sum(frag[:lvl])
        max_sol    += sum(sol)
        max_frag   += sum(frag)
    return spent_sol, max_sol, spent_frag, max_frag


def Calculatefragment(
        SkillNodes1, SkillNodes2,
        MasteryNodes1, MasteryNodes2, MasteryNodes3, MasteryNodes4,
        BoostNode1, BoostNode2, BoostNode3, BoostNode4,
        CommonNode1,
        extrafragment,
        CommonNode2=-1, CommonNode3=-1
    ):
    """舊版純碎片計算（/character 六轉完成度% 仍使用）。"""

    maxtotal = 0
    totalcount = 0
    if SkillNodes1 >= 0 :
        maxtotal += 4500
        totalcount += sum(HexaNodesCost["SkillNodes"]["solerdafragment"][:SkillNodes1])
    if SkillNodes2 >= 0 :
        maxtotal += 4500
        totalcount += sum(HexaNodesCost["SkillNodes"]["solerdafragment"][:SkillNodes2])
    if MasteryNodes1 >= 0 :
        totalcount += sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes1])
        maxtotal += 2252
    if MasteryNodes2 >= 0 :
        totalcount += sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes2])
        maxtotal += 2252
    if MasteryNodes3 >= 0 :
        totalcount += sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes3])
        maxtotal += 2252
    if MasteryNodes4 >= 0 :
        totalcount += sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes4])
        maxtotal += 2252
    if BoostNode1 >= 0 :
        totalcount += sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode1])
        maxtotal += 3383
    if BoostNode2 >= 0 :
        totalcount += sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode2])
        maxtotal += 3383
    if BoostNode3 >= 0 :
        totalcount += sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode3])
        maxtotal += 3383
    if BoostNode4 >= 0 :
        totalcount += sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode4])
        maxtotal += 3383
    if CommonNode1 >= 0 :
        totalcount += sum(HexaNodesCost["CommonNodes"]["solerdafragment"][:CommonNode1])
        maxtotal += 6268
    if CommonNode2 >= 0 :
        totalcount += sum(HexaNodesCost["CommonNodes"]["solerdafragment"][:CommonNode2])
        maxtotal += 6268
    if CommonNode3 >= 0 :
        totalcount += sum(HexaNodesCost["CommonNodes3"]["solerdafragment"][:CommonNode3])
        maxtotal += 4035

    totalcount += extrafragment

    return totalcount, maxtotal


def CreateSolErdaProgress(character_name, hexa_equipment, solerda_stock=0, fragment_stock=0):
    global stolen_fragments

    c2_open, c3_open = common_cores_open()
    cores = extract_hexa_cores(hexa_equipment)
    levels = {t: [lv for lv, _ in cs] for t, cs in cores.items()}
    core_pairs, *_ = build_core_pairs(levels, c2_open, c3_open)
    spent_sol, max_sol, spent_frag, max_frag = CalculateHexaMaterials(core_pairs)

    # 各核心 (等級, 名稱)，共用核心未開放者隱藏
    skill_c   = _pad_cores(cores['技能核心'], 2)
    mastery_c = _pad_cores(cores['精通核心'], 4)
    boost_c   = _pad_cores(cores['強化核心'], 4)
    common_all = _pad_cores(cores['共用核心'], 3)
    common_c = [common_all[0]]
    if c2_open:
        common_c.append(common_all[1])
    if c3_open:
        common_c.append(common_all[2])

    frag_pct = (spent_frag / max_frag * 100) if max_frag else 0
    sol_pct = (spent_sol / max_sol * 100) if max_sol else 0

    # 進度條（以碎片進度為主）
    progress_length = 20
    progress = min(int((spent_frag / max_frag) * progress_length) if max_frag else 0, progress_length)
    progress_bar = '▓' * progress + '░' * (progress_length - progress)

    # 距離全滿還需
    need_sol = max(0, max_sol - spent_sol)
    need_frag = max(0, max_frag - spent_frag)
    short_sol = max(0, need_sol - solerda_stock)
    short_frag = max(0, need_frag - fragment_stock)

    # 愚人節機率
    now = datetime.datetime.now()
    probability = 0.99 if (now.month == 4 and now.day == 1) else 0.01

    if probably(probability):
        stolen_fragments += spent_frag
        embed = discord.Embed(title="**靈魂艾爾達碎片進度**", color=0x6f00d2)
        embed.add_field(name=f"{character_name} 原本的進度是 {frag_pct:.2f}%", value="但***邪惡***的蟲蟲把他們都偷走了", inline=False)
        embed.add_field(name="技能核心", value="```autohotkey\n" + _core_name_lines(skill_c, force_zero=True) + "\n```", inline=False)
        embed.add_field(name="精通核心", value="```autohotkey\n" + _core_name_lines(mastery_c, force_zero=True) + "\n```", inline=False)
        embed.add_field(name="強化核心", value="```autohotkey\n" + _core_name_lines(boost_c, force_zero=True) + "\n```", inline=False)
        embed.add_field(name="共用核心", value="```autohotkey\n" + _core_name_lines(common_c, force_zero=True) + "\n```", inline=False)
        embed.add_field(name=f"蟲蟲已經累計偷走了{stolen_fragments:,}個碎片", value="請保護好你的碎片", inline=False)
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
        return embed

    embed = discord.Embed(title="**靈魂艾爾達碎片進度**", color=0x6f00d2)
    embed.add_field(
        name=f"{character_name}",
        value=(
            "```autohotkey\n"
            f"碎片進度 : {spent_frag:,}/{max_frag:,} ({frag_pct:.2f}%)\n"
            f"靈魂進度 : {spent_sol:,}/{max_sol:,} ({sol_pct:.2f}%)\n"
            f"進度條　 : {progress_bar}\n"
            "```"
        ),
        inline=False,
    )

    embed.add_field(
        name="技能核心",
        value="```autohotkey\n" + _core_name_lines(skill_c) + "\n```",
        inline=False,
    )
    embed.add_field(
        name="精通核心",
        value="```autohotkey\n" + _core_name_lines(mastery_c) + "\n```",
        inline=False,
    )
    embed.add_field(
        name="強化核心",
        value="```autohotkey\n" + _core_name_lines(boost_c) + "\n```",
        inline=False,
    )
    embed.add_field(
        name="共用核心",
        value="```autohotkey\n" + _core_name_lines(common_c) + "\n```",
        inline=False,
    )

    embed.add_field(
        name="📦距離全滿還需",
        value=(
            "```autohotkey\n"
            f"靈魂艾爾達　　 : {need_sol:,}  (持有 {solerda_stock:,} → 還缺 {short_sol:,})\n"
            f"靈魂艾爾達碎片 : {need_frag:,}  (持有 {fragment_stock:,} → 還缺 {short_frag:,})\n"
            "```"
        ),
        inline=False,
    )

    embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
    return embed
