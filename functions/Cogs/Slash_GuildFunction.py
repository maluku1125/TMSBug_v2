import discord
from discord import app_commands
from discord.ext import commands
import json
import re

from functions.SlashCommandManager import UseSlashCommand 

config_file_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\Guild_Function.json'

with open(config_file_path, 'r', encoding='utf-8') as f:
    Guild_Function = json.load(f)
    
class Slash_GuildFunctions(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
    #-----------------servercheck-----------------
    @app_commands.command(name="servercheck", description="新增或更新開機通知")
    @app_commands.describe(channel="頻道ID或mention (未填則為當前頻道)", mention="標記身分組ID或mention (未填則不進行tag)")
    async def servercheck(self, interaction: discord.Interaction, channel: str = None, mention: str = None):
        # 檢查使用者是否具有管理員身分

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("你沒有權限使用這個指令，請洽DC伺服器管理員。", ephemeral=True)
            return
        
        guild_id = str(interaction.guild_id)
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
                
        
        if guild_id not in Guild_Function:
            Guild_Function[guild_id] = {}
                     
        Guild_Function[guild_id]['ServerCheck_Channel'] = channel_id
        Guild_Function[guild_id]['ServerCheck_mention'] = mention_id
        
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
            
            await interaction.response.send_message(
                f"伺服器開機檢查配置已更新並測試成功：\n目標頻道: <#{channel_id}>\n標記身分組: <@&{mention_id}>" 
                if mention_id != "None" else 
                f"伺服器開機檢查配置已更新並測試成功：\n目標頻道: <#{channel_id}>\n標記身分組: 無"
            )
        except Exception as e:
            await interaction.response.send_message(f"配置已更新，但發送測試訊息時發生錯誤：{e}")

        with open(config_file_path, 'w') as f:
            json.dump(Guild_Function, f, indent=4)

        UseSlashCommand('ServerCheckSetting', interaction)
        
