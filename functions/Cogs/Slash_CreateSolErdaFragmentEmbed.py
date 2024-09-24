import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
from functions.tinyfunctions import probably
from functions.SlashCommandManager import UseSlashCommand

# 偷走的數量
stolen_fragments = 0


with open(f'C:\\Users\\User\\Desktop\\DiscordBot\\TMSBug_v2\\Data\\HexaNodesCost.json', 'r', encoding='utf-8') as f:
    HexaNodesCost = json.load(f)

class Slash_CreateSolErdaFragmentEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------碎碎-----------------
    @app_commands.command(name="solerda碎片進度", description="碎碎進度")
    @app_commands.describe(
            skillnodes1 = "起源", 
            masterynodes1 = "精通1", masterynodes2 = "精通2", 
            boostnode1 = "強化1", boostnode2 = "強化2", boostnode3 = "強化3", boostnode4 = "強化4", 
            commonnode1 = "共用1",
            extrafragment = "預留碎片"
        )
    async def calculatefragment(
        self, interaction: discord.Interaction, 
        skillnodes1: int, 
        masterynodes1: int, masterynodes2: int, 
        boostnode1: int, boostnode2: int, boostnode3: int, boostnode4: int, 
        commonnode1: int,
        extrafragment: int=0
        ):
        embed = CreateSolErdaFragment(
            skillnodes1,
            masterynodes1, masterynodes2, 
            boostnode1, boostnode2, boostnode3, boostnode4, 
            commonnode1,
            extrafragment
        )

        UseSlashCommand('calculatefragment', interaction)
        await interaction.response.send_message(embed=embed)


def Calculatefragment(
        SkillNodes1, 
        MasteryNodes1, MasteryNodes2,
        BoostNode1, BoostNode2, BoostNode3, BoostNode4,
        CommonNode1,
        extrafragment
    ):
    
    maxtotal = 0
    totalcount = 0
    if SkillNodes1 >= 0 :
        maxtotal += 4400
        totalcount += sum(HexaNodesCost["SkillNodes"]["solerdafragment"][:SkillNodes1])
    if MasteryNodes1 >= 0 :
        totalcount += sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes1])
        maxtotal += 2252
    if MasteryNodes2 >= 0 :  
        totalcount += sum(HexaNodesCost["MasteryNodes"]["solerdafragment"][:MasteryNodes2])
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
   
    totalcount += extrafragment

    return totalcount, maxtotal


def CreateSolErdaFragment(
        SkillNodes1, 
        MasteryNodes1, MasteryNodes2,
        BoostNode1, BoostNode2, BoostNode3, BoostNode4,
        CommonNode1,
        extrafragment
    ):
    global stolen_fragments

    # 確保所有節點等級都在有效範圍內
    nodes = [SkillNodes1, MasteryNodes1, BoostNode1, BoostNode2, BoostNode3, BoostNode4]
    for node in nodes:
        if node < -30 or node > 30:
            error_embed = discord.Embed(title="等級輸入錯誤", description="必須填入-30~30之間的數", color=0xff0000)
            return error_embed

    # 愚人節機率
    now = datetime.datetime.now()  
    if now.month == 4 and now.day == 1:
        probability = 0.99
    else:
        probability = 0.01

    totalcount, maxfragment = Calculatefragment(
        SkillNodes1, 
        MasteryNodes1, MasteryNodes2,
        BoostNode1, BoostNode2, BoostNode3, BoostNode4,
        CommonNode1,
        extrafragment
    ) 

    percentage = totalcount / maxfragment * 100
    percentagemsg = f"{totalcount}/{maxfragment} ({percentage:.2f}%)"

    # 計算進度條的長度
    progress_length = 20
    progress = min(int(totalcount / maxfragment * progress_length),20)

    # 創建進度條
    progress_bar = '▓' * progress + '░' * (progress_length - progress)

    if probably(probability):    

        stolen_fragments += totalcount

        embed = discord.Embed(
        title=f"**靈魂艾爾達碎片進度**", 
        color=0x6f00d2,
        )        
        embed.add_field(name=f"你原本的進度是{percentage:.2f}%", value=f"但***邪惡***的蟲蟲把他們都偷走了", inline = False)

        embed.add_field(
        name=f"當前進度：{percentagemsg}", 
        value=f"{progress_bar}", 
        inline = False
    )
        
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
                f"精通核心1 : 0\n"
                f"精通核心2 : 0\n```"
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
                f"共用核心1 : 0"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"蟲蟲已經累計偷走了{stolen_fragments:,}個碎片", value=f"請保護好你的碎片", inline = False
        )
        embed.set_footer(text=f'預留碎片 : {extrafragment}')
        
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
        return embed

    embed = discord.Embed(
        title=f"**靈魂艾爾達碎片進度**", 
        color=0x6f00d2,
        )
    embed.add_field(
        name=f"當前進度：{percentagemsg}", 
        value=(
            f"{progress_bar}\n"
            f"預留碎片 : {extrafragment}"
        ),
        
        inline = False
    )

    embed.add_field(
        name="技能核心",
        value=(
            "```autohotkey\n"
            f"技能核心1 : {max(0, SkillNodes1)}{'🚫' if SkillNodes1 < 0 else ''}\n```"
        ),
        inline=False,
    )
    embed.add_field(
        name="精通核心",
        value=(
            "```autohotkey\n"
            f"精通核心1 : {abs(MasteryNodes1)}{'🚫' if MasteryNodes1 < 0 else ''}\n"
            f"精通核心2 : {abs(MasteryNodes2)}{'🚫' if MasteryNodes2 < 0 else ''}\n```"
        ),
        inline=False,
    )
    embed.add_field(
        name="強化核心",
        value=(
            "```autohotkey\n"
            f"強化核心1 : {abs(BoostNode1)}{'🚫' if BoostNode1 < 0 else ''}\n"
            f"強化核心2 : {abs(BoostNode2)}{'🚫' if BoostNode2 < 0 else ''}\n"
            f"強化核心3 : {abs(BoostNode3)}{'🚫' if BoostNode3 < 0 else ''}\n"
            f"強化核心4 : {abs(BoostNode4)}{'🚫' if BoostNode4 < 0 else ''}\n```"
        ),
        inline=False,
    )
    embed.add_field(
        name="共用核心",
        value=(
            "```autohotkey\n"
            f"共用核心1 : {abs(CommonNode1)}{'🚫' if CommonNode1 < 0 else ''}"
            "```"
        ),
        inline=False,
    )
    embed.set_footer(text=f'輸入-1~-30即忽略該技能進度')


    embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/1196836355225952336.webp?size=96&quality=lossless')
    
    return embed
