import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import datetime
import time
import io
import aiohttp
from PIL import Image

from functions.API_functions.API_Request_Character import (
    get_character_ocid, request_character_stat, request_character_hexamatrix,
    request_character_basic,
)
from functions.API_functions.CreateCharacterEmbed import apply_look_params
from functions.database_manager import UserDataDB
from functions.SlashCommandManager import UseSlashCommand

user_db = UserDataDB()

COMBAT_POWER_FLOOR = 100_000_000  # 戰鬥力下限 1億(1E)

# 決鬥結束的姿勢（動作/表情）
WIN_POSE = ('A10', 'E09')   # heal + cheers
LOSE_POSE = ('A33', 'E03')  # dead + cry
DRAW_POSE = ('A00', 'E00')  # 預設站立


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


def _roll_hit(combat_power: int):
    """擲 d100 算單次傷害，回傳 dict(roll, mult, label, damage)"""
    roll = random.randint(1, 100)
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
        'image': basic.get('character_image'),
        'skills': skills,
    }


def _fight(fighter: dict):
    """兩招各打一擊，記錄明細與總傷害"""
    hits = []
    total = 0
    for skill_name, _lv in fighter['skills'][:2]:
        hit = _roll_hit(fighter['cp'])
        hit['skill'] = skill_name
        hits.append(hit)
        total += hit['damage']
    fighter['hits'] = hits
    fighter['total'] = total
    return total


def _intro_value(fighter: dict) -> str:
    cp_line = _format_num(fighter['cp']) + ("（補至1億）" if fighter['floored'] else "")
    return (f"角色：{fighter['name']}\n"
            f"職業：{fighter['char_class']}\n"
            f"戰鬥力：{cp_line}")


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


async def _compose_duel_image(left, left_pose, right, right_pose,
                              left_mirror=False, right_mirror=False):
    """把雙方依指定姿勢合成成一張並排圖片，回傳 BytesIO（失敗回 None）。
    left_mirror/right_mirror 為 True 時將該側左右鏡像（戰敗方面向對手）。"""
    if not (left.get('image') and right.get('image')):
        return None
    urls = [
        apply_look_params(left['image'], action=left_pose[0], emotion=left_pose[1]),
        apply_look_params(right['image'], action=right_pose[0], emotion=right_pose[1]),
    ]
    mirrors = [left_mirror, right_mirror]
    images = []
    try:
        async with aiohttp.ClientSession() as session:
            for url in urls:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        images.append(Image.open(io.BytesIO(data)).convert('RGBA'))
                    else:
                        images.append(None)
    except Exception:
        return None

    if not any(images):
        return None

    def _compose():
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

        if target.bot:
            await interaction.response.send_message("❌ 不能對機器人發起決鬥。", ephemeral=True)
            return
        # 測試階段：先允許與自己對戰（之後要禁止再把下面恢復）
        # if target.id == interaction.user.id:
        #     await interaction.response.send_message("❌ 不能跟自己對戰。", ephemeral=True)
        #     return

        me_name = user_db.get_user_character_slot(str(interaction.user.id), 1)
        opp_name = user_db.get_user_character_slot(str(target.id), 1)
        if not me_name:
            await interaction.response.send_message(
                "❌ 你尚未綁定本尊角色，請先用 `/setting設定 type:角色 type2:1本` 設定。", ephemeral=True)
            return
        if not opp_name:
            await interaction.response.send_message(
                f"❌ {target.mention} 尚未綁定本尊角色（1本），無法決鬥。", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            me = await asyncio.to_thread(_build_fighter, me_name)
            opp = await asyncio.to_thread(_build_fighter, opp_name)
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

        # 開戰（發起者 me 先攻）
        _fight(me)
        _fight(opp)

        if me['total'] > opp['total']:
            winner, loser = me, opp
        elif opp['total'] > me['total']:
            winner, loser = opp, me
        else:
            winner, loser = None, None

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
        embed.add_field(
            name="🏆 結果",
            value=(f"**{winner['name']}** 獲勝！" if winner else "🤝 平手！"),
            inline=False,
        )
        embed.set_footer(text=f"{'-' * 19}TMS對戰系統 v1.0.0{'-' * 19}")

        # 合成決鬥圖：勝者固定在右(勝利姿勢)、敗者在左(陣亡姿勢+鏡像面向勝者)
        if winner is not None:
            left_f, left_pose, right_f, right_pose = loser, LOSE_POSE, winner, WIN_POSE
            left_mirror = True
        else:
            left_f, left_pose, right_f, right_pose = me, DRAW_POSE, opp, DRAW_POSE
            left_mirror = False

        duel_file = None
        try:
            buf = await _compose_duel_image(
                left_f, left_pose, right_f, right_pose,
                left_mirror=left_mirror,
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
