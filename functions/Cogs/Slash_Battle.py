import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import datetime
import time
import io
import os
import aiohttp
from PIL import Image

from functions.API_functions.API_Request_Character import (
    get_character_ocid, request_character_stat, request_character_hexamatrix,
    request_character_basic,
)
from functions.API_functions.CreateCharacterEmbed import apply_look_params
from functions.API_functions.CreateEXPTrackingEmbed import calculate_exp_growth, get_adjusted_datetime
from functions.API_functions.API_BattleRecord import get_record, add_result, get_quotes
from functions.database_manager import UserDataDB
from functions.SlashCommandManager import UseSlashCommand

user_db = UserDataDB()

COMBAT_POWER_FLOOR = 100_000_000  # 戰鬥力下限 1億(1E)

# 決鬥結束的姿勢（動作/表情）
WIN_POSE = ('A10', 'E09')   # heal + cheers
LOSE_POSE = ('A33', 'E03')  # dead + cry
DRAW_POSE = ('A00', 'E00')  # 預設站立

# 彩蛋：對象是 bot 本身(TMSBug_v2) 時，對手固定為「蟲蟲」
EASTER_EGG_BOT_ID = 1215617946601263125
BOSS_IMAGE_PATH = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\battle\\bug.png'


def _build_boss_fighter() -> dict:
    """彩蛋對手「蟲蟲」：戰鬥力 1 兆、骰固定 100、固定感言、固定圖片。"""
    return {
        'name': '蟲蟲',
        'cp': 1_000_000_000_000,        # 1兆
        'cp_raw': 1_000_000_000_000,
        'floored': False,
        'char_class': '???',
        'level': 0,
        'exp_bonus_pct': 100.0,
        'image': None,
        'image_path': BOSS_IMAGE_PATH,  # 本地固定圖（合成用）
        'skills': [('普通攻擊', 0), ('普通攻擊', 0)],
        'fixed_roll': 100,              # 骰固定 100
        'user_id': None,
        'boss_quote': '下次再來',
    }


def _format_num(n: int) -> str:
    """大數字以 兆/億/萬 顯示"""
    n = int(n)
    if n >= 10 ** 12:
        return f"{n / 10 ** 12:.2f}兆"
    if n >= 10 ** 8:
        return f"{n / 10 ** 8:.2f}億"
    if n >= 10 ** 4:
        return f"{n / 10 ** 4:.1f}萬"
    return f"{n:,}"


def _get_combat_power(stat_data: dict) -> int:
    if stat_data and stat_data.get('final_stat'):
        for s in stat_data['final_stat']:
            if s.get('stat_name') == '戰鬥力':
                try:
                    return int(s.get('stat_value') or 0)
                except (ValueError, TypeError):
                    return 0
    return 0


def _get_top_skills(hexa_data: dict, n: int = 2):
    """取技能核心等級最高的 n 招 (name, level)"""
    cores = (hexa_data or {}).get('character_hexa_core_equipment') or []
    skill_cores = [c for c in cores if c.get('hexa_core_type') == '技能核心']
    skill_cores.sort(key=lambda c: c.get('hexa_core_level', 0), reverse=True)
    return [(c.get('hexa_core_name', '未知技能'), c.get('hexa_core_level', 0))
            for c in skill_cores[:n]]


def _roll_hit(combat_power: int, forced_roll: int = None):
    """擲 d100 算單次傷害，回傳 dict(roll, mult, label, damage)。forced_roll 可固定骰值（彩蛋用）"""
    roll = forced_roll if forced_roll is not None else random.randint(1, 100)
    if roll == 100:
        mult, label = 100.0, '💥命中弱點'
    elif roll > 90:
        mult, label = 1.5, '✨爆擊'
    elif roll > 80:
        mult, label = 1.2, '✨爆擊'
    elif roll < 10:
        mult, label = 0.5, '💢失手'
    elif roll < 20:
        mult, label = 0.8, '💢失手'
    else:
        mult, label = 1.0, ''
    return {'roll': roll, 'mult': mult, 'label': label,
            'damage': int(combat_power * roll * mult)}


def _exp_growth_bonus(level: int, growth_7d: float) -> float:
    """7日成長經驗加乘(上限100%)：依等級級距決定『打滿100%所需的7日成長量』門檻。
    300等固定100%；275等以下不給。"""
    if level >= 300:
        return 100.0
    if level >= 295:
        threshold = 5
    elif level >= 290:
        threshold = 10
    elif level >= 285:
        threshold = 20
    elif level >= 280:
        threshold = 50
    elif level >= 275:
        threshold = 100
    else:
        return 0.0
    return 100.0 * min(growth_7d / threshold, 1.0)


def _calc_exp_multiplier(level: int, growth_7d: float) -> float:
    """經驗加乘(%) = 等級(上限300%) + 7日成長加乘(上限100%)"""
    return min(level, 300) + _exp_growth_bonus(level, growth_7d)


def _build_fighter(character_name: str):
    """查詢角色資料，組出對戰者。無法取得 ocid 時回 None。"""
    ocid = get_character_ocid(character_name)
    if not ocid:
        return None
    basic = request_character_basic(ocid) or {}
    stat = request_character_stat(ocid)
    hexa = request_character_hexamatrix(ocid)

    cp_raw = _get_combat_power(stat)
    cp = max(cp_raw, COMBAT_POWER_FLOOR)

    # 經驗加乘：等級% + 7日成長加乘
    level = int(basic.get('character_level') or 0)
    exp_rate = basic.get('character_exp_rate') or 0
    growth_7d = 0.0
    try:
        seven_days_ago = (get_adjusted_datetime() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        old_basic = request_character_basic(ocid, date=seven_days_ago) or {}
        old_level = old_basic.get('character_level')
        old_exp = old_basic.get('character_exp_rate')
        if old_level is not None:
            growth_7d = calculate_exp_growth(level, exp_rate, old_level, old_exp)
    except Exception:
        growth_7d = 0.0
    exp_bonus_pct = _calc_exp_multiplier(level, growth_7d)

    char_class = basic.get('character_class') or '未知'
    char_class = (char_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
                            .replace('大魔導士(火、毒)', '大魔導士（火、毒）'))

    skills = _get_top_skills(hexa, 2)
    while len(skills) < 2:
        skills.append(skills[-1] if skills else ('普通攻擊', 0))

    return {
        'name': character_name,
        'cp': cp,
        'cp_raw': cp_raw,
        'floored': cp_raw < COMBAT_POWER_FLOOR,
        'char_class': char_class,
        'level': level,
        'exp_bonus_pct': exp_bonus_pct,
        'image': basic.get('character_image'),
        'skills': skills,
    }


def _fight(fighter: dict):
    """兩招各打一擊，記錄明細與總傷害（經驗加乘乘入傷害）"""
    exp_mult = fighter.get('exp_bonus_pct', 100) / 100.0
    forced = fighter.get('fixed_roll')
    hits = []
    total = 0
    for skill_name, _lv in fighter['skills'][:2]:
        hit = _roll_hit(fighter['cp'], forced)
        hit['damage'] = int(hit['damage'] * exp_mult)
        hit['skill'] = skill_name
        hits.append(hit)
        total += hit['damage']
    fighter['hits'] = hits
    fighter['total'] = total
    return total


def _intro_value(fighter: dict) -> str:
    cp_line = _format_num(fighter['cp']) + ("（補至1億）" if fighter['floored'] else "")
    w, l = fighter.get('record', (0, 0))
    return (f"角色：{fighter['name']}\n"
            f"職業：{fighter['char_class']}\n"
            f"戰鬥力：{cp_line}\n"
            f"經驗加乘：{fighter.get('exp_bonus_pct', 0):g}%\n"
            f"{w}W {l}L")


def _battle_log(attacker: dict, defender: dict) -> str:
    """交錯排出回合 log：發起者(attacker)先攻，輪流出招"""
    lines = []
    order = [
        (attacker, attacker['hits'][0]),
        (defender, defender['hits'][0]),
        (attacker, attacker['hits'][1]),
        (defender, defender['hits'][1]),
    ]
    for i, (f, hit) in enumerate(order, 1):
        crit = f" {hit['label']}" if hit['label'] else ""
        lines.append(f"`{i}.` **{f['name']}** 使用【{hit['skill']}】"
                     f"🎲{hit['roll']}{crit} → 造成 **{_format_num(hit['damage'])}** 傷害")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(f"💥 {attacker['name']} 總傷害：**{_format_num(attacker['total'])}**")
    lines.append(f"💥 {defender['name']} 總傷害：**{_format_num(defender['total'])}**")
    return "\n".join(lines)


def _result_value(winner: dict, loser: dict) -> str:
    """結果欄文字：勝者宣告 + 勝/敗感言（大勝/大敗依傷害是否 >10倍；無設定不顯示）"""
    if winner is None:
        return "🤝 平手！"
    big = winner['total'] > 10 * max(loser['total'], 1)
    lines = [f"**{winner['name']}** 獲勝！" + ("　💥大勝利！" if big else "")]
    # 彩蛋角色用固定感言（無 user_id，不查 DB）
    win_q = winner.get('boss_quote') or get_quotes(winner.get('user_id'))['big_win' if big else 'win']
    lose_q = loser.get('boss_quote') or get_quotes(loser.get('user_id'))['big_lose' if big else 'lose']
    if win_q:
        lines.append(f"{winner['name']}：{win_q}")
    if lose_q:
        lines.append(f"{loser['name']}：{lose_q}")
    return "\n".join(lines)


async def _compose_duel_image(left, left_pose, right, right_pose,
                              left_mirror=False, right_mirror=False):
    """把雙方依指定姿勢合成成一張並排圖片，回傳 BytesIO（失敗回 None）。
    每側來源可為角色外型 URL（套姿勢）或本地圖檔 image_path（彩蛋蟲蟲，不套姿勢）。
    left_mirror/right_mirror 為 True 時將該側左右鏡像。"""
    # 決定每側影像來源：('file', 路徑) / ('url', 套姿勢後的URL) / (None, None)
    sources = []
    for fighter, pose in ((left, left_pose), (right, right_pose)):
        if fighter.get('image_path'):
            sources.append(('file', fighter['image_path']))
        elif fighter.get('image'):
            sources.append(('url', apply_look_params(fighter['image'], action=pose[0], emotion=pose[1])))
        else:
            sources.append((None, None))

    if all(kind is None for kind, _ in sources):
        return None

    # 下載 URL 來源
    fetched = [None, None]
    try:
        async with aiohttp.ClientSession() as session:
            for i, (kind, val) in enumerate(sources):
                if kind == 'url':
                    async with session.get(val) as resp:
                        if resp.status == 200:
                            fetched[i] = await resp.read()
    except Exception:
        pass

    mirrors = [left_mirror, right_mirror]

    def _compose():
        images = [None, None]
        for i, (kind, val) in enumerate(sources):
            try:
                if kind == 'file' and os.path.exists(val):
                    images[i] = Image.open(val).convert('RGBA')
                elif kind == 'url' and fetched[i]:
                    images[i] = Image.open(io.BytesIO(fetched[i])).convert('RGBA')
            except Exception:
                images[i] = None
        if not any(images):
            return None
        cell_w = max((im.width for im in images if im), default=96)
        cell_h = max((im.height for im in images if im), default=96)
        gap = 24
        canvas = Image.new('RGBA', (cell_w * 2 + gap, cell_h), (0, 0, 0, 0))
        for idx, im in enumerate(images):
            if not im:
                continue
            if mirrors[idx]:
                im = im.transpose(Image.FLIP_LEFT_RIGHT)
            x = idx * (cell_w + gap) + (cell_w - im.width) // 2
            y = (cell_h - im.height) // 2
            canvas.paste(im, (x, y), im)
        buf = io.BytesIO()
        canvas.save(buf, format='PNG')
        buf.seek(0)
        return buf

    return await asyncio.to_thread(_compose)


class Slash_Battle(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="battle對戰", description="與其他玩家的本尊角色決鬥（實驗性娛樂功能）")
    @app_commands.describe(target="要決鬥的對象（需已用 /setting 綁定 1本）")
    async def battle(self, interaction: discord.Interaction, target: discord.Member):
        start_time = time.time()

        # 彩蛋：對戰 bot 本身 → 對手固定為「蟲蟲」
        is_boss = target.id in (EASTER_EGG_BOT_ID, interaction.client.user.id)

        if target.bot and not is_boss:
            await interaction.response.send_message("❌ 不能對機器人發起決鬥。", ephemeral=True)
            return
        # 測試階段：先允許與自己對戰（之後要禁止再把下面恢復）
        # if target.id == interaction.user.id:
        #     await interaction.response.send_message("❌ 不能跟自己對戰。", ephemeral=True)
        #     return

        me_name = user_db.get_user_character_slot(str(interaction.user.id), 1)
        if not me_name:
            await interaction.response.send_message(
                "❌ 你尚未綁定本尊角色，請先用 `/setting設定 type:角色 type2:1本` 設定。", ephemeral=True)
            return
        opp_name = None if is_boss else user_db.get_user_character_slot(str(target.id), 1)
        if not is_boss and not opp_name:
            await interaction.response.send_message(
                f"❌ {target.mention} 尚未綁定本尊角色（1本），無法決鬥。", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            me = await asyncio.to_thread(_build_fighter, me_name)
            opp = _build_boss_fighter() if is_boss else await asyncio.to_thread(_build_fighter, opp_name)
        except Exception as e:
            await interaction.followup.send(f"❌ 查詢角色資料時發生錯誤：{e}")
            UseSlashCommand('battle', interaction, time.time() - start_time, False)
            return

        if not me:
            await interaction.followup.send(f"❌ 找不到你的角色 `{me_name}`。")
            return
        if not opp:
            await interaction.followup.send(f"❌ 找不到對象的角色 `{opp_name}`。")
            return

        # 標記 Discord user_id（感言以 user_id 為 key）
        me['user_id'] = str(interaction.user.id)
        opp['user_id'] = str(target.id)

        # 開戰（發起者 me 先攻）
        _fight(me)
        _fight(opp)

        if me['total'] > opp['total']:
            winner, loser = me, opp
            me_pose, opp_pose = WIN_POSE, LOSE_POSE
        elif opp['total'] > me['total']:
            winner, loser = opp, me
            me_pose, opp_pose = LOSE_POSE, WIN_POSE
        else:
            winner, loser = None, None
            me_pose, opp_pose = DRAW_POSE, DRAW_POSE

        # 記錄戰績（以角色暱稱為 key；平手不計）。同名角色只計一次避免自打灌水
        if winner is not None and me['name'] != opp['name']:
            add_result(me['name'], winner is me)
            add_result(opp['name'], winner is opp)
        me['record'] = get_record(me['name'])
        opp['record'] = get_record(opp['name'])

        # Embed
        embed = discord.Embed(
            title="⚔️ 決鬥",
            description=f"{interaction.user.mention} 對 {target.mention} 發起決鬥！",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(),
        )
        embed.add_field(name=f"{interaction.user.display_name}", value=_intro_value(me), inline=True)
        embed.add_field(name=f"{target.display_name}", value=_intro_value(opp), inline=True)
        embed.add_field(name="📜 戰鬥流程", value=_battle_log(me, opp), inline=False)
        embed.add_field(name="🏆 結果", value=_result_value(winner, loser), inline=False)
        embed.set_footer(text=f"{'-' * 19}TMS對戰系統 v1.1.0{'-' * 19}")

        # 合成決鬥圖：發起方(me)固定在左、左邊一律左右鏡像；對象(opp)固定在右
        duel_file = None
        try:
            buf = await _compose_duel_image(
                me, me_pose, opp, opp_pose,
                left_mirror=True,
                right_mirror=False,
            )
            if buf:
                duel_file = discord.File(buf, filename="duel.png")
                embed.set_image(url="attachment://duel.png")
        except Exception:
            duel_file = None

        if duel_file:
            await interaction.followup.send(embed=embed, file=duel_file)
        else:
            await interaction.followup.send(embed=embed)
        UseSlashCommand('battle', interaction, time.time() - start_time, True)


async def setup(client: commands.Bot):
    await client.add_cog(Slash_Battle(client))
