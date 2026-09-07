import socket
import time
from discord.ext import commands, tasks
import discord
import json
import datetime
import asyncio
from functions.database_manager import GuildFunctionDB
from functions.ConcurrentBroadcast import broadcast_to_channels
from concurrent.futures import ThreadPoolExecutor

# 關機判定需要連續幾輪都離線（server_down_check 每 5 分鐘一輪）。
# 開機判定維持「任一台通就算開」—— 那個方向本來就不容易誤判。
DOWN_ROUNDS = 3

# 初判離線後，要連續觀察幾秒、每隔幾秒探測一次。全程都不通才算離線。
OFFLINE_SUSTAIN = 60
OFFLINE_PROBE_INTERVAL = 10

# 本機對外連線壅塞的門檻。實測無負載時 SYN_SENT=0、TIME_WAIT≈73；
# 管線滿載時 SYN_SENT=63、TIME_WAIT≈1,972。
SYN_SENT_LIMIT = 10
TIME_WAIT_LIMIT = 800

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

def outbound_pressure():
    """本機對外連線的壅塞程度，回 (SYN_SENT 數, TIME_WAIT 數)。

    ⚠️ 這是 2026-09-06 誤報事故的根因偵測。

    當管線在跑大量 API 請求時（每秒上百條新連線），中間路徑的連線狀態表
    （HiNet 的 NAT／防火牆）會被撐滿，**新連線的 SYN 直接被丟棄**。
    已建立的連線不受影響 —— 所以 `www.google.com` 那道防線測起來正常，
    但遊戲伺服器每次都是冷連線，剛好是最脆弱的那種。

    實測：
        無管線負載   SYN_SENT   0   TIME_WAIT    73   6 台全通（7-8ms）
        有管線負載   SYN_SENT  63   TIME_WAIT 1,972   6 台輪流逾時
        停掉負載 45 秒後                              6 台全通

    外部監測服務同時段顯示登入伺服器一路正常 146ms —— 是我們這端的問題。
    """
    try:
        import psutil
        conns = psutil.net_connections(kind='tcp')
        ext = [c for c in conns
               if c.raddr and not str(c.raddr.ip).startswith(('127.', '::1'))]
        syn = sum(1 for c in ext if c.status == 'SYN_SENT')
        tw = sum(1 for c in conns if c.status == 'TIME_WAIT')
        return syn, tw
    except Exception:
        return 0, 0          # 量不到就不擋，維持原行為


def outbound_congested():
    syn, tw = outbound_pressure()
    return (syn >= SYN_SENT_LIMIT or tw >= TIME_WAIT_LIMIT), syn, tw


class Loop_ServerCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 每輪的探測結果。三個迴圈共用這個名字，但都會在 update 前重設 ——
        # 不重設的話，任務拋例外沒更新的那一格會留著上一輪的值。
        self.ret = {}
        self.server_status = ''
        self.offline_count = 0
        # 關機判定要連續 DOWN_ROUNDS 輪都離線才成立（每輪間隔 5 分鐘）。
        # 關機通知不講求速度，寧可晚十幾分鐘也不要誤報。
        self.down_rounds = 0
        # 以下純粹是給後台監看用的觀測值（Loop_StatusReport 會讀走）。
        # 不參與任何判定 —— 加欄位不該改變通知行為。
        self.last_check_at = None      # 這輪探測的時間
        self.last_verdict = None       # 這輪的原始結論：online / offline / unreliable
        self.last_congested = False    # 本機出口是否壅塞（壅塞時結論不採信）
        self.last_pressure = None      # (SYN_SENT, TIME_WAIT)
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
        # 5 秒。2026-09-06 觀察到本機連線建立被拖慢時（外部 API 節流造成
        # 63 條連線卡在 SYN_SENT、新連線要 15 秒），3 秒很容易讓 6 台全部誤判離線。
        # 遊戲伺服器是冷連線，比 www.google.com 那種熱門目標更容易受影響。
        s.settimeout(5)
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
    
    async def sustained_offline(self):
        """在 OFFLINE_SUSTAIN 秒內反覆探測，**任何一次任何一台通就否決**。

        原本只是「隔 10 秒再測一次」，擋得住瞬間閃斷，擋不住持續數十秒的
        連線劣化。改成整整一分鐘的連續觀察。
        """
        deadline = time.time() + OFFLINE_SUSTAIN
        rounds = 0
        while True:
            results = await asyncio.gather(
                *[self.async_worker(h) for h in HOST], return_exceptions=True)
            ret = {}
            for r in results:
                if isinstance(r, dict):
                    ret.update(r)
            rounds += 1
            if any(v == 'online' for v in ret.values()):
                print(f"{get_now_HMS()}, 第 {rounds} 次探測有伺服器回應，"
                      f"取消離線判定")
                return False, rounds
            if time.time() >= deadline:
                return True, rounds
            await asyncio.sleep(OFFLINE_PROBE_INTERVAL)

    def load_guild_function(self):
        """從資料庫載入所有 Guild 設定"""
        return self.db.get_all_guild_configs()  

    @tasks.loop(minutes = 1)
    async def check_server_status(self):
        print("check_server_status...")
        tasks = [self.async_worker(h) for h in HOST]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 每輪用新的 dict。self.ret 是實例屬性且從不重設，某台的任務拋例外時
        # 那一格會留著**上一輪的值** —— 舊的 'online' 會讓 any() 為 True，
        # 真的全掛時反而不通知。
        self.ret = {}
        for result in results:
            if isinstance(result, dict):
                self.ret.update(result)

        # 後台監看用：這輪的原始觀測（尚未經過壅塞判斷與連續輪數）
        self.last_check_at = datetime.datetime.now()
        self.last_verdict = ('online'
                             if any(v == 'online' for v in self.ret.values())
                             else 'offline')
        
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
        
        # 每輪用新的 dict。self.ret 是實例屬性且從不重設，某台的任務拋例外時
        # 那一格會留著**上一輪的值** —— 舊的 'online' 會讓 any() 為 True，
        # 真的全掛時反而不通知。
        self.ret = {}
        for result in results:
            if isinstance(result, dict):
                self.ret.update(result)

        # 後台監看用：這輪的原始觀測（尚未經過壅塞判斷與連續輪數）
        self.last_check_at = datetime.datetime.now()
        self.last_verdict = ('online'
                             if any(v == 'online' for v in self.ret.values())
                             else 'offline')

        server_online = any(status == 'online' for status in self.ret.values())
 
        if server_online and self.server_status != 'online':

            await self.bot.change_presence(activity=discord.Game(name="MapleStory"))

            # 預先初始化計數，避免 offline_count < 30 時未定義（舊版 NameError）
            channelsendcountsuccess = 0
            channelsendcountfail = 0

            if self.offline_count >= 30:
                # 發送通知前先確認Bot網路狀態正常
                network_check = {}
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self.worker, 'www.google.com', network_check)

                if network_check.get('www.google.com') != 'online':
                    print(f"{get_now_HMS()}, Bot network issue detected, skipping notifications")
                    # 不重置offline_count，等下次網路正常時再發送
                    return
                
                Guild_Function = self.load_guild_function()
                remove_list = []
                targets = []

                for guild_id, guild_config in Guild_Function.items():
                    channel_id = guild_config['ServerCheck_Channel']
                    if not channel_id:
                        print(f"{get_now_HMS()}, Guild: {guild_id} dont have ServerCheck_Channel")
                        remove_list.append(guild_id)
                        continue
                    targets.append((guild_id, channel_id))

                def make_payload(guild_id, channel_id):
                    mention = Guild_Function[guild_id].get('ServerCheck_mention')
                    if mention and mention != "None":
                        return {'content': f"<@&{mention}> 登入口已開啟。"}
                    return {'content': "登入口已開啟。"}

                # 並發廣播（含每頻道一次重試）
                channelsendcountsuccess, failures = await broadcast_to_channels(
                    self.bot, targets, make_payload, concurrency=20
                )
                channelsendcountfail = len(failures) + len(remove_list)

                # 只有在 Bot 網路正常時，才將發送失敗的 guild 移除
                if failures:
                    network_status = {}
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self.executor, self.worker, 'www.google.com', network_status)
                    if network_status.get('www.google.com') == 'online':
                        remove_list += [guild_id for guild_id, _, _ in failures]
                    else:
                        print(f"{get_now_HMS()}, Network issue detected, skipping guild removal")

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
        
        # 每輪用新的 dict。self.ret 是實例屬性且從不重設，某台的任務拋例外時
        # 那一格會留著**上一輪的值** —— 舊的 'online' 會讓 any() 為 True，
        # 真的全掛時反而不通知。
        self.ret = {}
        for result in results:
            if isinstance(result, dict):
                self.ret.update(result)

        # 後台監看用：這輪的原始觀測（尚未經過壅塞判斷與連續輪數）
        self.last_check_at = datetime.datetime.now()
        self.last_verdict = ('online'
                             if any(v == 'online' for v in self.ret.values())
                             else 'offline')

        server_online = any(status == 'online' for status in self.ret.values())
        
        # 初判離線 → 連續觀察 OFFLINE_SUSTAIN 秒，全程都不通才算本輪離線
        congested_before, syn0, tw0 = outbound_congested()
        congested_after = False
        if not server_online:
            print(f"{get_now_HMS()}, 初判離線，開始連續 {OFFLINE_SUSTAIN} 秒觀察…")
            still_off, probes = await self.sustained_offline()

            # 觀察期間本機也可能出問題，結束後再確認一次
            network_recheck = {}
            await loop.run_in_executor(self.executor, self.worker,
                                       'www.google.com', network_recheck)
            if network_recheck.get('www.google.com') != 'online':
                print(f"{get_now_HMS()}, Bot network unstable, aborting check")
                self.down_rounds = 0
                return
            congested_after, syn1, tw1 = outbound_congested()

            server_online = not still_off
            if server_online:
                print(f"{get_now_HMS()}, 觀察期內有回應（共 {probes} 次探測），"
                      f"誤報已避免")
            else:
                print(f"{get_now_HMS()}, 連續 {OFFLINE_SUSTAIN} 秒 "
                      f"{probes} 次探測全部失敗")

        # ⚠️ 本機出口壅塞時「照測但不發」。
        #
        # 2026-09-06：管線跑大量 API 請求期間，6 台登入伺服器輪流逾時，
        # 而外部監測顯示它們一路正常 146ms —— 是我們這端的冷連線被拖垮。
        # 停掉管線靜置 45 秒後，6 台立刻全通（7-8ms）。
        #
        # 所以壅塞期間的探測結果**不可信**，但仍然照測、照記錄（log 看得到
        # 實際狀況），只是不送通知；並把連續計數歸零，
        # 等負載結束後重新累積 DOWN_ROUNDS 輪可信的判定才發送。
        self.last_congested = bool(congested_before or congested_after)
        self.last_pressure = (syn0, tw0)
        if congested_before or congested_after:
            self.last_verdict = 'unreliable'
            state = "離線" if not server_online else "線上"
            print(f"{get_now_HMS()}, 本機對外連線壅塞"
                  f"（SYN_SENT={syn0} TIME_WAIT={tw0}）—— "
                  f"本輪探測結果為「{state}」但不予採信，連續計數歸零")
            self.down_rounds = 0
            return

        # 本輪的結論確定後，累計／重置連續離線輪數
        if server_online:
            if self.down_rounds:
                print(f"{get_now_HMS()}, 伺服器回應正常，連續離線計數歸零"
                      f"（原本 {self.down_rounds}/{DOWN_ROUNDS}）")
            self.down_rounds = 0
        else:
            self.down_rounds += 1
            print(f"{get_now_HMS()}, 判定離線 {self.down_rounds}/{DOWN_ROUNDS} 輪")
            if self.down_rounds < DOWN_ROUNDS:
                print(f"{get_now_HMS()}, 尚未達連續 {DOWN_ROUNDS} 輪，先不通知")
                return

        remove_list = []
          
        if not server_online and self.server_status != 'offline':
        # if server_online and self.server_status != 'offline':
            
            await self.bot.change_presence(activity=discord.CustomActivity(name="TMS 登入口關閉中"))

            Guild_Function = self.load_guild_function()
            targets = []

            for guild_id, guild_config in Guild_Function.items():
                channel_id = guild_config['ServerCheck_Channel']
                if not channel_id:
                    print(f"{get_now_HMS()}, Guild: {guild_id} dont have ServerCheck_Channel")
                    remove_list.append(guild_id)
                    continue
                targets.append((guild_id, channel_id))

            # 並發廣播（含每頻道一次重試）
            channelsendcountsuccess, failures = await broadcast_to_channels(
                self.bot, targets, lambda g, c: {'content': "MapleStory 登入口已關閉。"}, concurrency=20
            )
            channelsendcountfail = len(failures) + len(remove_list)

            # 只有在 Bot 網路正常時，才將發送失敗的 guild 移除
            if failures:
                network_status = {}
                await loop.run_in_executor(self.executor, self.worker, 'www.google.com', network_status)
                if network_status.get('www.google.com') == 'online':
                    remove_list += [guild_id for guild_id, _, _ in failures]
                else:
                    print(f"{get_now_HMS()}, Network issue detected, skipping guild removal")

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

       