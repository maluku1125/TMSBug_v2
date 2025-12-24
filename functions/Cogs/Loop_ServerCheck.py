import socket
from discord.ext import commands, tasks
import discord
import json
import datetime
import asyncio
from functions.database_manager import GuildFunctionDB
from concurrent.futures import ThreadPoolExecutor

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

def removeguild(db, guild_id):
    """從資料庫移除 guild 設定"""
    success = db.remove_guild(guild_id)
    if success:
        print(f"remove guild {guild_id} from database")
    else:
        print(f"guild {guild_id} not found in database")
    return success

class Loop_ServerCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ret = {}
        self.google = {}
        self.server_status = ''
        self.offline_count = 0
        self.db = GuildFunctionDB()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.check_server_status.start()

    def cog_unload(self):
        self.server_up_check.cancel()
        self.server_down_check.cancel()
        self.executor.shutdown(wait=False)

    def worker(self, host, ret):
        """同步socket連接（在線程中執行）"""
        port = 8484
        if host == 'www.google.com':
            port = 80
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)  # 增加timeout到3秒，避免因網路延遲誤判
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
        finally:
            try:
                s.close()
            except:
                pass
        return

    async def async_worker(self, host):
        """異步執行socket連接，使用線程池避免阻塞事件循環"""
        loop = asyncio.get_event_loop()
        try:
            ret = {}
            await loop.run_in_executor(self.executor, self.worker, host, ret)
            return ret
        except Exception as e:
            return {host: "error"}     
    
    def load_guild_function(self):
        """從資料庫載入所有 Guild 設定"""
        return self.db.get_all_guild_configs()  

    @tasks.loop(minutes = 1)
    async def check_server_status(self):
        print("check_server_status...")
        tasks = [self.async_worker(h) for h in HOST]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                self.ret.update(result)
        
        server_online = any(status == 'online' for status in self.ret.values())    

        if server_online:
            await self.bot.change_presence(activity=discord.Game(name="MapleStory"))
            self.server_down_check.start()
            self.server_status = 'online'
            self.check_server_status.cancel()
        else:
            await self.bot.change_presence(activity=discord.CustomActivity(name="TMS 登入口關閉中"))
            self.server_up_check.start()
            self.server_status = 'offline'
            self.check_server_status.cancel()

    @tasks.loop(minutes = 1)
    async def server_up_check(self):
        print(f"{get_now_HMS()}, server_up_check...")

        tasks = [self.async_worker(h) for h in HOST]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                self.ret.update(result)

        server_online = any(status == 'online' for status in self.ret.values())
 
        if server_online and self.server_status != 'online':

            await self.bot.change_presence(activity=discord.Game(name="MapleStory")) 

            if self.offline_count >= 30:
                # 發送通知前先確認Bot網路狀態正常
                network_check = {}
                self.worker('www.google.com', network_check)
                
                if network_check.get('www.google.com') != 'online':
                    print(f"{get_now_HMS()}, Bot network issue detected, skipping notifications")
                    # 不重置offline_count，等下次網路正常時再發送
                    return
                
                channelsendcountsuccess = 0
                channelsendcountfail = 0   
                
                Guild_Function = self.load_guild_function()
                remove_list = []
                
                for guild_id, guild_config in Guild_Function.items():
                    
                    channel_id = guild_config['ServerCheck_Channel']
                    if not channel_id:
                        print(f"{get_now_HMS()}, Guild: {guild_id} dont have ServerCheck_Channel")
                        remove_list.append(guild_id)
                        channelsendcountfail += 1
                        continue
                    
                    channel = self.bot.get_channel(channel_id)
                    
                    if channel is None:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} message not sent")
                        remove_list.append(guild_id)
                        channelsendcountfail += 1
                        continue
                    
                    if channel is None or not channel.permissions_for(channel.guild.me).send_messages:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} has no permission")
                        remove_list.append(guild_id)
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
                            
                        await asyncio.sleep(0.02)
                        channelsendcountsuccess += 1
                        
                    except Exception as e:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} error: {e}")
                        
                        # 延遲後重試一次，避免因短暫問題誤判
                        await asyncio.sleep(2)
                        try:
                            if mention and mention != "None":
                                await channel.send(f"<@&{mention}> 登入口已開啟。")
                            else:
                                await channel.send("登入口已開啟。")
                            print(f"{get_now_HMS()}, ChannelID: {channel_id} retry successful")
                            channelsendcountsuccess += 1
                        except Exception as retry_error:
                            print(f"{get_now_HMS()}, ChannelID: {channel_id} retry failed: {retry_error}")
                            
                            # 重試失敗後檢查網路狀況
                            network_status = {}
                            self.worker('www.google.com', network_status)
                            
                            # 只有在網路正常但持續發送失敗時才刪除guild
                            if network_status.get('www.google.com') == 'online':
                                print(f"{get_now_HMS()}, Network is online but send failed twice, removing guild {guild_id}")
                                remove_list.append(guild_id)
                            else:
                                print(f"{get_now_HMS()}, Network issue detected, skipping guild removal for {guild_id}")
                            
                            channelsendcountfail += 1
                        continue
                    
                for gid in remove_list:
                    removeguild(self.db, gid)
                 
                        
            self.offline_count = 0    
            self.server_status = 'online'
            self.server_up_check.cancel()
            self.server_down_check.start()
            print('Server turn online')
            print(f"Successfully sent message to {channelsendcountsuccess} channel, {channelsendcountfail} channel failed")
            print("-"*30)
        else:              
            network_check = {}
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self.worker, 'www.google.com', network_check)
            if network_check.get('www.google.com') == 'online':
                self.offline_count += 1
                
                print(f'Server is offline {self.offline_count}')
                print("-"*30)
     
    @tasks.loop(minutes = 5)
    async def server_down_check(self):
        print(f"{get_now_HMS()}, server_down_check...")
        
        # 先檢查Bot網路狀態，避免因Bot網路問題誤判伺服器離線
        network_check = {}
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self.worker, 'www.google.com', network_check)
        
        if network_check.get('www.google.com') != 'online':
            print(f"{get_now_HMS()}, Bot network issue detected, skipping server check")
            return
        
        tasks = [self.async_worker(h) for h in HOST]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                self.ret.update(result)

        server_online = any(status == 'online' for status in self.ret.values())
        
        # 如果判定離線，進行二次確認避免誤報
        if not server_online:
            print(f"{get_now_HMS()}, First check shows offline, verifying after 10 seconds...")
            await asyncio.sleep(10)
            
            # 再次檢查網路狀態
            network_recheck = {}
            await loop.run_in_executor(self.executor, self.worker, 'www.google.com', network_recheck)
            if network_recheck.get('www.google.com') != 'online':
                print(f"{get_now_HMS()}, Bot network unstable, aborting check")
                return
            
            # 二次確認伺服器狀態
            verify_tasks = [self.async_worker(h) for h in HOST]
            verify_results = await asyncio.gather(*verify_tasks, return_exceptions=True)
            verify_ret = {}
            for result in verify_results:
                if isinstance(result, dict):
                    verify_ret.update(result)
            server_online = any(status == 'online' for status in verify_ret.values())
            
            if server_online:
                print(f"{get_now_HMS()}, Second check shows online, false alarm avoided")
        
        remove_list = []
          
        if not server_online and self.server_status != 'offline':
        # if server_online and self.server_status != 'offline':
            
            await self.bot.change_presence(activity=discord.CustomActivity(name="TMS 登入口關閉中"))
            channelsendcountsuccess = 0
            channelsendcountfail = 0
            
            Guild_Function = self.load_guild_function()
            
            for guild_id, guild_config in Guild_Function.items():
                channel_id = guild_config['ServerCheck_Channel']
                
                if not channel_id:
                    print(f"{get_now_HMS()}, Guild: {guild_id} dont have ServerCheck_Channel")
                    remove_list.append(guild_id)
                    channelsendcountfail += 1
                    continue
                
                channel = self.bot.get_channel(channel_id)                
                if channel is None:
                    print(f"{get_now_HMS()}, ChannelID: {channel_id} message not sent")
                    remove_list.append(guild_id)
                    channelsendcountfail += 1
                    continue
                
                if channel is None or not channel.permissions_for(channel.guild.me).send_messages:
                    print(f"{get_now_HMS()}, ChannelID: {channel_id} has no permission")
                    remove_list.append(guild_id)
                    channelsendcountfail += 1
                    continue
                                
                mention = guild_config.get('ServerCheck_mention')
                
                try:
                    if mention and mention != "None":
                        await channel.send(f"MapleStory 登入口已關閉。")
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} message sent successfully") 
                    else:
                        await channel.send("MapleStory 登入口已關閉。")
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} message sent successfully") 
                                  
                    channelsendcountsuccess += 1
                    await asyncio.sleep(0.02)
                    
                except Exception as e:
                        print(f"{get_now_HMS()}, ChannelID: {channel_id} error: {e}")
                        
                        # 延遲後重試一次
                        await asyncio.sleep(2)
                        try:
                            if mention and mention != "None":
                                await channel.send(f"MapleStory 登入口已關閉。")
                            else:
                                await channel.send("MapleStory 登入口已關閉。")
                            print(f"{get_now_HMS()}, ChannelID: {channel_id} retry successful")
                            channelsendcountsuccess += 1
                        except Exception as retry_error:
                            print(f"{get_now_HMS()}, ChannelID: {channel_id} retry failed: {retry_error}")
                            
                            # 重試失敗後檢查網路狀況
                            network_status = {}
                            self.worker('www.google.com', network_status)
                            
                            # 只有在網路正常但持續發送失敗時才刪除guild
                            if network_status.get('www.google.com') == 'online':
                                print(f"{get_now_HMS()}, Network is online but send failed twice, removing guild {guild_id}")
                                remove_list.append(guild_id)
                            else:
                                print(f"{get_now_HMS()}, Network issue detected, skipping guild removal for {guild_id}")
                            
                            channelsendcountfail += 1
                        continue
 
            for gid in remove_list:
                removeguild(self.db, gid)
                                       
            self.server_status = 'offline'
            self.server_up_check.start()
            self.server_down_check.cancel()
            print('Server turn offline')
            print(f"Successfully sent message to {channelsendcountsuccess} channel, {channelsendcountfail} channel failed")
            print("-"*30)
        else:
 
            print(f'Server is online')
            print("-"*30)
    
    @commands.command(name='db_backup')
    @commands.is_owner()
    async def backup_database(self, ctx):
        """備份資料庫為 JSON 格式"""
        try:
            backup_filename = f'Guild_Function_backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            backup_path = f'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\{backup_filename}'
            
            self.db.backup_to_json(backup_path)
            await ctx.send(f"✅ 資料庫已備份至: `{backup_filename}`")
            
        except Exception as e:
            await ctx.send(f"❌ 備份失敗: {e}")
    
    @commands.command(name='db_status')
    @commands.is_owner()
    async def database_status(self, ctx):
        """顯示資料庫狀態"""
        try:
            guild_list = self.db.get_guild_list()
            guild_count = len(guild_list)
            
            embed = discord.Embed(title="資料庫狀態", color=0x00ff00)
            embed.add_field(name="Guild 數量", value=str(guild_count), inline=True)
            embed.add_field(name="資料庫路徑", value=self.db.db_path, inline=False)
            
            if guild_count > 0:
                recent_guilds = guild_list[:5]  # 顯示前5個
                embed.add_field(
                    name="最近的 Guild ID", 
                    value="\n".join([f"`{gid}`" for gid in recent_guilds]), 
                    inline=False
                )
                
                if guild_count > 5:
                    embed.add_field(name="其他", value=f"... 還有 {guild_count - 5} 個", inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ 無法取得資料庫狀態: {e}")
    
    @commands.command(name='migrate_json')
    @commands.is_owner()
    async def migrate_from_json(self, ctx, json_filename: str = "Guild_Function.json"):
        """從 JSON 檔案匯入資料"""
        try:
            json_path = f'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\{json_filename}'
            success = self.db.import_from_json(json_path)
            
            if success:
                await ctx.send(f"✅ 成功從 `{json_filename}` 匯入資料！")
            else:
                await ctx.send(f"❌ 匯入失敗，請檢查檔案是否存在或格式是否正確")
                
        except Exception as e:
            await ctx.send(f"❌ 匯入過程中發生錯誤: {e}")

       