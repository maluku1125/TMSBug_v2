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

        await self.process_commands(message)

        # 略 TMS server
        if message.guild.id == int(self._config["function"]["tmsguildid"]):
            return

        #MEMO資訊
        if message.content == '練等備忘' or message.content == '鍊等備忘':
            embed = CreateFarmingEmbed()
            sent_message = await message.channel.send(embed=embed)
            print(f'{now_HMS}, Guild：{message.channel.guild}, User：{message.author} ,FarmingMemo')
            print('-'*40)

        if message.content == '打王備忘' or message.content == 'BOSS備忘' or message.content == 'Boss備忘' or message.content == 'boss備忘':
            embed = CreateCombatEmbed()
            sent_message = await message.channel.send(embed=embed)
            print(f'{now_HMS}, Guild：{message.channel.guild}, User：{message.author} ,CombatMemo')
            print('-'*40)

        #BOSS資訊    
        #----------------------------------------        
        if message.content in boss_aliases:    

            if message.content == '蟲蟲':
                await message.channel.send(f'叫我嗎?')
            else:
                await message.add_reaction('<:img17:588950160399269889>')
                embed, num_subtitles= Create_Boss_Data_Embed(message.content, 0)
                if probably(0.02):
                    embed, num_subtitles= Create_Boss_Data_Embed("蟲蟲", 0)  
                sent_message = await message.channel.send(embed=embed)
                await sent_message.add_reaction('🔄')
                await sent_message.add_reaction('❌')

            Bossmode = [0]   # 將 Bossmode 定義為全域變數

            @self.event
            async def on_reaction_add(reaction, user):
                if user == self.user:
                    return  # 忽略機器人自身的反應

                if reaction.message.author != self.user:
                    return  # 忽略機器人所發送訊息以外的反應

                if reaction.message.id != sent_message.id:
                    return  # 忽略其他訊息的反應

                if reaction.emoji == '🔄':
                    await reaction.remove(user)  # 刪除使用者加上的反應                
                    await asyncio.wait_for(switch_boss_mode(), timeout=10)  # 等待使用者反應，設定超時時間為 10 秒    
                if reaction.emoji == '❌':
                    await sent_message.delete()
                                

            async def switch_boss_mode():
                Bossmode[0] = (Bossmode[0] + 1) % num_subtitles

                embed, _ = Create_Boss_Data_Embed(message.content, Bossmode[0])    
                await sent_message.edit(embed=embed)

async def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tmsbot = TMSBot(config=_TMSBot_CONF, intents=resolve_intents())

    await tmsbot.start(_TMSBot_CONF["discord"]["token"], reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())