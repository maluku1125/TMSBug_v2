import json
import discord
from functions.tinyfunctions import probably

maxfragment = 20184

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

    # 確保所有節點等級都在有效範圍內
    nodes = [SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4]
    for node in nodes:
        if node < 0 or node > 30:
            error_embed = discord.Embed(title="等級輸入錯誤", description="必須在0~30等之間", color=0xff0000)
            return error_embed
        
    if probably(0.01):
        totalcount = Calculatefragment(SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4)
        embed = discord.Embed(
        title=f"**靈魂艾爾達碎片進度**", 
        color=0x6f00d2,
        )
        percentage = totalcount / maxfragment * 100
        embed.add_field(name=f"你原本的進度是{percentage:.2f}%", value=f"但***邪惡***的蟲蟲把他們都偷走了", inline = False)
        embed.add_field(name="技能核心", value=f"技能核心１: 0 ", inline = True)
        embed.add_field(name="精通核心", value=f"精通核心１: 0 ", inline = True)
        embed.add_field(name="", value=f"", inline = False)
        embed.add_field(name="強化核心", value=f"強化核心１: 0\n強化核心２: 0\n強化核心３: 0\n強化核心４: 0", inline = True)
        embed.add_field(name="共用核心", value=f" ", inline = True)
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
        return embed

        
    totalcount = Calculatefragment(SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4)
    embed = discord.Embed(
        title=f"**靈魂艾爾達碎片進度**", 
        color=0x6f00d2,
        )
    percentage = totalcount / maxfragment * 100
    embed.add_field(name="當前進度", value=f"{totalcount}/{maxfragment} ({percentage:.2f}%)", inline = False)
    embed.add_field(name="", value=f"", inline = False)
    embed.add_field(name="技能核心", value=f"技能核心１: {SkillNodes1} ", inline = True)
    embed.add_field(name="精通核心", value=f"精通核心１: {MasteryNodes1} ", inline = True)
    embed.add_field(name="", value=f"", inline = False)
    embed.add_field(name="強化核心", value=f"強化核心１: {BoostNode1}\n強化核心２: {BoostNode2}\n強化核心３: {BoostNode3}\n強化核心４: {BoostNode4}", inline = True)
    embed.add_field(name="共用核心", value=f" ", inline = True)

    embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
    
    return embed
