# original source code from 析唄
import datetime 

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Get official site events 
# API_BULLETIN = "https://maplestory.beanfun.com/api/GamaAd/FindAdData?AdType=MainBulletin&_=1712640985888"
# int(time()*1000) in the back for no reason
API_BULLETIN = "https://maplestory.beanfun.com/api/GamaAd/FindAdData?AdType=MainBulletin&_=" 
# Resp	{"ListData", "Data", "Code", "Message", "Url"}

def get_now_HMS():
    return datetime.datetime.now().strftime('%H:%M:%S')

def PrintSlash(type, interaction: discord.Interaction):
    print(f'{get_now_HMS()}, Guild：{interaction.guild}, User：{interaction.user} ,Slash：{type}')
    print('-'*40)

class EventsDropdown(discord.ui.Select):
    def __init__(self, embedlist):
        options = []
        for num, embed in enumerate(embedlist):
            options.append(discord.SelectOption(value=str(num), label=embed.title))
        self.embedlist = embedlist

        super().__init__(placeholder=embedlist[0].title, min_values=1, max_values=1, options=options)

    async def callback(self, interaction):
        await interaction.response.edit_message(embed=self.embedlist[int(self.values[0])])


class EventsView(discord.ui.View):
    def __init__(self, embedlist):
        super().__init__()
        self.add_item(EventsDropdown(embedlist))


class Slash_RequestMapleEvents(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.bulletin_cache = {}
        self.bulletin_update_ts = 0
        self.bulletin_code: int = 0

    @app_commands.command(name="events當前活動", description="查看官網活動訊息")
    async def events(self, interaction: discord.Interaction):
        PrintSlash('events', interaction)
        await interaction.response.defer()
        if datetime.datetime.now().timestamp() > self.bulletin_update_ts + 1800.0 or self.bulletin_code != 1:
            # Refresh API is outdate or fail            
            async with aiohttp.ClientSession() as session:
                async with session.get(API_BULLETIN + str(int(datetime.datetime.now().timestamp() * 1000))) as response:
                    if response.status == 200:
                        json = await response.json()
                        self.bulletin_code = 1
                        self.bulletin_cache = json['listData']
                        self.bulletin_update_ts = datetime.datetime.now().timestamp()
              
        embeds = self.CreateMapleEventsEmbeds()
        
        events_view = EventsView(embeds)
        await interaction.edit_original_response(embed=embeds[0], view=events_view)

    def CreateMapleEventsEmbeds(self):
        embeds = []
        for data in self.bulletin_cache:
            
            embed = discord.Embed(                
                title = data["adName"],
                url = data["adUrl"],
                description = f""
            )
            embed.set_image(url=data["adImage"])
            start_dt = datetime.datetime.strptime(data["adsTime"], "%Y-%m-%dT%H:%M:%S")
            end_dt = datetime.datetime.strptime(data["adeTime"], "%Y-%m-%dT%H:%M:%S")
            if isinstance(start_dt, datetime.datetime) and isinstance(end_dt, datetime.datetime):
                text = f"{start_dt.strftime('%Y年%m月%d日 %H點%M分')} ~ {end_dt.strftime('%Y年%m月%d日 %H點%M分')}"
            else:
                text = "未知"
            embed.add_field(
                name="活動期限:",
                value=f"{text}"
            )
            embed.set_footer(text=f"資料更新時間: {datetime.datetime.fromtimestamp(self.bulletin_update_ts).strftime('%Y/%m/%d %H:%M:%S')}")
            embeds.append(embed)
        return embeds