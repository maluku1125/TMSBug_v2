import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
import json

from functions.GetPrize import use_apple, use_fashionbox, use_apple_FrenzyTotem, Create_FashionBox_embed, Create_Apple_embed
from functions.SlashCommandManager import UseSlashCommand

with open(rf'C:\Users\User\Desktop\DiscordBot\TMSBug_v2\Data\PirzeWebSite.json', 'r', encoding='utf-8') as prizewebsitefile:
    prizewebsite = json.load(prizewebsitefile)

class Slash_CreatePrizeEmbed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #-----------------抽獎-----------------
    @app_commands.describe(type = "類別")
    @app_commands.choices(
        type = [
            Choice(name = "蘋果", value = "GoldApple"),
            Choice(name = "時尚", value = "FashionBox"),
            Choice(name = "輪迴", value = "FrenzyTotem"),
            Choice(name = "伴侶", value = "boyngirl"),
            ]
    )
    @app_commands.command(name="getprize抽", description="抽獎")
    async def getprize(self, interaction: discord.Interaction, type: str):
        if type == "GoldApple":
            Message = use_apple(interaction.user.mention)
        elif type == "FashionBox":
            Message = use_fashionbox(interaction.user.mention)
        elif type == "FrenzyTotem":
            Message = use_apple_FrenzyTotem(interaction.user.mention)
        elif type == "boyngirl":
            Message = "抽不到"

        
        UseSlashCommand('getprize', interaction)
        await interaction.response.send_message(content=f"{Message}")

    #-----------------當期抽獎機率-----------------
    @app_commands.command(name="prize當期抽獎機率", description="當期抽獎機率")
   
    async def getprizechance(self, interaction: discord.Interaction):
        embed = Create_PrizeWebSite_embed()
        print(embed.to_dict())
        UseSlashCommand('getprizechance', interaction)
        await interaction.response.send_message(embed=embed)

def Create_PrizeWebSite_embed():

    embed = discord.Embed(
        title="**新楓之谷**",
        description="[機率型道具說明](https://maplestory-event.beanfun.com/eventad/eventad?eventadid=5325)",
        color=0xfbe222
    )

    # 新增三大類別的資料 - 分批處理避免字數限制
    for category, items in prizewebsite.items():
        field_value = ""
        item_count = 0
        part_number = 1
        
        for item_name, item_id in items.items():
            url = f"https://maplestory-event.beanfun.com/eventad/eventad?eventadid={item_id}"
            new_line = f"[{item_name}]({url})\n"
            
            # 檢查是否會超過字數限制
            if len(field_value + new_line) > 1800 or item_count >= 12:
                field_name = f"**{category}**" if part_number == 1 else f"**{category} ({part_number})**"
                embed.add_field(name=field_name, value=field_value, inline=True)
                field_value = new_line
                item_count = 1
                part_number += 1
            else:
                field_value += new_line
                item_count += 1
        
        if field_value:
            field_name = f"**{category}**" if part_number == 1 else f"**{category} ({part_number})**"
            embed.add_field(name=field_name, value=field_value, inline=True)
        

    print("Create_PrizeWebSite_embed completed.")

    return embed