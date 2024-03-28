import discord
from discord import app_commands
from discord.ext import commands
import datetime
import psutil
import time

from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed


process = psutil.Process()

# 獲取 CPU 使用率
cpu_usage = f"{(process.cpu_percent() / psutil.cpu_count()):.2f}"

# 獲取當前進程的記憶體使用量（MB）
memory_usage_mb = process.memory_info().rss / 1024 / 1024
# 獲取系統的總記憶體量（MB）
total_memory_mb = psutil.virtual_memory().total / 1024 / 1024
# 計算記憶體使用率
memory_usage_percent = memory_usage_mb / total_memory_mb * 100

# 作者
owner_id = '310164490391912448'

# 版本  
version = 'v2.4.2'

# 在程式開始運行時記錄當前的時間
start_time = time.time()


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
            description = f'', 
            color=0x32EBA7,
            )
        
        owner = await self.client.fetch_user(owner_id)

        embed.add_field(
            name="**作者**",
            value=f"諭諭({owner.name})",
        )        
        embed.add_field(
            name="版本",
            value=f"{version}",
        )    
        embed.add_field(
            name="BOT",
            value=(
                ""
                f"[__TMS Discord & Support Guild__](https://discord.gg/maplestory-tw)\n"
                f"[__邀請TMSBug__](https://reurl.cc/aLj8V9)\n"
                f"[__功能/指令列表__](https://reurl.cc/kr25Wq)\n"
                ""
            ),
            inline=False,
        )
        embed.add_field(
            name="BOT資料",
            value=(
                "```autohotkey\n"
                f"指令數量: {len(self.client.tree.get_commands())}\n"
                f"群組數量: {len(self.client.guilds):,}\n"
                f"成員人數: {sum([_.member_count or 0 for _ in self.client.guilds if not _.unavailable]):,}\n" 
                "```"
            ),
            inline=False,
        )
        # 在需要的時候計算運行時間
        runtime_seconds = time.time() - start_time
        runtime_minutes, runtime_seconds = divmod(runtime_seconds, 60)
        runtime_hours, runtime_minutes = divmod(runtime_minutes, 60)
        runtime_days, runtime_hours = divmod(runtime_hours, 24)
        if runtime_days > 0:
            runtime_str = f"{int(runtime_days)}天{int(runtime_hours)}時{int(runtime_minutes)}分{int(runtime_seconds)}秒"
        else:
            runtime_str = f"{int(runtime_hours)}小時{int(runtime_minutes)}分{int(runtime_seconds)}秒"


        embed.add_field(
            name="運行狀態",
            value=(
                "```autohotkey\n"
                f"CPU使用率: {cpu_usage}%\n"
                f"MEM使用率: {memory_usage_percent:.2f}%\n"
                f"MEM使用量: {memory_usage_mb:.2f} MB\n"
                f"BOT運行時間: {runtime_str} \n"
                "```"
            ),
            inline=False,
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

