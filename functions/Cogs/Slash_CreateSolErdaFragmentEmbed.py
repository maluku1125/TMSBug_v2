import discord
from discord import app_commands
from discord.ext import commands
import datetime

from functions.CreateSolErdaFragmentEmbed import CreateSolErdaFragment

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def PrintSlash(type, interaction: discord.Interaction):
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type}')
    print('-'*40)

class Slash_CreateSolErdaFragmentEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------碎碎-----------------
    @app_commands.command(name="solerda碎片進度", description="碎碎進度")
    @app_commands.describe(skillnodes1 = "起源", masterynodes1 = "精通1", boostnode1 = "強化1", boostnode2 = "強化2", boostnode3 = "強化3", boostnode4 = "強化4")
    async def calculatefragment(self, interaction: discord.Interaction, skillnodes1: int, masterynodes1: int, boostnode1: int, boostnode2: int, boostnode3: int, boostnode4: int):
        embed = CreateSolErdaFragment(skillnodes1, masterynodes1, boostnode1, boostnode2, boostnode3, boostnode4, interaction.user.mention)
        
        PrintSlash('calculatefragment', interaction)
        await interaction.response.send_message(embed=embed)