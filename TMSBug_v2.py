import os

# ⚠️ 必須在 import 任何 functions.* 之前 —— 那些 cog 會 import
# tmsapi.request，而 tmsapi.config 一被 import，API key 就定案了。
# tmsapi 的預設是管線的 key（Maplecube），Bot 在這裡指回自己的。
os.environ.setdefault(
    'TMSAPI_CONFIG',
    r'C:\Users\User\Desktop\DiscordBot\Config\TMSBug_v2_config.ini')

import datetime
import discord
from discord.ext import commands
import configparser
import asyncio
import logging


from functions.Cogs.Loop_ServerCheck import Loop_ServerCheck
from functions.Cogs.Loop_ServerAnnounce import Loop_ServerAnnounce
from functions.Cogs.Loop_StatusReport import Loop_StatusReport

from functions.cogs_registry import RELOADABLE_COGS

try:
    _TMSBot_CONF = configparser.ConfigParser()
    config_path = rf'C:\Users\User\Desktop\DiscordBot\Config\TMSBug_v2_config.ini'
    _TMSBot_CONF.read(config_path, encoding="utf-8")
except FileNotFoundError:
    print("`config.ini` file missing.")
    #sys.exit(1)

discord.voice_client.VoiceClient.warn_nacl = False


def resolve_intents() -> discord.Intents:
    "Resolves configured intents to discord format"
    intents = discord.Intents.default()
    intents.members = _TMSBot_CONF.getboolean("intents", "members", fallback=False)
    intents.presences = _TMSBot_CONF.getboolean("intents", "presences", fallback=False)
    intents.message_content = _TMSBot_CONF.getboolean("intents", "message_content", fallback=False)
    return intents

class TMSBot(commands.AutoShardedBot):

    def __init__(self, config, intents):
        allowed_mentions = discord.AllowedMentions(
            roles=True, everyone=False, users=True, replied_user=False
        )
        super().__init__(
            self_bot=True,
            command_prefix=commands.when_mentioned_or(
                config["bot"]["prefix"].strip('"')
            ),
            description=config["bot"]["description"],
            pm_help=True,
            heartbeat_timeout=150.0,
            allowed_mentions=allowed_mentions,
            intents=intents,
            activity=discord.Activity(
                type=int(config["bot"]["activity_type"]), name=config["bot"]["activity"]
            ),
        )
      
        # setup from config
        self._config = config
        self.color = discord.Color.from_str(config["bot"]["color"])
        self.name = config["bot"]["name"]
        self.session = None
        self.uptime = None
        self.time_date = ''
        self._ready_once = False  # 添加標記確保只執行一次
        
        print('-'*25)
        print('TMSBot_v2 is Loading')
        print('-'*25)

    async def setup_hook(self):
        """
        setup_hook 只會在 bot 啟動時執行一次
        適合用來載入 Cogs 和同步命令
        """
        # 全域指令錯誤處理：互動逾時(10062)不再噴 traceback
        self.tree.on_error = self.on_tree_error

        print('\n🔧 Loading Cogs...')
        
        # ── 可熱重載的 cog（extension）────────────────────────
        #
        # 這些走 load_extension 而不是 add_cog：後台就能單獨 reload 一支，
        # 改一行文案不必重啟整台 Bot（5 個 shard、近 5,000 個伺服器要重連，
        # 還會多做一次全域指令同步）。reload_extension 是原子的 ——
        # 新版載入失敗時 discord.py 會把舊版整個還原回去。
        #
        # ⚠️ Loop_* 不放這裡：它們帶 tasks.loop，而 Loop_StatusReport 正是
        # 執行 reload 的那一支，重載自己等於抽掉腳下的地板。那三支要改就重啟。
        for name in RELOADABLE_COGS:
            try:
                await self.load_extension(f'functions.Cogs.{name}')
                print(f'Cogs:{name} loaded')
            except Exception as e:
                print(f'✗ Cogs:{name} 載入失敗：{type(e).__name__}: {e}')

        await self.add_cog(Loop_ServerCheck(self))
        print('Cogs:Loop_ServerCheck loaded')
        await self.add_cog(Loop_ServerAnnounce(self))
        print('Cogs:Loop_ServerAnnounce loaded')
        await self.add_cog(Loop_StatusReport(self))
        print('Cogs:Loop_StatusReport loaded')

        # 列出所有已註冊的命令
        all_commands = self.tree.get_commands()
        print(f"\n📋 已註冊的命令 ({len(all_commands)} 個):")
        for cmd in all_commands:
            print(f"  - {cmd.name}")

        dev_guild_id = self._config["bot"]["dev_guild"]
        print('\n🔄 Syncing slash commands...')
        print(f'Dev guild: {dev_guild_id}')
        
        if dev_guild_id:
            dev_guild = discord.Object(id=int(dev_guild_id))
            self.tree.copy_global_to(guild=dev_guild)
            slash = await self.tree.sync(guild=dev_guild)
            print(f"✅ Loaded {len(slash)} slash commands to dev guild")
        else:
            slash = await self.tree.sync()
            print(f"✅ Loaded {len(slash)} slash commands globally")

        print(f"\n📊 Total Slash Commands Synced: {len(slash)}")
        for cmd in slash:
            print(f"  - {cmd.name}")

    async def on_tree_error(self, interaction: discord.Interaction, error):
        """全域斜線指令錯誤處理。

        Discord 規定互動必須在 3 秒內被回應，逾時後 token 失效 → 404 (10062)。
        這種情況多半來自 event loop 短暫阻塞或 Discord 自身的傳播延遲，
        不是程式邏輯錯誤，因此只記一行 log，不輸出整段 traceback。
        """
        cmd = interaction.command.name if interaction.command else 'unknown'
        err = getattr(error, 'original', error)

        if isinstance(err, discord.NotFound) and getattr(err, 'code', None) == 10062:
            logging.warning(f"[互動逾時] {cmd}: 使用者端未收到回應 (10062)")
            return
        if isinstance(err, discord.errors.InteractionResponded):
            logging.warning(f"[重複回應] {cmd}")
            return

        logging.exception(f"指令 {cmd} 發生未預期錯誤", exc_info=err)
        # 盡量通知使用者；互動已失效就安靜放棄
        try:
            msg = "❌ 指令執行時發生錯誤，請稍後再試。"
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass

    async def on_ready(self):
        """
        on_ready 會在每個 shard 連接時觸發
        只用來顯示狀態訊息
        """
        if not self._ready_once:
            self._ready_once = True
            print('\n' + '-'*25)
            print('TMSBot_v2 is Online')
            print(f'Bot: {self.user.name}#{self.user.discriminator}')
            print(f'Bot ID: {self.user.id}')
            print(f'Guilds: {len(self.guilds)}')
            print(f'Shards: {self.shard_count}')
            print('-'*25)
        else:
            print(f'Shard {self.shard_id} is ready')

    async def on_guild_join(self, guild):
        
        print(f'Joined new guild: {guild.name} (id: {guild.id})')
        print(f'Currently in {len(self.guilds)} guilds')
        print('-'*25)


async def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tmsbot = TMSBot(config=_TMSBot_CONF, intents=resolve_intents())

    await tmsbot.start(_TMSBot_CONF["discord"]["token"], reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())