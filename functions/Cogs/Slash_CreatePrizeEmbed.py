import discord
from discord import app_commands
from discord.ext import commands
import datetime
from discord.app_commands import Choice

from functions.GetPrize import use_apple, use_fashionbox, use_apple_FrenzyTotem, Create_FashionBox_embed, Create_Apple_embed
from functions.SlashCommandManager import UseSlashCommand

class Slash_CreatePrizeEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------抽獎-----------------
    @app_commands.describe(type = "類別")
    @app_commands.choices(
        type = [
            Choice(name = "蘋果", value = "GoldApple"),
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

        
        UseSlashCommand('getprize', interaction)
        await interaction.response.send_message(content=f"{Message}")

    #-----------------當期抽獎機率-----------------
    @app_commands.command(name="prizedata當期抽獎機率", description="當期抽獎機率")
    @app_commands.describe(type = "類別")
    @app_commands.choices(
        type = [
            Choice(name = "蘋果", value = "GoldApple")
            ]
    )
    async def getprizechance(self, interaction: discord.Interaction, type: str):
        if type == "GoldApple":
            embed = Create_Apple_embed()
        elif type == "FashionBox":
            embed = Create_FashionBox_embed()
            
        UseSlashCommand('getprizechance', interaction)
        await interaction.response.send_message(embed=embed)