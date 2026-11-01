import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import psutil
import time

from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed
from ..SlashCommandManager import UseSlashCommand, GetLastHourCommandCount, GetTopCommandsSimple, GetDailyTrend
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
version = 'v3.12.8'

# 在程式開始運行時記錄當前的時間
start_time = time.time()

# 指令分類。鍵 = 指令名，值 = 分類；字典的順序就是清單裡的順序。
#
# ⚠️ 清單**本身**是從 client.tree 即時產生的，這張表只決定「分到哪一組、
# 排第幾個」。沒列到的指令會掉進「其他」，所以之後新增指令就算忘了更新
# 這裡，它一樣會出現在 /help 上。
#
# 會改成這樣是因為以前整份清單是手寫的：accounttracking 上線之後，
# /help 裡一直沒有它（2026-10-30 對帳才發現）。手寫清單遲早會漏。
CATEGORY = {
    # 基本功能
    'help': '基本功能',
    'ping': '基本功能',
    '打王備忘': '基本功能',
    '練等備忘': '基本功能',
    # BOSS查詢
    'bossarc困王': 'BOSS查詢',
    'bossaut困王': 'BOSS查詢',
    'easyboss里程周王': 'BOSS查詢',
    # 活動與查詢
    'events當前活動': '活動與查詢',
    'prize當期抽獎機率': '活動與查詢',
    # 計算與模擬
    'solerda碎片進度': '計算與模擬',
    'formulas各式公式': '計算與模擬',
    'scrolls卷軸模擬器': '計算與模擬',
    'cubes洗方塊': '計算與模擬',
    'starforce衝星': '計算與模擬',
    'getprize抽': '計算與模擬',
    # 娛樂
    'battle對戰': '娛樂',
    # API功能
    'character角色查詢': 'API功能',
    'guild公會查詢': 'API功能',
    'accounttracking帳號追蹤': 'API功能',
    'exptracking經驗追蹤': 'API功能',
    'uniontracking戰地追蹤': 'API功能',
    'champion聯盟冠軍': 'API功能',
    'union戰地查詢': 'API功能',
    'rank排行': 'API功能',
    'apianalyse楓谷分析': 'API功能',
    # 設定
    'servercheck': '設定',
    'serverannounce': '設定',
    'setting設定': '設定',
}

CATEGORY_ORDER = ('基本功能', 'BOSS查詢', '活動與查詢', '計算與模擬',
                  '娛樂', 'API功能', '設定', '其他')

# 指令自己的 description 是給 Discord 的輸入提示用的，有幾個塞進清單會
# 換行把版面撐爛，或是少了只有這裡才講得清楚的前提（例如對戰要先綁本尊）。
# 這裡覆寫成短版；沒列到的就直接用指令自己的 description。
SHORT = {
    'battle對戰': '與其他玩家的本尊角色決鬥（雙方需先用 /setting 綁 1 本）',
    'servercheck': '伺服器開機通知設定（僅群主）',
    'serverannounce': '官網公告通知設定（僅群主）',
    'apianalyse楓谷分析': '職業、世界、等級、寶玉、裝備、CD帽、冠軍分析',
    'accounttracking帳號追蹤': '列出同帳號所有角色的等級、經驗、戰力與成長',
}

_ORDER = {name: i for i, name in enumerate(CATEGORY)}


def build_command_embed(client) -> discord.Embed:
    """指令清單。內容來自 client.tree，所以不會跟實際註冊的指令脫節。"""
    groups = {}
    for cmd in client.tree.get_commands():
        if not isinstance(cmd, app_commands.Command):
            continue                    # Group 沒有自己的說明，略過
        cat = CATEGORY.get(cmd.name, '其他')
        desc = SHORT.get(cmd.name) or cmd.description or ''
        groups.setdefault(cat, []).append(
            (_ORDER.get(cmd.name, 9999), f'/{cmd.name} - {desc}'))

    embed = discord.Embed(title='📋 指令說明', color=0x32EBA7)
    total = 0
    for cat in CATEGORY_ORDER:
        rows = groups.get(cat)
        if not rows:
            continue
        rows.sort()
        total += len(rows)
        embed.add_field(
            name=cat,
            value='```\n' + '\n'.join(r[1] for r in rows) + '\n```',
            inline=False)
    embed.set_footer(text=f'共 {total} 個指令')
    return embed


class HelpCommandView(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=180)
        self.client = client

    @discord.ui.button(label="指令說明", style=discord.ButtonStyle.primary, emoji="📋")
    async def command_info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            embed=build_command_embed(self.client), ephemeral=True)


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
    # 作者與一般使用者看到的內容相同（2026-09-20 移除開發者面板）——
    # 儀表板與月報後台都有，而且那邊不受 Discord 的 3 秒互動逾時限制。
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
        view = HelpCommandView(self.client)
        await interaction.edit_original_response(embed=embed, view=view)
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
        

# 讓這支可以被 load_extension／reload_extension 熱抽換（2026-09-20）。
# setup_hook 改用 load_extension 之後，後台就能單獨重載這一個 cog，
# 不必為了改一行文案重啟整台 Bot（5 個 shard、近 5,000 個伺服器要重連）。
async def setup(client: commands.Bot):
    await client.add_cog(Slash_BasicCommands(client))
