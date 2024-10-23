import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
from functions.tinyfunctions import probably

from functions.SlashCommandManager import UseSlashCommand 

class Slash_CalculateScrolls(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
    #-----------------BOSS-----------------
    @app_commands.command(name="scrolls卷軸模擬器", description="BOSS資料")
    @app_commands.describe(equiptype = "裝備類型", equipscrollscount = "裝備卷數", purplevalue = "紫字數值")
    @app_commands.choices(
        equiptype = [
            Choice(name = "武器卷", value = "weapon"),
            Choice(name = "防具卷", value = "armor"),
            Choice(name = "飾品卷", value = "accessories")
        ]
    )
    
    async def calculatescrolls(self, interaction: discord.Interaction, equiptype: str, equipscrollscount:int, purplevalue: int):
        
        if equiptype == "weapon":
            equipname = "武器/心臟"
        elif equiptype == "armor":
            equipname = "防具"
        elif equiptype == "accessories":
            equipname = "飾品"
            
        
        avgvalue = float(purplevalue) / float(equipscrollscount)
        if equiptype == "weapon":
            if avgvalue == 3:
                ScrollType = "咒文100%"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            elif avgvalue < 3:
                ScrollType = "或許混沌或某種低攻卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            elif avgvalue == 5:
                ScrollType = "咒文70%"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            elif avgvalue == 7:
                ScrollType = "咒文30%"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            elif avgvalue == 9:
                ScrollType = "咒文15%"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            elif 10 > avgvalue > 9:
                ScrollType = "咒文15% + 混衝"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            elif avgvalue == 10:
                ScrollType = "RED卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252068416422051.webp?size=96&quality=lossless'
            elif 12 > avgvalue > 10:
                ScrollType = "混衝(RED卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252068416422051.webp?size=96&quality=lossless'
            elif avgvalue == 12:
                ScrollType = "X卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252072321318983.webp?size=96&quality=lossless'
            elif 13 > avgvalue > 12:
                ScrollType = "混衝(X卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252072321318983.webp?size=96&quality=lossless'
            elif avgvalue == 13:
                ScrollType = "V卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252070429687909.webp?size=96&quality=lossless'
            elif 14 > avgvalue > 13:
                ScrollType = "混衝(V卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252070429687909.webp?size=96&quality=lossless'
            elif avgvalue == 14:
                ScrollType = "B卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252074540240916.webp?size=96&quality=lossless'
            elif 17 >= avgvalue > 14:
                ScrollType = "榮耀/命運/救世"
                emojilink = 'https://cdn.discordapp.com/emojis/1293260931471638632.webp?size=96&quality=lossless'
            elif 20 >= avgvalue > 17:
                ScrollType = "榮耀/命運/救世"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252079086993408.webp?size=96&quality=lossless'    
            elif avgvalue > 20:
                ScrollType = "您超越了"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
        else:
            if avgvalue < 4:
                ScrollType = "咒文或混沌卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252066160017520.webp?size=96&quality=lossless'
            elif avgvalue == 4:
                ScrollType = "極電卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252080781492296.webp?size=96&quality=lossless'
            elif 5 > avgvalue > 4:
                ScrollType = "混衝(極電卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252080781492296.webp?size=96&quality=lossless'
            elif avgvalue == 5:
                ScrollType = "RED卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252068416422051.webp?size=96&quality=lossless'
            elif 7 > avgvalue > 5:
                ScrollType = "混衝(RED卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252068416422051.webp?size=96&quality=lossless'
            elif avgvalue == 7:
                ScrollType = "X卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252072321318983.webp?size=96&quality=lossless'
            elif 8 > avgvalue > 7:
                ScrollType = "混衝(X卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252072321318983.webp?size=96&quality=lossless'
            elif avgvalue == 8:
                ScrollType = "V卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252070429687909.webp?size=96&quality=lossless'
            elif 9 > avgvalue > 8:
                ScrollType = "混衝(V卷+)"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252070429687909.webp?size=96&quality=lossless'
            elif avgvalue == 9:
                ScrollType = "B卷"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252074540240916.webp?size=96&quality=lossless'
            elif 12 >= avgvalue > 9:
                ScrollType = "榮耀/命運/救世"
                emojilink = 'https://cdn.discordapp.com/emojis/1293260931471638632.webp?size=96&quality=lossless'
            elif 15 >= avgvalue > 12:
                ScrollType = "榮耀/命運/救世"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252079086993408.webp?size=96&quality=lossless'    
            elif avgvalue > 15:
                ScrollType = "您超越了"
                emojilink = 'https://cdn.discordapp.com/emojis/1293252076180078713.webp?size=96&quality=lossless'
            
        
        
        embed = discord.Embed(
            title="卷軸模擬器", color=0x00ff00
            )
        
        if probably(0.01):
            if ScrollType == "您超越了":
                ScrollType = "蟲蟲的祝福卷"
                embed.set_footer(text=f'*別跟人說有這張卷*')
                
        embed.add_field(
            name="模擬結果",
            value=(
                "```autohotkey\n"
                f"裝備類型 : {equipname}(+{equipscrollscount})\n"
                f"卷軸類型 : {ScrollType}\n"    
                f"均攻　　 : {round(avgvalue,2)}(+{purplevalue})\n```"          
            ),
            inline=True,
        )
        
        embed.set_thumbnail(url=emojilink)
        
        UseSlashCommand('scrollsimulator', interaction)
        
        await interaction.response.send_message(embed=embed)