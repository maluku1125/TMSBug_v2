import socket
from discord.ext import commands, tasks
import discord
import json
import datetime
import asyncio

HOST = [
  "202.80.104.24",
  "202.80.104.25",
  "202.80.104.26",
  "202.80.104.27",
  "202.80.104.28",
  "202.80.104.29"
]

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

class Loop_ServerCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ret = {}
        self.google = {}
        self.server_status = ''
        self.offline_count = 0
        self.check_server_status.start()

    def cog_unload(self):
        self.server_up_check.cancel()
        self.server_down_check.cancel()

    def worker(self, host, ret):
        port = 8484
        if host == 'www.google.com':
            port = 80
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        try:
            s.connect((host, port))
            s.shutdown(socket.SHUT_RD)
        except socket.timeout as err:
            ret[host] = "timeout"
        except OSError as err:
            ret[host] = "os error"
        except Exception as err:
            ret[host] = "unknown error"
        else:
            ret[host] = "online"
        return     
    
    def load_guild_function(self):
        with open(f'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\Guild_Function.json', 'r', encoding='utf-8') as f:
            return json.load(f)  

    @tasks.loop(minutes = 1)
    async def check_server_status(self):
        print("check_server_status...")
        for h in HOST:    
            self.worker(h, self.ret)
        server_online = any(status == 'online' for status in self.ret.values())    

        if server_online:
            await self.bot.change_presence(activity=discord.Game(name="MapleStory"))
            self.server_down_check.start()
            self.server_status = 'online'
            self.check_server_status.cancel()
        else:
            await self.bot.change_presence(activity=discord.CustomActivity(name="TMS Server Offline"))
            self.server_up_check.start()
            self.server_status = 'offline'
            self.check_server_status.cancel()

    @tasks.loop(minutes = 1)
    async def server_up_check(self):
        print(f"{get_now_HMS()}, server_up_check...")

        for h in HOST:    
            self.worker(h, self.ret)

        server_online = any(status == 'online' for status in self.ret.values())
 
        if server_online and self.server_status != 'online':

            await self.bot.change_presence(activity=discord.Game(name="MapleStory")) 

            if self.offline_count >= 30: 
                channelsendcountsuccess = 0
                channelsendcountfail = 0   
                
                Guild_Function = self.load_guild_function()
                
                for guild_id, guild_config in Guild_Function.items():
                    
                    channel_id = guild_config['ServerCheck_Channel']
                    if not channel_id:
                        print(f"{get_now_HMS()}, Guild: {guild_id} dont have ServerCheck_Channel")
                        continue
                    
                    channel = self.bot.get_channel(channel_id)
                    
                    if channel is None:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} message not sent")
                        channelsendcountfail += 1
                        continue
                    
                    if channel is None or not channel.permissions_for(channel.guild.me).send_messages:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} has no permission")
                        channelsendcountfail += 1
                        continue
                        
                    mention = guild_config.get('ServerCheck_mention')
                    
                    try:
                        if mention and mention != "None":
                            await channel.send(f"<@&{mention}> 登入口已開啟。")
                            print(f"{get_now_HMS()}, ChannelID: {channel_id} message sent successfully") 
                            channelsendcountsuccess += 1
                        else:
                            await channel.send("登入口已開啟。")
                            print(f"{get_now_HMS()}, ChannelID: {channel_id} message sent successfully") 
                            
                        await asyncio.sleep(1)
                        channelsendcountsuccess += 1
                        
                    except Exception as e:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} error: {e}")
                        channelsendcountfail += 1
                        continue
                        
                        
            self.offline_count = 0    
            self.server_status = 'online'
            self.server_up_check.cancel()
            self.server_down_check.start()
            print('Server turn online')
            print(f"Successfully sent message to {channelsendcountsuccess} channel, {channelsendcountfail} channel failed")
            print("-"*30)
        else:              
            self.worker('www.google.com', self.google)
            if self.google['www.google.com'] == 'online':
                self.offline_count += 1
                
                print(f'Server is offline {self.offline_count}')
                print("-"*30)
     
    @tasks.loop(minutes = 5)
    async def server_down_check(self):
        print(f"{get_now_HMS()}, server_down_check...")
            
        for h in HOST:    
            self.worker(h, self.ret)

        server_online = any(status == 'online' for status in self.ret.values())
          
        if not server_online and self.server_status != 'offline':
        # if server_online and self.server_status != 'offline':
            
            await self.bot.change_presence(activity=discord.CustomActivity(name="TMS Server Offline"))
            channelsendcountsuccess = 0
            channelsendcountfail = 0
            
            Guild_Function = self.load_guild_function()
            
            for guild_id, guild_config in Guild_Function.items():
                channel_id = guild_config['ServerCheck_Channel']
                
                if not channel_id:
                    print(f"{get_now_HMS()}, Guild: {guild_id} dont have ServerCheck_Channel")
                    continue
                
                channel = self.bot.get_channel(channel_id)                
                if channel is None:
                    print(f"{get_now_HMS()}, ChannelID: {channel_id} message not sent")
                    channelsendcountfail += 1
                    continue
                
                if channel is None or not channel.permissions_for(channel.guild.me).send_messages:
                    print(f"{get_now_HMS()}, ChannelID: {channel_id} has no permission")
                    channelsendcountfail += 1
                    continue
                                
                mention = guild_config.get('ServerCheck_mention')
                
                try:
                    if mention and mention != "None":
                        await channel.send(f"MapleStory 登入口已關閉。")
                        # await channel.send(f"群發訊息測試中，打擾抱歉orz")
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} message sent successfully") 
                    else:
                        await channel.send("MapleStory 登入口已關閉。")
                        # await channel.send(f"群發訊息測試中，打擾抱歉orz")
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} message sent successfully") 
                                  
                    channelsendcountsuccess += 1
                    await asyncio.sleep(1)
                    
                except Exception as e:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} error: {e}")
                        channelsendcountfail += 1
                        continue
                    
            self.server_status = 'offline'
            self.server_up_check.start()
            self.server_down_check.cancel()
            print('Server turn offline')
            print(f"Successfully sent message to {channelsendcountsuccess} channel, {channelsendcountfail} channel failed")
            print("-"*30)
        else:

            await self.bot.change_presence(activity=discord.Game(name="MapleStory"))       
            
            print(f'Server is online')
            print("-"*30)

       