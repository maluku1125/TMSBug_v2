import discord
from discord import app_commands
from discord.ext import commands
import datetime
import psutil
import time

from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed
from functions.MSCrawler import Format_ApplePrizeData, Format_FashionBoxPrizeData, save_apple_json_file, save_fashionbox_json_file
from functions.GetPrize import reloaddata
from ..SlashCommandManager import UseSlashCommand, GetSlashCommandUsage, SaveSystemStats, GetLastHourCommandCount, GetTopCommandsSimple, GetDailyTrend
 
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
version = 'v3.8.1'

# 在程式開始運行時記錄當前的時間
start_time = time.time()

class HelpCommandView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="指令說明", style=discord.ButtonStyle.primary, emoji="📋")
    async def command_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📋 指令說明",
            color=0x32EBA7,
        )
        embed.add_field(
            name="基本功能",
            value=(
                "```\n"
                "/help - 幫助\n"
                "/ping - BOT延遲\n"
                "/打王備忘 - 顯示打王備忘\n"
                "/練等備忘 - 顯示練等備忘\n"               
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="BOSS查詢",
            value=(
                "```\n"
                "/bossarc困王 - 查詢ARC區的BOSS資料\n"
                "/bossaut困王 - 查詢AUT區的BOSS資料\n"
                "/easyboss里程周王 - 查詢史戴以前的BOSS資料\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="活動與查詢",
            value=(
                "```\n"
                "/events當期活動 - 顯示當前進行中的活動\n"
                "/prize當期抽獎機率 - 查詢當期抽獎機率\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="計算與模擬",
            value=(
                "```\n"
                "/solerda碎片進度 - 計算六轉碎片進度\n"
                "/formulas各種公式 - 各種公式的簡易計算機\n"
                "/scrolls卷軸模擬器 - 卷軸模擬器\n"
                "/cubes洗方塊 - 洗方塊模擬器\n"
                "/starforce衛星 -衛星模擬\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="API功能",
            value=(
                "```\n"
                "/character角色查詢 - API 角色查詢\n"
                "/guild公會查詢 - API 公會查詢\n"
                "/exptracking經驗追蹤 - API 角色經驗追蹤\n"
                "/uniontracking戰地追蹤 - API 角色戰地追蹤\n"
                "/rank排行 - API 角色排行榜\n"
                "/apianalyse楓谷分析 - API 資料分析\n"
                "/union戰地查詢 - API 戰地查詢\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="設定",
            value=(
                "```\n"
                "/servercheck - 伺服器開機通知設定(僅群主)\n"
                "/setting設定 - 設定連結角色\n"
                "```"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
            
        # 開發者功能處理 - 合併的 usage/dashboard/stats 功能
        if dev_func and str(interaction.user.id) == '310164490391912448':
            if dev_func == "dashboard":
                print(f"slash_command_{dev_func}")
                dashboard_start_time = time.time()
                await interaction.response.defer()  # 因為可能需要較長時間處理
                
                try:
                    # 保存當前系統統計
                    guild_count = len(self.client.guilds)
                    user_count = sum([_.member_count or 0 for _ in self.client.guilds if not _.unavailable])
                    SaveSystemStats(guild_count, user_count)
                    
                    # 創建詳細儀表板
                    embed = GetSlashCommandUsage(30, self.client)
                    
                    response_time = time.time() - dashboard_start_time
                    UseSlashCommand(f'help_{dev_func}', interaction, response_time)
                    await interaction.edit_original_response(embed=embed)
                    return
                    
                except Exception as e:
                    error_embed = discord.Embed(
                        title="❌ 儀表板載入失敗",
                        description=f"錯誤: {str(e)}",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=error_embed)
                    UseSlashCommand(f'help_{dev_func}', interaction, time.time() - dashboard_start_time, False)
                    return

        # 預設 help 模式 - 顯示基本幫助資訊
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
                ""
            ),
            inline=False,
        )
        # 計算運行時間
        runtime_seconds = time.time() - start_time
        runtime_minutes, runtime_seconds = divmod(runtime_seconds, 60)
        runtime_hours, runtime_minutes = divmod(runtime_minutes, 60)
        runtime_days, runtime_hours = divmod(runtime_hours, 24)
        if runtime_days > 0:
            runtime_str = f"{int(runtime_days)}天{int(runtime_hours)}時{int(runtime_minutes)}分{int(runtime_seconds)}秒"
        else:
            runtime_str = f"{int(runtime_hours)}小時{int(runtime_minutes)}分{int(runtime_seconds)}秒"

        embed.add_field(
            name="BOT資料",
            value=(
                "```autohotkey\n"
                f"指令數量: {len(self.client.tree.get_commands())}\n"
                f"群組數量: {len(self.client.guilds):,}\n"
                f"成員人數: {sum([_.member_count or 0 for _ in self.client.guilds if not _.unavailable]):,}\n"
                f"運行時間: {runtime_str}\n"
                "```"
            ),
            inline=False,
        )
        # 營運狀態
        last_hour_count = GetLastHourCommandCount()
        daily_trend = GetDailyTrend(7)
        separator = '\u2500' * 28
        operation_text = f"過去1小時指令觸發次數: {last_hour_count}\n"
        if daily_trend:
            operation_text += f"{separator}\n"
            operation_text += '\n'.join([
                f"{day['date']} | {day['count']:>6,} 次"
                for day in daily_trend[-7:]
            ])

        embed.add_field(
            name="營運狀態",
            value=f"```autohotkey\n{operation_text}\n```",
            inline=False,
        )
        # 最熱門指令
        top_commands = GetTopCommandsSimple(30, 5)
        if top_commands:
            cmd_text = '\n'.join([
                f"{cmd['command']:23s} | {cmd['count']:>6,} 次"
                for cmd in top_commands
            ])
            embed.add_field(
                name="最熱門指令 (過去30天)",
                value=f"```{cmd_text}```",
                inline=False,
            )

        embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/957283103364235284.webp?size=96&quality=lossless')
        UseSlashCommand('help', interaction)
        view = HelpCommandView()
        await interaction.response.send_message(embed=embed, view=view)
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
        
