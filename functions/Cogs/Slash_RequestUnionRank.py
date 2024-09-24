import discord
from discord import app_commands
from discord.ext import commands
import datetime

from functions.RequestUnionRank import Create_UnionRank_embed
from functions.SlashCommandManager import UseSlashCommand

class Slash_RequestUnionRank(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------戰地-----------------
    @app_commands.command(name="union戰地查詢", description="查戰地排行")
    async def unionsearch(self, interaction: discord.Interaction, playername: str):
        await interaction.response.defer()
        embed = Create_UnionRank_embed(playername)
        
        UseSlashCommand('unionsearch', interaction)                
        await interaction.edit_original_response(embed=embed)

