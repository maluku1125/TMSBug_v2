import datetime
import discord
from discord.ext import commands
import configparser
import asyncio


from functions.Cogs.Slash_BasicCommands import Slash_BasicCommands
from functions.Cogs.Slash_RequestUnionRank import Slash_RequestUnionRank
from functions.Cogs.Slash_CreateBossDataEmbed import Slash_CreateBossDataEmbed
from functions.Cogs.Slash_CreatePrizeEmbed import Slash_CreatePrizeEmbed
from functions.Cogs.Slash_CreateSolErdaFragmentEmbed import Slash_CreateSolErdaFragmentEmbed
from functions.Cogs.Slash_RequestMapleEvents import Slash_RequestMapleEvents
from functions.Cogs.Slash_Formulas import Slash_Formulas
from functions.Cogs.Slash_CalculateScrolls import Slash_CalculateScrolls
from functions.Cogs.Slash_Cubes import Slash_Cubes

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
        
        await self.add_cog(Slash_BasicCommands(self))
        print('Cogs:Slash_BasicCommands loaded')
        await self.add_cog(Slash_RequestUnionRank(self))
        print('Cogs:Slash_RequestUnionRank loaded')
        await self.add_cog(Slash_CreateBossDataEmbed(self))
        print('Cogs:Slash_CreateBossDataEmbed loaded')
        await self.add_cog(Slash_CreatePrizeEmbed(self))
        print('Cogs:Slash_CreatePrizeEmbed loaded')
        await self.add_cog(Slash_CreateSolErdaFragmentEmbed(self))
        print('Cogs:Slash_CreateSolErdaFragmentEmbed loaded')
        await self.add_cog(Slash_RequestMapleEvents(self))
        print('Cogs:Slash_RequestMapleEvents loaded')
        await self.add_cog(Slash_Formulas(self))
        print('Cogs:Slash_Formulas loaded')
        await self.add_cog(Slash_CalculateScrolls(self))
        print('Cogs:Slash_CalculateScrolls loaded')
        await self.add_cog(Slash_Cubes(self))
        print('Cogs:Slash_Cubes loaded')

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