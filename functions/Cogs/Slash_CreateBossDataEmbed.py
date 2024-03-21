import discord
from discord import app_commands
from discord.ext import commands
import datetime
from discord.app_commands import Choice

from functions.CreateBossDataEmbed import Create_Boss_Data_Embed, get_difficulty_value

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def PrintSlash(type, interaction: discord.Interaction):
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type}')
    print('-'*40)

class Slash_CreateBossDataEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

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
    