import json
import discord
from functions.tinyfunctions import probably
import datetime

maxfragment = 20184
# 偷走的數量
stolen_fragments = 0


with open(f'C:\\Users\\User\\Desktop\\DiscordBot\\TMSBug_v2\\Data\\HexaNodesCost.json', 'r', encoding='utf-8') as f:
    HexaNodesCost = json.load(f)

def Calculatefragment(SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4):

    SkillNodes1count = sum(HexaNodesCost["SkillNodes"]["solerdafragment"][:SkillNodes1])
    MasteryNodes1count = sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes1])
    BoostNode1count = sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode1])
    BoostNode2count = sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode2])
    BoostNode3count = sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode3])
    BoostNode4count = sum(HexaNodesCost["BoostNodes"]["solerdafragment"][:BoostNode4])

    totalcount = SkillNodes1count + MasteryNodes1count + BoostNode1count + BoostNode2count + BoostNode3count + BoostNode4count

    return totalcount


def CreateSolErdaFragment(SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4, user):
    global stolen_fragments

    # 確保所有節點等級都在有效範圍內
    nodes = [SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4]
    for node in nodes:
        if node < 0 or node > 30:
            error_embed = discord.Embed(title="等級輸入錯誤", description="必須在0~30等之間", color=0xff0000)
            return error_embed

    # 獲取當前的日期
    now = datetime.datetime.now()  
    if now.month == 4 and now.day == 1:
        probability = 0.99
    else:
        probability = 0.01

    if probably(probability):
        totalcount = Calculatefragment(SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4)        
        percentage = totalcount / maxfragment * 100

        stolen_fragments += totalcount

        embed = discord.Embed(
        title=f"**靈魂艾爾達碎片進度**", 
        color=0x6f00d2,
        )        
        embed.add_field(name=f"你原本的進度是{percentage:.2f}%", value=f"但***邪惡***的蟲蟲把他們都偷走了", inline = False)
        
        embed.add_field(
            name="技能核心",
            value=(
                "```autohotkey\n"
                f"技能核心1 : 0\n```"
            ),
            inline=False,
        )
        embed.add_field(
            name="精通核心",
            value=(
                "```autohotkey\n"
                f"精通核心1 : 0\n```"
            ),
            inline=False,
        )
        embed.add_field(
            name="強化核心",
            value=(
                "```autohotkey\n"
                f"強化核心1 : 0\n"
                f"強化核心2 : 0\n"
                f"強化核心3 : 0\n"
                f"強化核心4 : 0\n```"
            ),
            inline=False,
        )
        embed.add_field(
            name="共用核心",
            value=(
                "```autohotkey\n"
                f"共用核心1 :"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"蟲蟲已經累計偷走了{stolen_fragments:,}個碎片", value=f"請保護好你的碎片", inline = False
        )
        
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
        return embed

        
    totalcount = Calculatefragment(SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4)
    percentage = totalcount / maxfragment * 100
    percentagemsg = f"{totalcount}/{maxfragment} ({percentage:.2f}%)"

    # 計算進度條的長度
    progress_length = 20
    progress = int(totalcount / maxfragment * progress_length)

    # 創建進度條
    progress_bar = '▓' * progress + '░' * (progress_length - progress)

    embed = discord.Embed(
        title=f"**靈魂艾爾達碎片進度**", 
        color=0x6f00d2,
        )
    embed.add_field(
        name=f"當前進度：{percentagemsg}", 
        value=f"{progress_bar}", 
        inline = False
    )

    embed.add_field(
        name="技能核心",
        value=(
            "```autohotkey\n"
            f"技能核心1 : {SkillNodes1}\n```"
        ),
        inline=False,
    )
    embed.add_field(
        name="精通核心",
        value=(
            "```autohotkey\n"
            f"精通核心1 : {MasteryNodes1}\n```"
        ),
        inline=False,
    )
    embed.add_field(
        name="強化核心",
        value=(
            "```autohotkey\n"
            f"強化核心1 : {BoostNode1}\n"
            f"強化核心2 : {BoostNode2}\n"
            f"強化核心3 : {BoostNode3}\n"
            f"強化核心4 : {BoostNode4}\n```"
        ),
        inline=False,
    )
    embed.add_field(
        name="共用核心",
        value=(
            "```autohotkey\n"
            f"共用核心1 : "
            "```"
        ),
        inline=False,
    )


    embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
    
    return embed
