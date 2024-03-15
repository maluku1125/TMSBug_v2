import datetime
import discord
from discord.ext import commands
import configparser
import asyncio

from functions.CreateBossDataEmbed import Create_Boss_Data_Embed, boss_aliases
from functions.tinyfunctions import probably
from functions.CreateMemoEmbed import CreateFarmingEmbed, CreateCombatEmbed
from functions.Cogs.Discord_Commands import DiscordCommands
from functions.Cogs.SlashCommands import SlashCommands

try:
    _TMSBot_CONF = configparser.ConfigParser()
    config_path = 'C:\\Users\\User\\Desktop\\DiscordBot\\Config\\TMSBug_v2_config.ini'
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
        
        print('-'*25)
        print('TMSBot_v2 is Loading')
        print('-'*25)

    async def on_ready(self):       
        
        await self.add_cog(DiscordCommands(self))
        print('Cogs:DiscordCommands loaded')
        await self.add_cog(SlashCommands(self))
        print('Cogs:SlashCommands loaded')


        dev_guild_id = self._config["bot"]["dev_guild"]
        print('slash command is now loading')
        print(f'devguild : {dev_guild_id}')
        
        if dev_guild_id:
            dev_guild = self.get_guild(int(dev_guild_id))
            self.tree.copy_global_to(guild=dev_guild)
            slash = await self.tree.sync(guild=dev_guild)
            print(f"Loaded slash command to dev guild")
        else:
            slash = await self.tree.sync()
            print(f"Loaded slash command to global guild")

        print(f"Total Slash Command Loaded:{len(slash)}")

        print('-'*25)
        print('TMSBot_v2 is Online')
        print('-'*25)


    async def on_message(self, message, /):
                
        if datetime.datetime.now().strftime('%m%d') != self.time_date:
            self.time_date = datetime.datetime.now().strftime('%m%d')
            self.speak_count = 0
        
        # 略自己
        if message.author == self.user:
            return
        
        now_HMS = datetime.datetime.now().strftime('%H:%M:%S')
        
        # 略 TMS server
        if message.guild.id == int(self._config["function"]["tmsguildid"]):
            return

        #await self.process_commands(message)

async def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tmsbot = TMSBot(config=_TMSBot_CONF, intents=resolve_intents())

    await tmsbot.start(_TMSBot_CONF["discord"]["token"], reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())