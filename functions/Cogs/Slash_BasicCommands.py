import discord
from discord import app_commands
from discord.ext import commands
import datetime

from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def PrintSlash(type, interaction: discord.Interaction):
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type}')
    print('-'*40)


class Slash_BasicCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------ping-----------------
    @app_commands.command(name="ping", description="ping")
    async def ping(self, interaction: discord.Interaction):
        bot_latency = round(self.client.latency * 1000)
        PrintSlash('ping', interaction)
        await interaction.response.send_message(f"pong, latency is {bot_latency} ms.")

    #-----------------help-----------------
    @app_commands.command(name="help",description="help")
    @app_commands.describe(dev_func = "起源")

    async def help(self, interaction: discord.Interaction, dev_func: str = None):

        # 如果 dev_func 為 'load'，並且命令的發送者是作者
        if dev_func == 'load_Slash_CreatePrizeEmbed' and str(interaction.user.id) == '310164490391912448':
            try:
                await self.client.add_cog('Slash_CreatePrizeEmbed')
            except Exception as e:
                print(f'Failed to load extension: {e}')
            print('Load Slash_CreatePrizeEmbed')

        # 如果 dev_func 為 'unload'，並且命令的發送者是作者
        elif dev_func == 'unload_Slash_CreatePrizeEmbed' and str(interaction.user.id) == '310164490391912448':
            try:
                await self.client.remove_cog('Slash_CreatePrizeEmbed')
            except Exception as e:
                print(f'Failed to unload extension: {e}')
            print('Unload Slash_CreatePrizeEmbed')

        embed = discord.Embed(
            title=f"**TMS新楓之谷BOT**", 
            description = f'Ver2.4.0\n\n[__TMS Discord & Support Guild__](https://discord.gg/maplestory-tw)\n\n[__邀請TMSBug__](https://reurl.cc/aLj8V9)\n\n[__功能/指令列表__](https://reurl.cc/kr25Wq)\n\n有問題請聯繫(.yuyu0)處理', 
            color=0x6f00d2,
            )
        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/957283103364235284.webp?size=96&quality=lossless')
        PrintSlash('help', interaction)
        await interaction.response.send_message(embed=embed)

    #-----------------MEMO-----------------
    @app_commands.command(name="練等備忘", description="練等備忘")
    async def farmingmemo(self, interaction: discord.Interaction):
        embed = CreateFarmingEmbed()
        PrintSlash('farmingmemo', interaction)
        await interaction.response.send_message(embed=embed)

  
    @app_commands.command(name="打王備忘", description="打王備忘")
    async def combatmemo(self, interaction: discord.Interaction):
        embed = CreateCombatEmbed()
        PrintSlash('combatmemo', interaction)
        await interaction.response.send_message(embed=embed)

