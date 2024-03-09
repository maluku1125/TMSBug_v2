import random
import datetime
import discord
from discord import app_commands
from discord.ext import commands 
import time
import json
import asyncio

from functions.chatlog import chat_log_save
from functions.getprize import  use_apple, use_fashionbox
from functions.CreateBossDataEmbed import Create_Boss_Data_Embed
from functions.CreatePrizeEmbed import Create_FashionBox_embed, Create_Apple_embed

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

def probably(chance):
    return random.random() < chance

client = discord.Client(intents=intents)
@client.event
async def on_ready():
    print('-'*25)
    print('目前登入身份：', client.user)
    print('-'*25)

    BOTACTIVITY = discord.Activity(
        type=discord.ActivityType.playing, 
        name=f'bug'
        )

    await client.change_presence(
        status = discord.Status.online, 
        activity = BOTACTIVITY
        )

@client.event
async def on_member_join(member):
    print(f'{member} 加入了伺服器')
    print('-'*40)
    for channel in member.guild.channels:
        if channel.id == 1020912280466112564:
            await channel.edit(name=f'全部人數：{member.guild.member_count}')
            print(f'更改了人數')
            print('-'*40)
            break


async def on_member_remove(member):
    print(f'{member} 離開了伺服器')
    print('-'*40)
    for channel in member.guild.channels:
        if channel.id == 1020912280466112564:
            await channel.edit(name=f'全部人數：{member.guild.member_count}')
            print(f'更改了人數')
            print('-'*40)
            break

time_date = ''
speak_count = 0
repeat_yuyu = False    

@client.event
async def on_message_edit(message_before, message_after):
    
    #Chat Log
    #----------------------------------------
    if message_after.guild.id == 420666881368784929:
        if message_after.author.bot != True :
            chat_log_save('Edit_Before', message_before.channel, message_before.author, message_before.content, message_before.attachments, message_before.stickers)
            chat_log_save('Edit_After', message_after.channel, message_after.author, message_after.content, message_after.attachments, message_after.stickers)

            print(f'Edit_Before, Channel：{message_before.channel}, User：{message_before.author}')
            print("Content：", message_before.content, message_before.stickers, message_before.attachments)
            print(f'Edit_After, Channel：{message_after.channel}, User：{message_after.author}')
            print("Content：", message_after.content, message_after.stickers, message_after.attachments)
            print('-'*40) 


@client.event
async def on_message(message):
    # 通用
    now = datetime.datetime.now()

    # 發言log
    global speak_count
    global time_date

    if now.strftime('%m%d') != time_date:
        time_date = now.strftime('%m%d')
        speak_count = 0

    speak_count += 1
    print(f'#{speak_count},Channel：{message.channel}, User：{message.author}')
    print("Content：", message.content, message.stickers, message.attachments)
    print('-'*40)    

    # 略自己
    if message.author == client.user:
        return
    

    #----------------------------------------
    #Chat Log
    #----------------------------------------
    #write
    if message.guild.id == 420666881368784929:
        if message.author.bot != True :
            chat_log_save(speak_count, message.channel, message.author, message.content, message.attachments, message.stickers)
    
    #read
    if message.content == 'chatlog' :
        for r in message.author.roles:
            if r.id == 477757173863153665:
                
                date = time.strftime('%Y%m%d', time.localtime(time.time()))

                await message.channel.send(file = discord.File(f'C:\\Users\\User\\Desktop\\DiscordChatlog\\ChatLog\\{date}_TMS新楓之谷_Chatlog.csv'))
                #chat_log_get()
                return

    #Count ServerMember
    #----------------------------------------
    if message.content == 'count':
        await message.channel.send(f'伺服器總人數：{message.guild.member_count}')
        for channel in message.guild.channels:
            if channel.id == 1020912280466112564:
                await channel.edit(name=f'全部人數：{message.guild.member_count}')
                break

    #Count DailySpeak
    #----------------------------------------
    if message.content == 'speakcount':
        await message.channel.send(f'今日總訊息數:{speak_count}')
    
    #Ping
    if message.content == 'ping':
        if probably(0.90):
            await message.channel.send(f'pong,latency is {round(client.latency*1000)}ms')
        else:
            await message.channel.send(f'pingpingpongpong!, latency is {round(client.latency*1000)}ms')

    #Random img17
    if probably(0.001):
        await message.add_reaction('<:img17:588950160399269889>')
        print(message.channel, ':', message.author, '隨機加上img17表情')
    
    #Flat img17
    if message.content == '<:ban:597267067581890571>' or message.content == '<:ban_g:927438410182963232>' or message.content == '<:ban_w:927423587911077990>':
        await message.add_reaction('<:img17_flat:839749212152528916>')
    
    FashionBox_Date = '230823'
    BoldApple_Date = '230823'
    # 抽時尚
    if message.content == '時尚隨機箱' or message.content == '<:fashion_cube:805310913938456598>' :          
        FashionboxMessage = use_fashionbox(FashionBox_Date, message.channel.id, message.author)
        await message.channel.send(content=f"{FashionboxMessage}") 

    if message.content == 'GET<:fashion_cube:805310913938456598>' or message.content == 'get<:fashion_cube:805310913938456598>' :          
        embed = Create_FashionBox_embed(FashionBox_Date)
        sent_message = await message.channel.send(embed=embed)
            
    # 抽蘋果
    if message.content == '黃金蘋果' or message.content == '<:goldapple:677489297557028864>' :
        GoldAppleMessage = use_apple(BoldApple_Date, message.channel.id, message.author)
        await message.channel.send(content=f"{GoldAppleMessage}")   

    if message.content == 'GET<:goldapple:677489297557028864>' or message.content == 'get<:goldapple:677489297557028864>' :          
        embed = Create_Apple_embed(BoldApple_Date)
        sent_message = await message.channel.send(embed=embed)

    # 抽輪迴
    if message.content == '輪迴抽到有':
        GoldAppleMessage = use_apple('FrenzyTotem', message.channel.id, message.author)
        await message.channel.send(content=f"{GoldAppleMessage}") 
    
    # BOSS資訊    
    boss_names = ['殘暴炎魔','史烏','使烏', '戴米安','守護天使綠水靈','露希妲','威爾','戴斯克','真希拉','頓凱爾','盾凱爾','黑魔法師','受選的賽蓮','賽蓮','監視者卡洛斯','卡洛斯','咖凌'] 
    if message.content in boss_names:        

        embed, num_subtitles= Create_Boss_Data_Embed(message.content, 0)

        if probably(0.02):
            embed, nowbossmode, num_subtitles= Create_Boss_Data_Embed("蟲蟲", 0)  
        sent_message = await message.channel.send(embed=embed)
        await sent_message.add_reaction('🔄')

        Bossmode = [0]   # 將 Bossmode 定義為全域變數

        @client.event
        async def on_reaction_add(reaction, user):
            if user == client.user:
                return  # 忽略機器人自身的反應A

            if reaction.message.author != client.user:
                return  # 忽略機器人所發送訊息以外的反應

            if reaction.message.id != sent_message.id:
                return  # 忽略其他訊息的反應

            if reaction.emoji == '🔄':
                await reaction.remove(user)  # 刪除使用者加上的反應                
                await asyncio.wait_for(switch_boss_mode(), timeout=10)  # 等待使用者反應，設定超時時間為 10 秒                

        async def switch_boss_mode():
            Bossmode[0] = (Bossmode[0] + 1) % num_subtitles

            embed, _ = Create_Boss_Data_Embed(message.content, Bossmode[0])    
            await sent_message.edit(embed=embed)

#slash command
#----------------------------------------

from core.config import token
if __name__ == "__main__":
    client.run(token)
    
    
