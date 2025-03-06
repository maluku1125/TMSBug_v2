
import discord
import datetime
import time
import csv

from wcwidth import wcswidth

Slash_Command_Usage = {}
Slash_Command_Usage_Guild = {}

savedmonth = ''
firstfile = False

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def get_day():
    return datetime.datetime.now().strftime('%Y-%m-%d')

def UseSlashCommand(type, interaction: discord.Interaction):    
    if type in Slash_Command_Usage:
        Slash_Command_Usage[type] += 1
    else:
        Slash_Command_Usage[type] = 1
        
    if interaction.guild.name in Slash_Command_Usage_Guild:
        Slash_Command_Usage_Guild[interaction.guild.name] += 1
    else:
        Slash_Command_Usage_Guild[interaction.guild.name] = 1    
    
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type} #{Slash_Command_Usage[type]}')
    print('-'*40)
    slash_log_save(interaction.guild, interaction.user, type)
 
def slash_log_save(guild, user, commandtype):    
    global savedmonth
    month = time.strftime('%m', time.localtime(time.time()))
    if month != savedmonth :
        savedmonth = month
        firstfile = True
    else:
        firstfile = False

    ChatLog_output_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\SlashLog'
    timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))

    with open(f'{ChatLog_output_path}\\{month}_slashlog.csv', 'a', newline='', encoding='utf-8') as csvfile:

        fieldnames = ['Time', 'Guild', 'User', 'CommandType']        
        writer = csv.DictWriter(csvfile, fieldnames = fieldnames) # 將 dictionary 寫入 CSV 檔 
        if firstfile == True :
            firstfile = False
            writer.writeheader()

        # 寫入資料
        writer.writerow(
            {
            'Time' : timestamp,
            'Guild': guild,
            'User': user,
            'CommandType' : commandtype      
            }
        ) 
    
def pad_string(s, width):
    pad_length = width - wcswidth(s)
    return ' ' * pad_length + s
 
def get_slash_count():
    command_count = {}
    guildlist ={}
    ChatLog_output_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\SlashLog'
    month = time.strftime('%m', time.localtime(time.time()))
    
    try:
        with open(f'{ChatLog_output_path}\\{month}_slashlog.csv', mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                
                command_type = row[3]
                if command_type in command_count:
                    command_count[command_type] += 1
                else:
                    command_count[command_type] = 1
                    
                guild = row[1]
                if guild in guildlist:
                    guildlist[guild] += 1
                else:
                    guildlist[guild] = 1
                
                    
    except FileNotFoundError:
        print("Log file not found.")
    return command_count, guildlist  
    
def GetSlashCommandUsage():
    

    command_count, guildlist = get_slash_count() 
    
    # 設定對齊寬度
    width = 7 
      
    topguild = sorted(guildlist.items(), key=lambda item: item[1], reverse=True)[:5]
    topguild_message = ""    
    for command, count in topguild:
        formatted_count = f"{count:,}"
        topguild_message += f'{pad_string(str(formatted_count), width)} : {command}\n'
    if topguild_message == "":
        topguild_message = "No guild commands have been used yet." 
    
    
    sorted_command_count = sorted(command_count.items(), key=lambda item: item[1], reverse=True)
    command_count_message = ""
    for command, count in sorted_command_count:
        command_count_message += f'{pad_string(str(count), width)} : {command}\n'
    if command_count_message == "":
        command_count_message = "No commands have been logged yet."
              
    embed = discord.Embed(
        title=f"**Command Dashboard**", 
        description = f'', 
        color=0x32EBA7,
        ) 
    
    embed.add_field(
        name="**Top Guild**", 
        value=f'```autohotkey\n{topguild_message}```', 
        inline=False
        )    
    embed.add_field(
        name="**Command Used**", 
        value=f'```autohotkey\n{command_count_message}```', 
        inline=False
        )              
     
    return embed
    
    
        
            
        