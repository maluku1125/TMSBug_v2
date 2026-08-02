import discord
from discord import app_commands
from discord.ext import commands

from functions.SlashCommandManager import UseSlashCommand
from functions.database_manager import GuildFunctionDB

# 初始化資料庫
db = GuildFunctionDB()
    
class Slash_GuildFunctions(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
    #-----------------servercheck-----------------
    @app_commands.command(name="servercheck", description="管理伺服器開機通知設定")
    @app_commands.describe(
        channel="通知頻道 (未填則為當前頻道)",
        mention="標記身分組 (未填則不進行tag)",
        delete="輸入'確認'來刪除此伺服器的設定 (預設不用輸入)",
        info="輸入'確認'來查看此伺服器的設定 (預設不用輸入)"
    )
    async def servercheck(self, interaction: discord.Interaction, channel: discord.TextChannel = None, mention: discord.Role = None, delete: str = None, info: str = None):
        # 私訊中無 guild，直接擋下（DM 的 user 沒有 guild_permissions）
        if interaction.guild is None:
            await interaction.response.send_message("此指令僅能在伺服器中使用。", ephemeral=True)
            return
        # 檢查使用者是否具有管理員身分
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用這個指令，請洽DC伺服器管理員。", ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id)
        
        # 處理查看資訊功能
        if info and info.strip() == "確認":
            config = db.get_guild_config(guild_id)
            
            if config:
                channel_id = config['ServerCheck_Channel']
                mention_role = config['ServerCheck_mention']
                updated_at = config.get('updated_at', '未知')
                
                # 取得頻道和角色資訊
                channel = interaction.guild.get_channel(channel_id)
                channel_info = f"<#{channel_id}>" if channel else f"頻道已不存在 (ID: {channel_id})"
                
                role_info = "無標記"
                if mention_role and mention_role != "None":
                    role = interaction.guild.get_role(int(mention_role))
                    role_info = f"<@&{mention_role}>" if role else f"角色已不存在 (ID: {mention_role})"
                
                embed = discord.Embed(
                    title="📋 伺服器開機檢查設定",
                    description=f"伺服器：**{interaction.guild.name}**",
                    color=0x00ff00
                )
                embed.add_field(name="🔔 通知頻道", value=channel_info, inline=False)
                embed.add_field(name="👥 標記角色", value=role_info, inline=False)
                embed.add_field(name="⏰ 最後更新", value=updated_at, inline=False)
                embed.set_footer(text="使用 /servercheck delete:確認 來刪除設定")
                
                await interaction.response.send_message(embed=embed, ephemeral=False)
            else:
                embed = discord.Embed(
                    title="❌ 無設定資料",
                    description=f"伺服器 **{interaction.guild.name}** 目前沒有開機檢查設定。\n\n使用 `/servercheck` 指令來建立設定。",
                    color=0xff6b6b
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
            UseSlashCommand('ServerCheckInfo', interaction)
            return
        
        # 處理刪除功能
        if delete and delete.strip() == "確認":
            # 檢查是否有現有設定
            existing_config = db.get_guild_config(guild_id)
            if existing_config:
                success = db.remove_guild(guild_id)
                if success:
                    await interaction.response.send_message(
                        "✅ **伺服器開機檢查設定已刪除！**\n"
                        f"已移除伺服器 `{interaction.guild.name}` 的所有開機通知設定。",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("❌ 刪除設定時發生錯誤。", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ 此伺服器目前沒有開機檢查設定可以刪除。", ephemeral=True)
            
            UseSlashCommand('ServerCheckDelete', interaction)
            return
        elif delete and delete.strip() != "":
            await interaction.response.send_message(
                "❌ **刪除確認失敗**\n"
                "如要刪除設定，請在 `delete` 參數中輸入 `確認`。",
                ephemeral=True
            )
            return
        elif info and info.strip() != "":
            await interaction.response.send_message(
                "❌ **查看確認失敗**\n"
                "如要查看設定，請在 `info` 參數中輸入 `確認`。",
                ephemeral=True
            )
            return
        # 參數為 discord.TextChannel / discord.Role 型別，由 Discord 端保證有效，毋須再解析字串
        channel_id = channel.id if channel else interaction.channel_id
        mention_id = mention.id if mention else "None"

        # 使用資料庫儲存設定
        db.set_guild_config(guild_id, channel_id, str(mention_id))

         # 發送測試訊息
        try:
            channel = interaction.guild.get_channel(channel_id)

            # 檢查機器人是否有發送訊息的權限
            if not channel.permissions_for(channel.guild.me).send_messages:
                await interaction.response.send_message(f"配置已更新，但機器人沒有權限在目標頻道 (ID: <#{channel_id}>) 發送訊息。")
                return

            if mention_id != "None":
                await channel.send(f"<@&{mention_id}> 伺服器開機檢查已設定（測試訊息）")
            else:
                await channel.send(f"伺服器開機檢查已設定（測試訊息）")
            
            embed = discord.Embed(
                title="✅ 伺服器開機檢查設定成功",
                description="配置已更新並測試成功！",
                color=0x00ff00
            )
            embed.add_field(name="🔔 通知頻道", value=f"<#{channel_id}>", inline=False)
            embed.add_field(
                name="👥 標記角色", 
                value=f"<@&{mention_id}>" if mention_id != "None" else "無標記",
                inline=False
            )
            embed.add_field(name="📝 說明", value="當遊戲伺服器開機或關機時，會在指定頻道發送通知。", inline=False)
            embed.set_footer(text="使用 /servercheck info:確認 查看設定 | /servercheck delete:確認 刪除設定")
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"配置已更新，但發送測試訊息時發生錯誤：{e}")

        UseSlashCommand('ServerCheckSetting', interaction)

    #-----------------serverannounce-----------------
    @app_commands.command(name="serverannounce_beta", description="管理官網公告通知設定（維護/開關機/手動更新）[測試中]")
    @app_commands.describe(
        channel="通知頻道 (未填則為當前頻道)",
        delete="輸入'確認'來刪除此伺服器的設定 (預設不用輸入)",
        info="輸入'確認'來查看此伺服器的設定 (預設不用輸入)"
    )
    async def serverannounce(self, interaction: discord.Interaction, channel: discord.TextChannel = None, delete: str = None, info: str = None):
        # 私訊中無 guild，直接擋下（DM 的 user 沒有 guild_permissions）
        if interaction.guild is None:
            await interaction.response.send_message("此指令僅能在伺服器中使用。", ephemeral=True)
            return
        # 檢查使用者是否具有管理員身分
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用這個指令，請洽DC伺服器管理員。", ephemeral=True)
            return

        guild_id = str(interaction.guild_id)

        # 查看設定
        if info and info.strip() == "確認":
            config = db.get_announce_config(guild_id)
            if config:
                channel_id = config['Announce_Channel']
                target = interaction.guild.get_channel(channel_id)
                channel_info = f"<#{channel_id}>" if target else f"頻道已不存在 (ID: {channel_id})"
                embed = discord.Embed(
                    title="📋 官網公告通知設定",
                    description=f"伺服器：**{interaction.guild.name}**",
                    color=0x00ff00
                )
                embed.add_field(name="📢 通知頻道", value=channel_info, inline=False)
                embed.add_field(name="⏰ 最後更新", value=config.get('updated_at', '未知'), inline=False)
                embed.set_footer(text="使用 /serverannounce_beta delete:確認 來刪除設定")
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    f"⚠️ 伺服器 **{interaction.guild.name}** 目前沒有公告通知設定。\n使用 `/serverannounce_beta` 指令來建立設定。",
                    ephemeral=True
                )
            UseSlashCommand('ServerAnnounceInfo', interaction)
            return
        elif info and info.strip() != "":
            await interaction.response.send_message(
                "❌ **查看確認失敗**\n如要查看設定，請在 `info` 參數中輸入 `確認`。", ephemeral=True)
            return

        # 刪除設定
        if delete and delete.strip() == "確認":
            if db.remove_announce_channel(guild_id):
                await interaction.response.send_message(
                    "✅ **官網公告通知設定已刪除！**\n"
                    f"已移除伺服器 `{interaction.guild.name}` 的公告通知設定。",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("⚠️ 此伺服器目前沒有公告通知設定可以刪除。", ephemeral=True)
            UseSlashCommand('ServerAnnounceDelete', interaction)
            return
        elif delete and delete.strip() != "":
            await interaction.response.send_message(
                "❌ **刪除確認失敗**\n如要刪除設定，請在 `delete` 參數中輸入 `確認`。", ephemeral=True)
            return

        # 設定頻道（型別參數由 Discord 端保證有效）
        target_channel = channel or interaction.channel
        channel_id = target_channel.id

        if not target_channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                f"❌ 機器人沒有權限在目標頻道 (<#{channel_id}>) 發送訊息，設定未儲存。", ephemeral=True)
            return

        db.set_announce_channel(guild_id, channel_id)

        try:
            await target_channel.send("📢 官網公告通知已設定（測試訊息）")
            embed = discord.Embed(
                title="✅ 官網公告通知設定成功",
                description="配置已更新並測試成功！",
                color=0x00ff00
            )
            embed.add_field(name="📢 通知頻道", value=f"<#{channel_id}>", inline=False)
            embed.add_field(
                name="📝 說明",
                value="官網出現「維護公告 / 開機公告 / 關機公告 / 手動更新下載開放通知」時，會在指定頻道發送公告標題與連結（每30分鐘檢查一次）。",
                inline=False
            )
            embed.add_field(
                name="⚠️ 功能測試中",
                value="此功能目前為測試版本，可能出現通知遺漏、重複、延遲或其他例外狀況，敬請見諒。",
                inline=False
            )
            embed.set_footer(text="使用 /serverannounce_beta info:確認 查看設定 | /serverannounce_beta delete:確認 刪除設定")
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"配置已更新，但發送測試訊息時發生錯誤：{e}")

        UseSlashCommand('ServerAnnounceSetting', interaction)
        
