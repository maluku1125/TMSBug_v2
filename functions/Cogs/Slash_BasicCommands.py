import discord
from discord import app_commands
from discord.ext import commands
import datetime
import psutil
import time

from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed
from functions.MSCrawler import Format_ApplePrizeData, Format_FashionBoxPrizeData, save_apple_json_file, save_fashionbox_json_file
from functions.GetPrize import reloaddata
from functions.SlashCommandManager import UseSlashCommand, GetSlashCommandUsage
 
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
version = 'v3.5.0'

# 在程式開始運行時記錄當前的時間
start_time = time.time()

class Slash_BasicCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------ping-----------------
    @app_commands.command(name="ping", description="ping")
    async def ping(self, interaction: discord.Interaction):
        bot_latency = round(self.client.latency * 1000)
        UseSlashCommand('ping', interaction)
        await interaction.response.send_message(f"pong, latency is {bot_latency} ms.")

    #-----------------help-----------------
    @app_commands.command(name="help",description="help")
    @app_commands.describe(dev_func = "dev_func")

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
        
        if dev_func == 'getprizetable' and str(interaction.user.id) == '310164490391912448':
            print('getprizetable')
            await interaction.response.defer()
            apple_formatted_data = Format_ApplePrizeData()
            fashionbox_formatted_data = Format_FashionBoxPrizeData()
            
            await interaction.edit_original_response(content=f'{apple_formatted_data}\n{fashionbox_formatted_data}')
        
        if dev_func == 'addprizetable' and str(interaction.user.id) == '310164490391912448':
            print('addprizetable')
            await interaction.response.defer()
            appleresult = save_apple_json_file()
            fashionmboxresult =save_fashionbox_json_file()
            await interaction.edit_original_response(content=f'已更新抽獎機率表\n黃金蘋果 : {appleresult}\n時尚隨機箱 : {fashionmboxresult}')

        if dev_func == 'reloadprize' and str(interaction.user.id) == '310164490391912448':
            print('reloadprize')
            reloaddata()
            await interaction.response.send_message(content=f'已重新加載抽獎機率表(黃金蘋果,時尚隨機箱)')
            
        if dev_func == "usage" and str(interaction.user.id) == '310164490391912448':
            print("slash_command_usage")
            embed = GetSlashCommandUsage()
            await interaction.response.send_message(embed=embed)
            

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
        UseSlashCommand('help', interaction)
        if interaction.guild_id != 420666881368784929 and self.client.user.id == 684625575729561609:
            await interaction.response.send_message("TMS_Bug未通過Discord驗證，可以轉至TMSBug_v2服務，請聯絡管理員邀請並於邀請後踢除TMS_Bug\n具體差異：\n```diff\n+通過discord認證\n+無法閱讀聊天室內容\n-無法使用<!>指令或讀取聊天室相關互動```\n[邀請TMSBug_v2](https://reurl.cc/aLj8V9)",embed=embed)
        else:
            await interaction.response.send_message(embed=embed)
    #-----------------MEMO-----------------
    @app_commands.command(name="練等備忘", description="練等備忘")
    async def farmingmemo(self, interaction: discord.Interaction):
        embed = CreateFarmingEmbed()
        UseSlashCommand('farmingmemo', interaction)
        await interaction.response.send_message(embed=embed)

  
    @app_commands.command(name="打王備忘", description="打王備忘")
    async def combatmemo(self, interaction: discord.Interaction):
        embed = CreateCombatEmbed()
        UseSlashCommand('Bossingmemo', interaction)
        await interaction.response.send_message(embed=embed)
        
