import asyncio
import io
import json
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import psutil
import time

from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed
from functions.MSCrawler import Format_ApplePrizeData, Format_FashionBoxPrizeData, save_apple_json_file, save_fashionbox_json_file
from functions.GetPrize import reloaddata
from ..SlashCommandManager import UseSlashCommand, GetSlashCommandUsage, SaveSystemStats, GetLastHourCommandCount, GetTopCommandsSimple, GetDailyTrend, GetMonthlyReport
from tmsapi.logger import get_last_hour_count as GetLastHourAPICount, get_daily_counts as GetDailyAPICounts
 
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
version = 'v3.12.4'

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
                "/events當前活動 - 顯示當前進行中的活動\n"
                "/prize當期抽獎機率 - 查詢當期抽獎機率\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="計算與模擬",
            value=(
                "```\n"
                "/solerda碎片進度 - 查詢角色六轉進度與所需材料\n"
                "/formulas各式公式 - 各種公式的簡易計算機\n"
                "/scrolls卷軸模擬器 - 卷軸模擬器\n"
                "/cubes洗方塊 - 洗方塊模擬器\n"
                "/starforce衝星 - 衝星模擬器\n"
                "/getprize抽 - 黃金蘋果抽輪迴碑石模擬\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="娛樂",
            value=(
                "```\n"
                "/battle對戰 - 與其他玩家的本尊角色決鬥(雙方需先用 /setting 綁定 1本)\n"
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
                "/champion聯盟冠軍 - API 聯盟冠軍查詢\n"
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
                "/serverannounce - 官網公告通知設定(僅群主)\n"
                "/setting設定 - 綁定角色、角色動作、對戰感言\n"
                "```"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


#-----------------開發者面板-----------------
# 作者執行 /help 時另外送出（ephemeral，只有作者看得到），取代原本的 dev_func 參數。
# 結果一律 ephemeral：/help 常在公開頻道用，避免點一下就把統計貼到頻道上。

def _error_embed(title, e):
    return discord.Embed(title=f"❌ {title}", description=f"錯誤: {e}", color=discord.Color.red())


async def _send_text(interaction: discord.Interaction, text: str, filename: str, fence: str = None):
    """Discord 訊息上限 2000 字，超過就改成附檔。"""
    content = f"```{fence}\n{text}\n```" if fence is not None else text
    if len(content) <= 2000:
        await interaction.followup.send(content=content, ephemeral=True)
    else:
        file = discord.File(io.BytesIO(text.encode('utf-8')), filename=filename)
        await interaction.followup.send(file=file, ephemeral=True)


class MonthlyReportSelect(discord.ui.Select):
    def __init__(self):
        today = datetime.date.today()
        y, m = today.year, today.month
        options = []
        for i in range(12):
            ym = f"{y:04d}-{m:02d}"
            options.append(discord.SelectOption(label=ym + ("（本月，未結束）" if i == 0 else ""), value=ym))
            y, m = (y, m - 1) if m > 1 else (y - 1, 12)
        super().__init__(placeholder="📅 月報（選擇月份）", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        start = time.time()
        await interaction.response.defer(ephemeral=True, thinking=True)
        year, month = (int(x) for x in self.values[0].split('-'))
        try:
            report_text = await asyncio.to_thread(GetMonthlyReport, year, month)
            await _send_text(interaction, report_text, f"monthly_{self.values[0]}.txt")
            UseSlashCommand('help_monthly', interaction, time.time() - start)
        except Exception as e:
            await interaction.followup.send(embed=_error_embed("月報載入失敗", e), ephemeral=True)
            UseSlashCommand('help_monthly', interaction, time.time() - start, False)


class DevPanelView(discord.ui.View):
    def __init__(self, client: commands.Bot):
        super().__init__(timeout=600)
        self.client = client
        self.add_item(MonthlyReportSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) == owner_id:
            return True
        await interaction.response.send_message("僅限作者使用", ephemeral=True)
        return False

    @discord.ui.button(label="儀表板", style=discord.ButtonStyle.primary, emoji="📊", row=0)
    async def dashboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        start = time.time()
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            guild_count = len(self.client.guilds)
            user_count = sum([_.member_count or 0 for _ in self.client.guilds if not _.unavailable])

            # 兩個都是同步 SQLite 查詢，丟到執行緒免得凍住 shard
            def work():
                SaveSystemStats(guild_count, user_count)
                return GetSlashCommandUsage(30, self.client)

            embed = await asyncio.to_thread(work)
            await interaction.followup.send(embed=embed, ephemeral=True)
            UseSlashCommand('help_dashboard', interaction, time.time() - start)
        except Exception as e:
            await interaction.followup.send(embed=_error_embed("儀表板載入失敗", e), ephemeral=True)
            UseSlashCommand('help_dashboard', interaction, time.time() - start, False)

    @discord.ui.button(label="查看抽獎表", style=discord.ButtonStyle.secondary, emoji="🎁", row=0)
    async def prize_view_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            # 會開 headless Chrome 爬官網，要好幾秒，必須丟執行緒
            apple, fashionbox = await asyncio.to_thread(
                lambda: (Format_ApplePrizeData(), Format_FashionBoxPrizeData()))
            text = json.dumps({'黃金蘋果': apple, '時尚隨機箱': fashionbox}, ensure_ascii=False, indent=1)
            await _send_text(interaction, text, "prizetable.json", fence="json")
        except Exception as e:
            await interaction.followup.send(embed=_error_embed("抽獎表讀取失敗", e), ephemeral=True)

    @discord.ui.button(label="更新抽獎表", style=discord.ButtonStyle.secondary, emoji="💾", row=0)
    async def prize_save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            appleresult, fashionboxresult = await asyncio.to_thread(
                lambda: (save_apple_json_file(), save_fashionbox_json_file()))
            await interaction.followup.send(
                f"已更新抽獎機率表\n黃金蘋果 : {appleresult}\n時尚隨機箱 : {fashionboxresult}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(embed=_error_embed("抽獎表更新失敗", e), ephemeral=True)

    @discord.ui.button(label="重載抽獎表", style=discord.ButtonStyle.secondary, emoji="🔄", row=0)
    async def prize_reload_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            reloaddata()
            await interaction.response.send_message("已重新加載抽獎機率表(黃金蘋果,時尚隨機箱)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(embed=_error_embed("抽獎表重載失敗", e), ephemeral=True)


class Slash_BasicCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------ping-----------------
    @app_commands.command(name="ping", description="BOT延遲")
    async def ping(self, interaction: discord.Interaction):
        bot_latency = round(self.client.latency * 1000)
        UseSlashCommand('ping', interaction)
        await interaction.response.send_message(f"pong, latency is {bot_latency} ms.")

    #-----------------help-----------------
    # 作者執行時，除了一般說明外，另外送出只有作者看得到的開發者面板（DevPanelView）
    @app_commands.command(name="help", description="BOT資訊與指令說明")
    async def help(self, interaction: discord.Interaction):
        # 先 defer：下面的營運統計要查 API 請求記錄，沒先回應的話
        # 互動 3 秒就過期，使用者只會看到「應用程式沒有回應」
        if not interaction.response.is_done():
            await interaction.response.defer()
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
        # 這四個都是同步 SQLite 查詢，其中 API 記錄那張表有 3,278 萬筆，
        # 直接在 event loop 上跑會把所有 shard 一起凍住十幾秒
        # （2026-09-13 實測 12.9 秒，heartbeat blocked）。丟到執行緒。
        (last_hour_count, last_hour_api_count, daily_trend,
         api_daily) = await asyncio.to_thread(
            lambda: (GetLastHourCommandCount(), GetLastHourAPICount(),
                     GetDailyTrend(7), GetDailyAPICounts(7)))
        separator = '\u2500' * 28
        operation_text = f"指令觸發/hr: {last_hour_count}\n"
        operation_text += f"API請求/hr: {last_hour_api_count}\n"
        if daily_trend:
            operation_text += f"{separator}\n"
            operation_text += '\n'.join([
                f"{day['date']} | {day['count']:>6,} | {api_daily.get(day['date'], 0):>6,}"
                for day in daily_trend[-7:]
            ])

        embed.add_field(
            name="營運狀態",
            value=f"```autohotkey\n{operation_text}\n```",
            inline=False,
        )
        # 最熱門指令
        top_commands = await asyncio.to_thread(GetTopCommandsSimple, 30, 5)
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
        # 虛線足標：一整條連續虛線撐住 embed 寬度，避免跑版（數字可調整寬度）
        embed.set_footer(text='-' * 72)
        UseSlashCommand('help', interaction)
        view = HelpCommandView()
        await interaction.edit_original_response(embed=embed, view=view)
        if str(interaction.user.id) == owner_id:
            await interaction.followup.send("🛠️ 開發者面板（只有你看得到）", view=DevPanelView(self.client), ephemeral=True)
    #-----------------MEMO-----------------
    @app_commands.command(name="練等備忘", description="練等前的檢查清單（設定、裝備、消耗品）")
    async def farmingmemo(self, interaction: discord.Interaction):
        embed = CreateFarmingEmbed()
        UseSlashCommand('farmingmemo', interaction)
        await interaction.response.send_message(embed=embed)

  
    @app_commands.command(name="打王備忘", description="打王前的檢查清單（設定、裝備、技能、消耗品）")
    async def combatmemo(self, interaction: discord.Interaction):
        embed = CreateCombatEmbed()
        UseSlashCommand('Bossingmemo', interaction)
        await interaction.response.send_message(embed=embed)
        
