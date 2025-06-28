
import json
import discord

boss_aliases = {
    '巴洛古': '巴洛古',
    '殘暴炎魔': '殘暴炎魔',
    '炎魔': '殘暴炎魔',
    '梅格耐斯': '梅格耐斯',
    '西拉': '希拉',
    '希拉': '希拉',
    '卡翁': '卡翁',
    '拉圖斯': '拉圖斯',
    '森蘭丸': '森蘭丸',
    '比艾樂': '比艾樂',
    '斑斑': '斑斑',
    '血腥皇后': '血腥皇后',
    '皇后': '血腥皇后',
    '貝倫': '貝倫',
    '凡雷恩': '凡雷恩',
    '暗黑龍王': '闇黑龍王',
    '闇黑龍王': '闇黑龍王',
    '阿卡伊農': '阿卡伊農',
    '皮卡啾': '皮卡啾',
    '西格諾斯': '西格諾斯',
    '培羅德': '培羅德',
    '濃姬': '濃姬',
    '史烏': '史烏',
    '使烏': '史烏',
    '戴米安': '戴米安',
    '守護天使綠水靈': '守護天使綠水靈',
    '露希妲': '露希妲',
    '露希達': '露希妲',
    '露西妲': '露希妲',
    '威爾': '威爾',
    '戴斯克': '戴斯克',
    '真希拉': '真希拉',
    '頓凱爾': '頓凱爾',
    '盾凱爾': '頓凱爾',
    '黑魔法師':'黑魔法師',
    '受選的賽蓮':'受選的賽蓮',
    '賽蓮':'受選的賽蓮',
    '監視者卡洛斯':'監視者卡洛斯',
    '卡洛斯':'監視者卡洛斯',
    '咖凌':'咖凌',
    '林波':'林波',
    '巴德利斯':'巴德利斯',
    '蟲蟲':'蟲蟲'
}
with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\BossData.json', 'r', encoding='utf-8') as f:
    boss_data = json.load(f)

def Create_Boss_Data_Embed(Content, Bossmode):

    boss_name = boss_aliases.get(Content, None)

    subtitles = list(boss_data[boss_name].keys())
    boss_mode = subtitles[Bossmode]

    boss_info = boss_data.get(boss_name, {}).get(boss_mode, {})
    entry_level = boss_info.get("EntryLevel", 0)
    timelimit = boss_info.get("Timelimit", 0)
    potion_cooldown = boss_info.get("PotionCoolDown", 0)
    death_count = boss_info.get("DeathCount", 0)
    death_print = f"{death_count} (💥機制殺)" if boss_info.get("SpecialKill", 0) else f"{death_count}"
    complete_count = boss_info.get("CompleteCount", "")
    defense = boss_info.get("Defense", "")
    use_arc_aut = boss_info.get("UseArcorAUT", "")
    stages = [
        '\n'.join([f"{k}: {v}"for k, v in boss_info.get("1stStage", {}).items()]),
        '\n'.join([f"{k}: {v}"for k, v in boss_info.get("2ndStage", {}).items()]),
        '\n'.join([f"{k}: {v}"for k, v in boss_info.get("3rdStage", {}).items()]),
        '\n'.join([f"{k}: {v}"for k, v in boss_info.get("4thStage", {}).items()]),
        '\n'.join([f"{k}: {v}"for k, v in boss_info.get("5thStage", {}).items()]),
    ]
    main_drop = boss_info.get("MainDrop", "")
    sub_drop = boss_info.get("SubDrop", [])
    cube_drop = boss_info.get("CubeDrop", "")
    glowing_soul_crystal = boss_info.get("GlowingSoulCrystal", 0)

    if use_arc_aut == "Arcane":
        arcane_authentic = f"\n🌌祕法力量：{boss_info.get('Arcane', '')}"
    elif use_arc_aut == "Authentic":
        arcane_authentic = f"\n🌌真實力量：{boss_info.get('Authentic', '')}"
    else:
        arcane_authentic = ""

    sub_drop_items = [' '.join(sub_drop[i:i+3]) for i in range(0, len(sub_drop), 3)]
    sub_drop_description = '\n'.join(sub_drop_items)

    sub_drop_description += f'\n{cube_drop}'

    main_drop_description = '\n'.join(main_drop)

    embed = discord.Embed(
        title=f"**{boss_name}({boss_mode}**)", 
        description = f'🚩入場等級：{entry_level}\n⌛時間限制：{timelimit}mins\n🧪藥水冷卻：{potion_cooldown}sec\n💀死亡次數：{death_print}\n📆完成次數：{complete_count}{arcane_authentic}\n🛡怪物防禦：{defense}\n{"-"*40}', 
        color=0xfbe200,
        )
    embed.set_footer(text='資料引用自hsiliya/zxcvll1379')
    embed.add_field(name="", value="> 🩸__**BOSS血量**__", inline = False)
    stage_count = ["第一階段", "第二階段", "第三階段", "第四階段", "第五階段"]
    for _ in range(len([_ for _ in stages if _])):
        embed.add_field(name=stage_count[_], value=stages[_], inline=True)
    embed.add_field(name="", value="> 💎__**獎勵**__", inline = False)
    embed.add_field(name="🎁__主要掉落物__", value=f"{main_drop_description}", inline = True)
    embed.add_field(name="🎁__其他掉落物__", value=f"{sub_drop_description}", inline = True)
    embed.add_field(name="💰結晶石", value=f"{glowing_soul_crystal:,}", inline = True)

    return embed

def get_difficulty_value(bossname: str, difficulty: str) -> int:
    difficulties = list(boss_data[bossname].keys())
    translated = translate_difficulty(difficulty)
    for index, value in enumerate(difficulties):
        if isinstance(translated, list):
            if value in translated:
                return index, "False"
    return None, "True"


def translate_difficulty(difficulty: str) -> str:
    translations = {
        "easy": ["簡單", "初級模式"],
        "normal": ["普通", "中級模式"],
        "hard": ["困難", "混沌", "高級模式"],
        "extreme": ["極限", "終極", "頂級模式"],
    }
    translated = translations.get(difficulty)
    return translated