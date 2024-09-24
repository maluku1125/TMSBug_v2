import discord
from discord import app_commands
from discord.ext import commands
import datetime
from discord.app_commands import Choice
import math

from functions.SlashCommandManager import UseSlashCommand
    
def CalculateUnionPower_combatpower(combatpower):
    if combatpower <= 499999:
        union_power = 2.00 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.00*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 999999:
        union_power = 2.05 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.05*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 4999999:
        union_power = 2.10 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.10*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 9999999:
        union_power = 2.15 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.15*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 19999999:
        union_power = 2.20 * 750 * math.sqrt(combatpower + 30000) 
        formula = "2.20*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 39999999:
        union_power = 2.25 * 750 * math.sqrt(combatpower + 30000) 
        formula = "2.25*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 59999999:
        union_power = 2.30 * 750 * math.sqrt(combatpower + 30000) 
        formula = "2.30*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 79999999:
        union_power = 2.35 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.35*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 99999999:
        union_power = 2.40 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.40*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 124999999:
        union_power = 2.45 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.45*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 149999999:
        union_power = 2.50 * 750 * math.sqrt(combatpower + 30000) 
        formula = "2.50*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 174999999:
        union_power = 2.55 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.55*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 199999999:
        union_power = 2.60 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.60*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 249999999:
        union_power = 2.65 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.65*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 299999999:
        union_power = 2.70 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.70*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 349999999:
        union_power = 2.75 * 750 * math.sqrt(combatpower + 30000)
        formula
    elif combatpower <= 399999999:
        union_power = 2.80 * 750 * math.sqrt(combatpower + 30000) 
        formula = "2.80*750*sqrt(戰鬥力+30000)"
    elif combatpower <= 499999999:
        union_power = 2.85 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.85*750*sqrt(戰鬥力+30000)"
    else:
        union_power = 2.90 * 750 * math.sqrt(combatpower + 30000)
        formula = "2.90*750*sqrt(戰鬥力+30000)"
    
    return union_power, formula

def CalculateUnionPower_level(level):
    if 60 <= level <= 99:
        union_power = 0.5 * (level ** 3)
        formula = "0.5*等級^3"
    elif 100 <= level <= 139:
        union_power = 0.4 * (level ** 3)
        formula = "0.4*等級^3"
    elif 140 <= level <= 179:
        union_power = 0.7 * (level ** 3)
        formula = "0.7*等級^3"
    elif 180 <= level <= 199:
        union_power = 0.8 * (level ** 3)
        formula = "0.8*等級^3"
    elif 200 <= level <= 209:
        union_power = level ** 3
        formula = "1*等級^3"
    elif 210 <= level <= 219:
        union_power = 1.1 * (level ** 3)
        formula = "1.1*等級^3"
    elif 220 <= level <= 229:
        union_power = 1.15 * (level ** 3)
        formula = "1.15*等級^3"
    elif 230 <= level <= 239:
        union_power = 1.2 * (level ** 3)
        formula = "1.2*等級^3"
    elif 240 <= level <= 249:
        union_power = 1.25 * (level ** 3)
        formula = "1.25*等級^3"
    elif 250 <= level <= 259:
        union_power = 1.3 * (level ** 3)
        formula = "1.3*等級^3"
    elif 260 <= level <= 269:
        union_power = 1.35 * (level ** 3)
        formula = "1.35*等級^3"
    elif 270 <= level <= 279:
        union_power = 1.4 * (level ** 3)
        formula = "1.4*等級^3"
    elif 280 <= level <= 289:
        union_power = 1.45 * (level ** 3)
        formula = "1.45*等級^3"
    elif 290 <= level <= 299:
        union_power = 1.5 * (level ** 3)
        formula = "1.5*等級^3"
    elif level >= 300:
        union_power = 1.55 * (level ** 3)
        formula = "1.55*等級^3"
    else:
        raise ValueError("Level must be 60 or higher.")
    
    return union_power, formula


class Slash_Formulas(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    #----------------------------------
    @app_commands.command(name="formulas各式公式", description="各種公式")
    @app_commands.describe(
            formulas = "功能", 
            var_1 = "變數1", var_2 = "變數2", var_3 = "變數3", var_4 = "變數4", var_5 = "變數5",
        )
    @app_commands.choices(
        formulas = [
            Choice(name = "說明", value = "help"), 
            Choice(name = "戰地攻擊力", value = "unionattackdamage"),
            Choice(name = "等差終傷", value = "levelfinaldamage"),
            Choice(name = "等差經驗", value = "levelexpmpdifier"),]
        )
        
    async def formulas(
        self, interaction: discord.Interaction, 
        formulas: str, 
        var_1: int=0, var_2: int=0, var_3: int=0, var_4: int=0, var_5: int=0):
        
        await interaction.response.defer()
        
        if formulas == "help":
            embed = discord.Embed(
                title="公式說明", description="各種公式", color=0x00ff00
                )
            embed.add_field(
                name="戰地攻擊力",
                value=(
                    "```autohotkey\n"
                    f"1:等級\n"
                    f"2:戰鬥力\n```"                
                ),
                inline=True,
            )
            embed.add_field(
                name="等差終傷",
                value=(
                    "```autohotkey\n"
                    f"1:角色等級\n"
                    f"2:怪物等級\n```"                
                ),
                inline=True,
            )
            embed.add_field(
                name="等差經驗",
                value=(
                    "```autohotkey\n"
                    f"1:角色等級\n"
                    f"2:怪物等級\n```"                
                ),
                inline=True,
            )
            
        if formulas == "unionattackdamage":
            embed = unionattackdamage(var_1, var_2)    
        elif formulas == "levelfinaldamage":    
            embed = levelfinaldamage(var_1, var_2)   
        elif formulas == "levelexpmpdifier":
            embed = levelexpmpdifier(var_1, var_2)
            
        UseSlashCommand('formulas', interaction)   
                     
        await interaction.edit_original_response(embed=embed)

def unionattackdamage(calculatevar_1, calculatevar_2):  
    if calculatevar_1 > 300 or calculatevar_1 < 60: 
        embed = discord.Embed(
            title="***戰地攻擊力***", description="**等級需介於60~300等之間**", color=0xff0000
            )
    else:            
        UnionPower_level, formula_level = CalculateUnionPower_level(calculatevar_1)
        UnionPower_combatpower, formula_combatpower = CalculateUnionPower_combatpower(calculatevar_2)
        
        embed = discord.Embed(
            title="***戰地攻擊力***", description="", color=0xFF8040
            )
        embed.add_field(
            name="",
            value=(
                "```autohotkey\n"
                f"等級　　　　:{calculatevar_1}\n"
                f"戰鬥力　　　:{calculatevar_2:,}\n"  
                f"戰地攻擊力　:{round(UnionPower_level + UnionPower_combatpower + 312500):,}\n```"               
            ),
            inline=False,
        )
        embed.set_footer(text=f"戰地攻擊力={formula_level}+{formula_combatpower}+312500")
    return embed

def levelfinaldamage(calculatevar_1, calculatevar_2):
    
    delta_level = calculatevar_1 - calculatevar_2
    
    if delta_level >= 0:
        final_damage = 1.1 + 0.02 * min(delta_level,5)
        formula = "1.1+0.02*等差"
    elif -5 <= delta_level < 0:
        final_damage = (1.1 + 0.02 * delta_level) * (1 + 0.025 * delta_level)
        formula = "(1.1+0.02*等差)*(1+0.025*等差)"
    elif -40 < delta_level < -5:
        final_damage = 1 + 0.025 * delta_level
        formula = "(1+0.025*等差)"
    elif delta_level <= -40:
        final_damage = 0
        formula = "固定1點傷害"
        
    embed = discord.Embed(
        title="***等差終傷***", description="", color=0xFF8040
        )
    embed.add_field(
        name="",
        value=(
            "```autohotkey\n"
            f"角色等級　:{calculatevar_1}\n"
            f"怪物等級　:{calculatevar_2:,}\n"  
            f"等差終傷　:{(final_damage*100):.1f}%\n```"               
        ),
        inline=False,
    )
    # embed.add_field(
    #     name="",
    #     value=(
    #         "```autohotkey\n"
    #         f"-40~0: (1-0.025*等差)\n" 
    #         f"-5~+5: (1.1-0.02*等差)\n"   
    #         f"兩項相乘\n```"                 
    #     ),
    #     inline=False,
    # )

    embed.set_footer(text=f"等差終傷={formula}")
    
    return embed

def levelexpmpdifier(calculatevar_1, calculatevar_2):
    
    delta_level = float(calculatevar_1 - calculatevar_2)
    
    if 1 >= delta_level >= -1:
        expmpdifier = 1.2
        formula = "±0~1等 +20%"
    elif 4 >= delta_level > 1:
        expmpdifier = 1.1
        formula = "±2~4等 +10%"
    elif 9 >= delta_level > 4:
        expmpdifier = 1.05
        formula = "+5~9等 +5%"
    elif delta_level == 10 or delta_level == -10:
        expmpdifier = 1.00
        formula = "+0%"
    elif 18 >= delta_level > 10:
        expmpdifier = 1 - round((delta_level-10)/2)*0.01
        formula = "+10~20等 每2等-1%"
    elif 20 >= delta_level > 18:
        expmpdifier = 0.95
        formula = "+10~20等 每2等-1%"    
    elif delta_level > 20:
        expmpdifier = 1 - min((delta_level-10),30) * 0.01
        formula = "+21等以上 每1等-1% max-30%"
    elif -4 <= delta_level < -1:
        expmpdifier = 1.1
        formula = "±2~4等 +10%"
    elif -9 <= delta_level < -4:
        expmpdifier = 1.05
        formula = "±5~9等 +5%"
    elif -20 <= delta_level < -10:    
        expmpdifier = 1 + (delta_level+10)*0.01
        formula = "-10~20等 每1等%"
    elif delta_level < -20:    
        expmpdifier = 0.7 + max((delta_level+21),-15)*0.04
        formula = "-21等以上 每1等-4% max-90%"
        
    embed = discord.Embed(
        title="***等差經驗***", description="", color=0xFF8040
        )
    embed.add_field(
        name="",
        value=(
            "```autohotkey\n"
            f"角色等級　:{calculatevar_1}\n"
            f"怪物等級　:{calculatevar_2:,}\n"  
            f"等差經驗　:{(expmpdifier*100):.1f}%\n```"               
        ),
        inline=False,
    )  

    embed.set_footer(text=f"等差經驗={formula}")
    
    return embed