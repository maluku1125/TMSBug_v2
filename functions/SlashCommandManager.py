
import discord
from discord.ext import commands
from discord import app_commands
import datetime

from wcwidth import wcswidth

Slash_Command_Usage = {}
Slash_Command_Usage_Guild = {}
Today_Slash_Command_Usage = {}
Today_Slash_Command_Usage_Guild = {}

today = None

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def get_day():
    return datetime.datetime.now().strftime('%Y-%m-%d')

def UseSlashCommand(type, interaction: discord.Interaction):
    
    global today, Today_Slash_Command_Usage, Today_Slash_Command_Usage_Guild
    
    if today == None:
        today = get_day()
    
    if type in Slash_Command_Usage:
        Slash_Command_Usage[type] += 1
    else:
        Slash_Command_Usage[type] = 1
        
    if interaction.guild.name in Slash_Command_Usage_Guild:
        Slash_Command_Usage_Guild[interaction.guild.name] += 1
    else:
        Slash_Command_Usage_Guild[interaction.guild.name] = 1    
    
    if get_day() == today :
        if type in Today_Slash_Command_Usage:
            Today_Slash_Command_Usage[type] += 1
        else:
            Today_Slash_Command_Usage[type] = 1
               
        if interaction.guild.name in Today_Slash_Command_Usage_Guild:
            Today_Slash_Command_Usage_Guild[interaction.guild.name] += 1
        else:
            Today_Slash_Command_Usage_Guild[interaction.guild.name] = 1
    else:
        Today_Slash_Command_Usage = {}
        Today_Slash_Command_Usage_Guild = {}
        today = get_day()
    
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type} #{Slash_Command_Usage[type]}')
    print('-'*40)
    
def pad_string(s, width):
    pad_length = width - wcswidth(s)
    return s + ' ' * pad_length
    
def GetSlashCommandUsage():
    
    global today, Today_Slash_Command_Usage, Today_Slash_Command_Usage_Guild

    usage_message = ""
    today_usage_message = ""
    topguild_message = ""
    today_topguild_message = ""
    
    # 設定對齊寬度
    width = 20
    
    topusage = sorted(Slash_Command_Usage.items(), key=lambda item: item[1], reverse=True)
    for command, count in topusage:
         usage_message += f'{pad_string(command, width)} : {count}\n'
    if usage_message == "":
        usage_message = "No commands have been used yet."   
    
    topguild = sorted(Slash_Command_Usage_Guild.items(), key=lambda item: item[1], reverse=True)[:10]
    for command, count in topguild:
        topguild_message += f'{pad_string(command, width)} : {count}\n'
    if topguild_message == "Top 10 Guild Command Usage:\n":
        topguild_message = "No guild commands have been used yet." 
    # Today
    today_topusagge = sorted(Today_Slash_Command_Usage.items(), key=lambda item: item[1], reverse=True)
    for command, count in today_topusagge:
        today_usage_message += f'{pad_string(command, width)} : {count}\n'
    if today_usage_message == "":
        today_usage_message = "No commands have been used yet." 
    
    today_topguild = sorted(Today_Slash_Command_Usage_Guild.items(), key=lambda item: item[1], reverse=True)[:10]
    for command, count in today_topguild:
        today_topguild_message += f'{pad_string(command, width)} : {count}\n'
    if today_topguild_message == "Top 10 Guild Command Usage:\n":
        today_topguild_message = "No guild commands have been used yet."
    
    print("Command Usage")
    print(usage_message)
    print("Top Guild")
    print(topguild_message)
    print("Command Usage(today)")
    print(today_usage_message)
    print("Top Guild(today)")
    print(today_topguild_message)
        
    embed = discord.Embed(
        title=f"**Command Dashboard**", 
        description = f'', 
        color=0x32EBA7,
        ) 
    
    embed.add_field(
        name="**Command Used**", 
        value=f'```autohotkey\n{usage_message}```', 
        inline=False
        )
        
    embed.add_field(
        name="**Top Guild**", 
        value=f'```autohotkey\n{topguild_message}```', 
        inline=False
        )  
    
    embed.add_field(
        name="**Command Used(today)**", 
        value=f'```autohotkey\n{today_usage_message}```', 
        inline=False
        )
        
    embed.add_field(
        name="**Top Guild(today)**", 
        value=f'```autohotkey\n{today_topguild_message}```', 
        inline=False
        )  
    
    
    return embed
    
    
        
            
        