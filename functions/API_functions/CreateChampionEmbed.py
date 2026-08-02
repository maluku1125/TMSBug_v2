import discord

from functions.API_functions.API_Request_Character import (
    get_character_ocid, request_character_basic, request_character_hexamatrix, request_character_stat
)
from functions.API_functions.API_Request_union import request_user_union_champion
from functions.Cogs.Slash_CreateSolErdaFragmentEmbed import (
    extract_hexa_levels, build_core_pairs, CalculateHexaMaterials, common_cores_open
)


def _champion_hexa_progress(ocid):
    """回傳 (已花碎片, 全滿碎片)；無六轉資料回 None。"""
    hexa = request_character_hexamatrix(ocid) or {}
    equipment = hexa.get('character_hexa_core_equipment')
    if not equipment:
        return None
    c2_open, c3_open = common_cores_open()
    levels = extract_hexa_levels(equipment)
    core_pairs, *_ = build_core_pairs(levels, c2_open, c3_open)
    _, _, spent_frag, max_frag = CalculateHexaMaterials(core_pairs)
    return spent_frag, max_frag


def create_champion_embed(character_name):
    """建立聯盟冠軍 embed。回傳 {'success': bool, 'embed': discord.Embed}。"""
    ocid = get_character_ocid(character_name)
    if not ocid:
        return {"success": False, "embed": discord.Embed(
            title="查無角色", description=f"找不到角色「{character_name}」", color=0xff0000)}

    data = request_user_union_champion(ocid)
    champions = (data or {}).get('union_champion') or []

    # 0 位冠軍
    if not champions:
        return {"success": True, "embed": discord.Embed(
            title=f"👑 {character_name} 的聯盟冠軍",
            description="該角色上未綁定冠軍",
            color=0x00bfff)}

    embed = discord.Embed(title=f"👑 {character_name} 的聯盟冠軍", color=0xffd700)

    for champ in sorted(champions, key=lambda c: c.get('champion_slot', 0)):
        name = champ.get('champion_name', '?')
        slot = champ.get('champion_slot', '?')
        grade = champ.get('champion_grade', '')
        champ_class = champ.get('champion_class', '')

        champ_ocid = get_character_ocid(name)

        # 等級(經驗%)
        basic = request_character_basic(champ_ocid) if champ_ocid else None
        if basic:
            try:
                exp_str = f"{float(basic.get('character_exp_rate', 0)):.2f}"
            except (TypeError, ValueError):
                exp_str = str(basic.get('character_exp_rate', '?'))
            level_str = f"Lv.{basic.get('character_level', '?')} ({exp_str}%)"
        else:
            level_str = "—"

        # solerda 進度（碎片）
        hexa = _champion_hexa_progress(champ_ocid) if champ_ocid else None
        if hexa:
            spent_frag, max_frag = hexa
            pct = (spent_frag / max_frag * 100) if max_frag else 0
            hexa_str = f"{spent_frag:,}/{max_frag:,} ({pct:.2f}%)"
        else:
            hexa_str = "無六轉資料"

        # 戰鬥力
        stat = request_character_stat(champ_ocid) if champ_ocid else None
        cp_str = "—"
        if stat:
            for item in (stat.get('final_stat') or []):
                if item.get('stat_name') == '戰鬥力':
                    try:
                        cp_str = f"{int(item.get('stat_value', 0)):,}"
                    except (TypeError, ValueError):
                        cp_str = str(item.get('stat_value', '—'))
                    break

        embed.add_field(
            name=f"#{slot}　{name}　[{grade}]",
            value=(
                "```autohotkey\n"
                f"職業　：{champ_class}\n"
                f"等級　：{level_str}\n"
                f"六轉　：{hexa_str}\n"
                f"戰鬥力：{cp_str}\n"
                "```"
            ),
            inline=False,
        )

    embed.set_footer(text=f"共 {len(champions)} 位冠軍")
    return {"success": True, "embed": embed}
