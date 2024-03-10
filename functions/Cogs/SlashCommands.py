import discord
from discord import app_commands
from discord.ext import commands
import math
from typing import Optional
from discord.app_commands import Choice
import configparser
import datetime

from functions.getprize import use_apple, use_fashionbox, use_apple_FrenzyTotem
from functions.CreatePrizeEmbed import Create_FashionBox_embed, Create_Apple_embed
from functions.CreateBossDataEmbed import Create_Boss_Data_Embed, get_difficulty_value
from functions.RequestUnionRank import Create_UnionRank_embed
from functions.CreateSolErdaFragmentEmbed import CreateSolErdaFragment

SlashCount = 0

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def SlashCountAdd():
    global SlashCount
    SlashCount += 1

def PrintSlash(type, interaction: discord.Interaction):
    SlashCountAdd()
    print(f'{get_now_HMS()}, #{SlashCount}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type}')
    print('-'*40)


class SlashCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
    now_HMS = datetime.datetime.now().strftime('%H:%M:%S')    

    #-----------------ping-----------------
    @app_commands.command(name="ping", description="ping")
    async def ping(self, interaction: discord.Interaction):
        bot_latency = round(self.client.latency * 1000)
        PrintSlash('ping', interaction)
        await interaction.response.send_message(f"pong, latency is {bot_latency} ms.")

    #-----------------help-----------------
    @app_commands.command(name="help", description="help")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"**TMS新楓之谷BOT**", 
            description = f'Ver2.1.2\n\n[__TMS Discord & Support Guild__](https://discord.gg/maplestory-tw)\n\n[__邀請TMSBug__](https://reurl.cc/aLj8V9)\n\n[__功能/指令列表__](https://reurl.cc/kr25Wq)\n\n有問題請聯繫(.yuyu0)處理', 
            color=0x6f00d2,
            )
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/957283103364235284.webp?size=96&quality=lossless')
        PrintSlash('help', interaction)
        await interaction.response.send_message(embed=embed)

    #-----------------抽獎-----------------
    @app_commands.describe(type = "類別")
    @app_commands.choices(
        type = [
            Choice(name = "蘋果", value = "GoldApple"),
            Choice(name = "時尚", value = "FashionBox"),
            Choice(name = "輪迴", value = "FrenzyTotem"),
            Choice(name = "伴侶", value = "boyngirl"),
            ]
    )
    @app_commands.command(name="抽", description="抽獎")
    async def getprize(self, interaction: discord.Interaction, type: str):
        if type == "GoldApple":
            Message = use_apple(interaction.user.mention)
        elif type == "FashionBox":
            Message = use_fashionbox(interaction.user.mention)
        elif type == "FrenzyTotem":
            Message = use_apple_FrenzyTotem(interaction.user.mention)
        elif type == "boyngirl":
            Message = "抽不到"

        
        PrintSlash('getprize', interaction)
        await interaction.response.send_message(content=f"{Message}")

    #-----------------當期抽獎機率-----------------
    @app_commands.command(name="當期抽獎機率", description="當期抽獎機率")
    @app_commands.describe(type = "類別")
    @app_commands.choices(
        type = [
            Choice(name = "蘋果", value = "GoldApple"),
            Choice(name = "時尚", value = "FashionBox"),
            ]
    )
    async def getprizechance(self, interaction: discord.Interaction, type: str):
        if type == "GoldApple":
            embed = Create_Apple_embed()
        elif type == "FashionBox":
            embed = Create_FashionBox_embed()
            
        PrintSlash('getprizechance', interaction)
        await interaction.response.send_message(embed=embed)

    #-----------------BOSS-----------------

    @app_commands.command(name="easyboss", description="BOSS資料")
    @app_commands.describe(bossname = "哪一隻", difficulty = "難度")
    @app_commands.choices(
        bossname = [
            Choice(name = "巴洛古", value = "巴洛古"),
            Choice(name = "殘暴炎魔", value = "殘暴炎魔"),
            Choice(name = "梅格耐斯", value = "梅格耐斯"),
            Choice(name = "希拉", value = "希拉"),
            Choice(name = "卡翁", value = "卡翁"),
            Choice(name = "拉圖斯", value = "拉圖斯"),
            Choice(name = "森蘭丸", value = "森蘭丸"),
            Choice(name = "比艾樂", value = "比艾樂"),
            Choice(name = "斑斑", value = "斑斑"),
            Choice(name = "血腥皇后", value = "血腥皇后"),
            Choice(name = "貝倫", value = "貝倫"),
            Choice(name = "凡雷恩", value = "凡雷恩"),
            Choice(name = "闇黑龍王", value = "闇黑龍王"),
            Choice(name = "阿卡依農", value = "阿卡依農"),
            Choice(name = "皮卡啾", value = "皮卡啾"),
            Choice(name = "西格諾斯", value = "西格諾斯"),
            Choice(name = "培羅德", value = "培羅德"),
            Choice(name = "濃姬", value = "濃姬"),
        ],
        difficulty = [
            Choice(name = "簡單", value = "easy"),
            Choice(name = "普通", value = "normal"),
            Choice(name = "困難/混沌", value = "hard"),
            Choice(name = "極限", value = "extreme"),
        ] 
    )
    async def easybossinfo(self, interaction: discord.Interaction, bossname: str, difficulty: str):
        
        index, indexerror = get_difficulty_value(bossname, difficulty)
        if indexerror == "True":
            await interaction.response.send_message(content=f"{interaction.user.mention} {bossname} 沒有這個難度")
            return

        embed, num_subtitles = Create_Boss_Data_Embed(bossname, index)
        PrintSlash('easybossinfo', interaction)
        await interaction.response.send_message(embed=embed)
        
    @app_commands.command(name="boss", description="BOSS資料")
    @app_commands.describe(bossname = "哪一隻", difficulty = "難度")
    @app_commands.choices(
        bossname = [
            Choice(name = "史烏", value = "史烏"),
            Choice(name = "戴米安", value = "戴米安"),
            Choice(name = "守護天使綠水靈", value = "守護天使綠水靈"),
            Choice(name = "露希妲", value = "露希妲"),
            Choice(name = "威爾", value = "威爾"),
            Choice(name = "戴斯克", value = "戴斯克"),
            Choice(name = "真希拉", value = "真希拉"),
            Choice(name = "頓凱爾", value = "頓凱爾"),
            Choice(name = "黑魔法師", value = "黑魔法師"),
            Choice(name = "受選的賽蓮", value = "受選的賽蓮"),
            Choice(name = "監視者卡洛斯", value = "監視者卡洛斯"),
            Choice(name = "咖凌", value = "咖凌")
        ],
        difficulty = [
            Choice(name = "簡單", value = "easy"),
            Choice(name = "普通", value = "normal"),
            Choice(name = "困難/混沌", value = "hard"),
            Choice(name = "極限", value = "extreme"),
        ] 
    )
    async def bossinfo(self, interaction: discord.Interaction, bossname: str, difficulty: str):
        
        index, indexerror = get_difficulty_value(bossname, difficulty)
        if indexerror == "True":
            await interaction.response.send_message(content=f"{interaction.user.mention} {bossname} 沒有這個難度")
            return

        embed, num_subtitles = Create_Boss_Data_Embed(bossname, index)
        PrintSlash('bossinfo', interaction)
        await interaction.response.send_message(embed=embed)

    #-----------------戰地-----------------
    @app_commands.command(name="戰地查詢", description="查戰地排行")
    async def unionsearch(self, interaction: discord.Interaction, playername: str):
        embed = Create_UnionRank_embed(playername)
        
        PrintSlash('unionsearch', interaction)
        await interaction.response.send_message(embed=embed)

    #-----------------碎碎-----------------
    @app_commands.command(name="碎片進度", description="碎碎進度")
    @app_commands.describe(skillnodes1 = "起源", masterynodes1 = "精通1", boostnode1 = "強化1", boostnode2 = "強化2", boostnode3 = "強化3", boostnode4 = "強化4")
    async def calculatefragment(self, interaction: discord.Interaction, skillnodes1: int, masterynodes1: int, boostnode1: int, boostnode2: int, boostnode3: int, boostnode4: int):
        embed = CreateSolErdaFragment(skillnodes1, masterynodes1, boostnode1, boostnode2, boostnode3, boostnode4, interaction.user.mention)
        
        PrintSlash('calculatefragment', interaction)
        await interaction.response.send_message(embed=embed)


    