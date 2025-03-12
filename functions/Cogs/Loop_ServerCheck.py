import socket
from discord.ext import commands, tasks
import discord
import json


with open(f'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\Guild_Function.json', 'r', encoding='utf-8') as f:
    Guild_Function = json.load(f)

HOST = [
  "202.80.104.24",
  "202.80.104.25",
  "202.80.104.26",
  "202.80.104.27",
  "202.80.104.28",
  "202.80.104.29"
]

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
        print("server_up_check...")

        for h in HOST:    
            self.worker(h, self.ret)

        server_online = any(status == 'online' for status in self.ret.values())
 
        if server_online and self.server_status != 'online':

            await self.bot.change_presence(activity=discord.Game(name="MapleStory")) 

            if self.offline_count >= 30:             
                for guild_id, guild_config in Guild_Function.items():
                    channel_id = guild_config['ServerCheck_Channel']
                    channel = self.bot.get_channel(channel_id)
                    channelsendcount = 0
                    if channel is None:
                        print(f"頻道ID {channel_id} 不存在或無效")
                        continue
                    mention = guild_config.get('ServerCheck_mention')
                    if mention and mention != "None":
                        await channel.send(f"<@&{mention}> 登入口已開啟。")
                        channelsendcount += 1
                    else:
                        await channel.send("登入口已開啟。")
                        channelsendcount += 1
                        
                        
            self.offline_count = 0    
            self.server_status = 'online'
            self.server_up_check.cancel()
            self.server_down_check.start()
            print('Server turn online')
            print(f" sent message to {channelsendcount} channel")
            print("-"*30)
        else:              
            self.worker('www.google.com', self.google)
            if self.google['www.google.com'] == 'online':
                self.offline_count += 1
                print(f'Server is offline {self.offline_count}')
                print("-"*30)
     
    @tasks.loop(minutes = 10)
    async def server_down_check(self):
        print("server_down_check...")
            
        for h in HOST:    
            self.worker(h, self.ret)

        server_online = any(status == 'online' for status in self.ret.values())
          
        if not server_online and self.server_status != 'offline':

            await self.bot.change_presence(activity=discord.CustomActivity(name="TMS Server Offline"))

            for guild_id, guild_config in Guild_Function.items():
                channel_id = guild_config['ServerCheck_Channel']
                channel = self.bot.get_channel(channel_id)
                channelsendcount = 0
                if channel is None:
                    print(f"頻道ID {channel_id} 不存在或無效")
                    continue
                mention = guild_config.get('ServerCheck_mention')
                if mention and mention != "None":
                    await channel.send(f"MapleStory 登入口已關閉。")
                    channelsendcount += 1
                else:
                    await channel.send("MapleStory 登入口已關閉。")
                    channelsendcount += 1
                    
            self.server_status = 'offline'
            self.server_up_check.start()
            self.server_down_check.cancel()
            print('Server turn offline')
            print(f" sent message to {channelsendcount} channel")
            print("-"*30)
        else:

            await self.bot.change_presence(activity=discord.Game(name="MapleStory"))             

            print(f'Server is online')
            print("-"*30)

       