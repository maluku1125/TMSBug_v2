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

# 讓這支可以被 load_extension／reload_extension 熱抽換（2026-09-20）。
# setup_hook 改用 load_extension 之後，後台就能單獨重載這一個 cog，
# 不必為了改一行文案重啟整台 Bot（5 個 shard、近 5,000 個伺服器要重連）。
async def setup(client: commands.Bot):
    await client.add_cog(Slash_RequestUnionRank(client))
