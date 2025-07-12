import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
import random
from discord.utils import escape_mentions

from functions.SlashCommandManager import UseSlashCommand 
from functions.tinyfunctions import probably

Starforcetable = {
    0: (0.95, 0.00, 0.05, 435000),
    1: (0.90, 0.00, 0.10, 869100),
    2: (0.85, 0.00, 0.15, 1303100),
    3: (0.85, 0.00, 0.15, 1737100),
    4: (0.80, 0.00, 0.20, 2171100),
    5: (0.75, 0.00, 0.25, 2605200),
    6: (0.70, 0.00, 0.30, 3039200),
    7: (0.65, 0.00, 0.35, 3473200),
    8: (0.60, 0.00, 0.40, 3907300),
    9: (0.55, 0.00, 0.45, 4341300),
    10: (0.50, 0.00, 0.50, 17740600),
    11: (0.45, 0.00, 0.55, 40802800),
    12: (0.40, 0.00, 0.60, 74312000), 
    13: (0.35, 0.00, 0.65, 123728500),
    14: (0.30, 0.00, 0.70, 218718100),
    15: (0.30, 0.021, 0.679, 222861900),
    16: (0.30, 0.021, 0.679, 273434000),
    17: (0.15, 0.068, 0.782, 348068200),
    18: (0.12, 0.085, 0.798, 984561100),
    19: (0.10, 0.090, 0.810, 1696211500),
    20: (0.30, 0.105, 0.595, 387009800),
    21: (0.20, 0.115, 0.685, 438804400),
    22: (0.175, 0.1225, 0.7025, 494760300),
    23: (0.085, 0.180, 0.735, 555008800),
    24: (0.085, 0.180, 0.735, 619680000),
    25: (0.080, 0.180, 0.740, 688902000),
    26: (0.070, 0.186, 0.744, 762801400),
    27: (0.050, 0.190, 0.760, 841503600),
    28: (0.030, 0.194, 0.776, 925132300),
    29: (0.010, 0.198, 0.792, 1013810000),
}
    
class Slash_StarForce(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
    @app_commands.command(name="starforce衝星", description="衝星")
    @app_commands.describe(target = "目標裝備", startlevel = "起始等級")
    async def starforcesimulator(self, interaction: discord.Interaction, target: str, startlevel: int=0 ):
        
               
        embed, view = roll_starforce(target, startlevel)
                
        UseSlashCommand('Starforcesimulator', interaction)
        
        await interaction.response.send_message(embed=embed, view=view)
        

def make_starforce_msg(nowstarlevel: int) -> str:
    total = 30
    per_row = 15
    per_group = 5

    yellow = "⭐"
    white = ""

    stars = yellow * nowstarlevel + white * (total - nowstarlevel)
    # 分成兩排
    row1 = stars[:per_row]
    row2 = stars[per_row:]

    # 每5顆加一個空格
    def group_row(row):
        return "　".join([row[i:i+per_group] for i in range(0, len(row), per_group)])

    return f"{group_row(row1)}\n{group_row(row2)}"        
        
def roll_starforce(target, nowstarlevel=1):
    
    starforcemsg = make_starforce_msg(nowstarlevel)
    upgradecount = 0
    totalmesos = 0
    destroycount = 0
    failcount = 0
    
    success, destroy, fail, price = Starforcetable[nowstarlevel]
    
    embed = discord.Embed(
        title="衝星模擬器", 
        description=f"{starforcemsg}\n**__{target}__**",
        color=0xffd306
        )      
    embed.add_field(
        name=f"{nowstarlevel}星 > {nowstarlevel+1}星",
        value=f"成功機率：{success*100:.2f}%\n維持機率：{fail*100:.2f}%\n破壞機率：{destroy*100:.2f}%\n消耗楓幣：{price:,}",
        inline=False,
    )
    embed.add_field(
        name=f"累計",
        value=f"累計次數：{upgradecount}\n累計花費：{totalmesos}楓幣",
        inline=False,
    )
      
    button = Button(label="強化", style=discord.ButtonStyle.green)
    
    async def button_callback(interaction: discord.Interaction):
        
        nonlocal nowstarlevel, upgradecount, totalmesos, starforcemsg, destroycount, failcount
        before_starlevel = nowstarlevel
        nowstarlevel, price, situation = enhance(nowstarlevel)
        upgradecount += 1
        totalmesos += price
        starforcemsg = make_starforce_msg(nowstarlevel)
        
        if situation == "success":
            situationmsg = "強化成功！"
        elif situation == "fail":
            situationmsg = "強化失敗，裝備等級不變。"
            failcount += 1
        elif situation == "destroy":
            situationmsg = "強化失敗，裝備破壞！"
            destroycount += 1
            
        success, destroy, fail, price = Starforcetable[nowstarlevel]

        embed = discord.Embed(
            title="衝星模擬器", 
            description=f"{starforcemsg}\n**__{target}__**",
            color=0xffd306
            ) 
        embed.add_field(
            name=f"{nowstarlevel}星 > {nowstarlevel+1}星",
            value=f"成功機率：{success*100:.1f}%\n維持機率：{fail*100:.1f}%\n破壞機率：{destroy*100:.1f}%\n消耗楓幣：{price:,}",
            inline=False,
        )
        embed.add_field(
            name=f"**__{situationmsg}__**",
            value=f"累計次數：{upgradecount}\n破壞次數：{destroycount}\n累計花費：{totalmesos:,}楓幣",
            inline=False,
        )

        embed.set_footer(text=f"強化人：{interaction.user.display_name}")
        
       
        await interaction.response.edit_message(embed=embed, view=view) 
        
        safe_target = escape_mentions(str(target))
        
        if nowstarlevel >= 26 and situation == "success":
            await interaction.followup.send(f"{interaction.user.mention}將 __{safe_target}__ 提升至了{nowstarlevel}星", ephemeral=False)
            
        if before_starlevel >= 26 and situation == "destroy":
            await interaction.followup.send(
                f"{interaction.user.mention}將{before_starlevel}星 __{safe_target}__ 給破壞了",
                file=discord.File("c:/Users/User/Desktop/DiscordBot/TMSBug_v2/Data/StarForceDestroyed.png"),
                ephemeral=False
            )
    
    button.callback = button_callback

    view = View(timeout=60)
    view.add_item(button)

    return embed, view    

def enhance(nowlevel):
        
    if nowlevel not in Starforcetable:
       
        nowlevel = nowlevel
        price = 0
            
    success, destroy, fail, price = Starforcetable[nowlevel]
    rand = random.random()
    
    if rand < success:
        newlevel = nowlevel + 1
        situation = "success"
    elif rand < success + fail:
        newlevel = nowlevel
        situation = "fail"
    else:        
        newlevel = 12
        situation = "destroy"   
    return newlevel, price, situation