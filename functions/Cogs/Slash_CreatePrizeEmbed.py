import discord
from discord import app_commands
from discord.ext import commands
import datetime
from discord.app_commands import Choice

from functions.GetPrize import use_apple, use_fashionbox, use_apple_FrenzyTotem, Create_FashionBox_embed, Create_Apple_embed

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def PrintSlash(type, interaction: discord.Interaction):
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type}')
    print('-'*40)

class Slash_CreatePrizeEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

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
    @app_commands.command(name="getprize抽", description="抽獎")
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
    @app_commands.command(name="prizedata當期抽獎機率", description="當期抽獎機率")
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