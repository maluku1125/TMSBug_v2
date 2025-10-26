import discord
from discord import app_commands
from discord.ext import commands
import json
import re

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
        channel="頻道ID或mention (未填則為當前頻道)", 
        mention="標記身分組ID或mention (未填則不進行tag)",
        delete="輸入'確認'來刪除此伺服器的設定 (預設不用輸入)",
        info="輸入'確認'來查看此伺服器的設定 (預設不用輸入)"
    )
    async def servercheck(self, interaction: discord.Interaction, channel: str = None, mention: str = None, delete: str = None, info: str = None):
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
        rolenotfound = False
        channelnotfound = False 
        
        if channel is None:
            channel_id = interaction.channel_id
        else:          
            # 檢查是否為 mention 形式
            mention_match = re.match(r'<#(\d+)>', channel)
            if mention_match:
                channel_id = int(mention_match.group(1))
            else:
                channel_id = int(channel)
                
            targetchannel = interaction.guild.get_channel(channel_id)
            if targetchannel is None:
                channel_id = interaction.channel_id
                channelnotfound = True    
                
                

        if mention is None:
            mention_id = "None"
        else:
            # 檢查是否為 mention 形式
            mention_match = re.match(r'<@&(\d+)>', mention)
            if mention_match:
                mention_id = int(mention_match.group(1))
            else:
                mention_id = int(mention)
                
            targetrole = interaction.guild.get_role(mention_id)
            if targetrole is None:
                mention_id = "None"
                rolenotfound = True    
                
        
        # 使用資料庫儲存設定
        db.set_guild_config(guild_id, channel_id, str(mention_id))
        
         # 發送測試訊息
        try:
            channel = interaction.guild.get_channel(channel_id)
            if channelnotfound == True:
                await interaction.response.send_message(f"配置更新失敗，無法找到目標頻道，設置為當前頻道 (ID: <#{channel_id}>)。")
                await channel.send(f"<@&{mention_id}> 伺服器開機檢查已設定（測試訊息）")
                return
            
            # 檢查機器人是否有發送訊息的權限
            if not channel.permissions_for(channel.guild.me).send_messages:
                await interaction.response.send_message(f"配置已更新，但機器人沒有權限在目標頻道 (ID: <#{channel_id}>) 發送訊息。")
                return
            
            # 檢查身分組是否有效
            if rolenotfound == True:
                await interaction.response.send_message(f"配置已更新，但無法找到目標身分組 (ID: <@&{mention}>)。")
                await channel.send(f"伺服器開機檢查已設定（測試訊息）")
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
        
