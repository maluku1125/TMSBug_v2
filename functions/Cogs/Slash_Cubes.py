import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
from discord.ui import Button, View
import random
import json

from functions.SlashCommandManager import UseSlashCommand 
from functions.tinyfunctions import probably

with open(f'C:\\Users\\User\\Desktop\\DiscordBot\\TMSBug_v2\\Data\\Cubes.json', 'r', encoding='utf-8') as f:
    cubestable = json.load(f)

def rolldice(cube_table):
    items = list(cube_table.items())
    total_weight = sum(weight for _, weight in items)
    random_value = random.uniform(0, total_weight)
    current_sum = 0

    for item, weight in items:
        current_sum += weight
        if random_value <= current_sum:
            return item


class Slash_Cubes(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        
    #-----------------BOSS-----------------
    @app_commands.command(name="cubes洗方塊", description="洗方塊")
    @app_commands.describe(cubetype = "方塊類型", target = "目標部位/類型")
    @app_commands.choices(
        cubetype = [
            Choice(name = "萌獸方塊", value = "familiar"),
            Choice(name = "恢復方塊", value = "renew_cube"),
            Choice(name = "閃耀鏡射方塊", value = "mirror_cube"),
            Choice(name = "閃炫方塊", value = "violet_cube"),
            Choice(name = "新對等方塊", value = "equality_cube"),
            Choice(name = "結合方塊", value = "uni_cube"),
            Choice(name = "珍貴附加方塊", value = "bonus_cube"),
            Choice(name = "恢復附加方塊", value = "bonus_renew_cube"),
            Choice(name = "閃亮附加方塊", value = "shiney_bonus_cube"),
            Choice(name = "絕對附加方塊", value = "abs_bonus_cube"),
        ],
        target = [
            Choice(name = "萌獸", value = ""),
            Choice(name = "武器", value = "1stweapon"),
            Choice(name = "副武器", value = "2ndweapon"),
            Choice(name = "能源", value = "3rdweapon"),
            Choice(name = "帽子", value = "hat"),
            Choice(name = "上衣/套服", value = "top"),
            Choice(name = "下衣", value = "bottom"),
            Choice(name = "手套", value = "gloves"),
            Choice(name = "鞋子", value = "shoes"),
            Choice(name = "下衣", value = "bottom"),
            Choice(name = "披風", value = "cape"),
            Choice(name = "腰帶", value = "belt"),
            Choice(name = "心臟", value = "heart"),
            Choice(name = "肩飾", value = "shoulder"),
            Choice(name = "飾品", value = "accessories"),      
        ],
    )
    async def cubesimulator(self, interaction: discord.Interaction, cubetype: str, target: str):
        
        if cubetype == "familiar":
            embed, view = roll_familiar_cube()
            
        renewcubeparts = ["hat", "top", "bottom", "gloves", "shoes", "cape", "belt", "heart", "shoulder", "accessories", "1stweapon", "2ndweapon", "3rdweapon"]    
        if cubetype != "familiar":
            if  target not in renewcubeparts: 
                await interaction.response.send_message("請選擇正確的部位/類型", ephemeral=True)
                return            
            embed, view = roll_equipment_cube(cubetype, target)
                
        UseSlashCommand('Cubessimulator', interaction)
        
        await interaction.response.send_message(embed=embed, view=view)
        
        
def roll_familiar_cube():
    cubename = "萌獸方塊"
    cubecolor = 0x8F5300
    target = "萌獸"
    
    usedcubecount = 1
    embed = discord.Embed(
        title="洗方塊模擬器", 
        description=f"{cubename}→{target}",
        color=cubecolor,
        )      
    embed.add_field(
        name=f"{cubename}x{usedcubecount}",
        value=(
            f'```{rolldice(cubestable["familiar_cube"])}```'
            f'```{rolldice(cubestable["familiar_cube"])}```'
            f'```{rolldice(cubestable["familiar_cube"])}```'      
        ),
        inline=True,
    )
    
    button = Button(label=cubename, style=discord.ButtonStyle.primary, emoji="<:cube13:1135615167384789084>")
    
    async def button_callback(interaction: discord.Interaction):
        nonlocal usedcubecount
        usedcubecount += 1
        
        embed = discord.Embed(
        title="洗方塊模擬器", 
        color=cubecolor,
        description=f"{cubename}→{target}",
        )  
        embed.add_field( 
            name=f"{cubename}x{usedcubecount}", 
            value=(
            f'```{rolldice(cubestable["familiar_cube"])}```'
            f'```{rolldice(cubestable["familiar_cube"])}```'
            f'```{rolldice(cubestable["familiar_cube"])}```'            
            ),
            inline=True)
        
        await interaction.response.edit_message(embed=embed, view=view)

    button.callback = button_callback
    
    view = View(timeout=60)
    view.add_item(button)
    
    return embed, view

def Convert_cubeandtarget(cubetype, target):
    if target == "1stweapon":
        target = "weapon"
        targetname = "武器"
    elif target == "2ndweapon":
        target = "weapon"
        targetname = "副武器"
        if cubetype == "bonus_cube" or cubetype == "bonus_renew_cube" or cubetype == "shiney_bonus_cube" or cubetype == "abs_bonus_cube":
            target = "2ndweapon"
            targetname = "副武器"
    elif target == "3rdweapon":
        targetname = "能源"
    elif target == "hat":
        targetname = "帽子"
    elif target == "top":
        targetname = "上衣/套服"
    elif target == "bottom":
        targetname = "下衣"
    elif target == "gloves":
        targetname = "手套"
    elif target == "shoes":
        targetname = "鞋子"
    elif target == "cape":
        targetname = "披風"
    elif target == "belt":
        target = "cape"
        targetname = "腰帶"
    elif target == "heart":
        target = "cape"
        targetname = "心臟"
    elif target == "shoulder":
        target = "cape"
        targetname = "肩飾"
    elif target == "accessories":
        targetname = "飾品"
        
    if cubetype == "renew_cube":
        cubename = "恢復方塊"
        cubecolor = 0x548C00      
        cubeemoji = "<:cube15:1135615190524776559>"
    elif cubetype == "mirror_cube":
        cubename = "閃耀鏡射方塊"
        cubecolor = 0xCB8119      
        cubeemoji = "<:cube9:901346916833574982>"
    elif cubetype == "violet_cube":
        cubename = "閃炫方塊"
        cubecolor = 0xAE79DF      
        cubeemoji = "<:cube7:901346808591179796>"
    elif cubetype == "equality_cube":
        cubename = "新對等方塊"
        cubecolor = 0x9CE1FF      
        cubeemoji = "<:cube10:901346946248233000>"
    elif cubetype == "uni_cube":
        cubename = "結合方塊"
        cubecolor = 0x4488CC      
        cubeemoji = "<:cube8:901346878854135869>"
    elif cubetype == "bonus_cube":
        cubename = "珍貴附加方塊"
        cubecolor = 0xffC8E1      
        cubeemoji = "<:cube16:1135615213413085234>"          
    elif cubetype == "bonus_renew_cube":
        cubename = "恢復附加方塊"
        cubecolor = 0xC2EB9F      
        cubeemoji = "<:cube17:1135615229259153449>"   
    elif cubetype == "shiney_bonus_cube":
        cubename = "閃亮附加方塊"
        cubecolor = 0xF6F9A2      
        cubeemoji = "<:cube18:1300867791985053716>"    
    elif cubetype == "abs_bonus_cube":
        cubename = "絕對附加方塊"
        cubecolor = 0x9CBCEF      
        cubeemoji = "<:cube13:1283030624080367701>"
        
    
        
    return target, targetname, cubename, cubecolor, cubeemoji
 
def create_rollcube_content(target, cubetype):
    
    content = "出現錯誤"
    
    # 恢復方塊  
    if cubetype == "renew_cube":
        content = (
            f'```{rolldice(cubestable[cubetype]["legendary"][target])}```'     
            f'```{rolldice(cubestable[cubetype]["legendary"][target]) if probably(0.2) else rolldice(cubestable[cubetype]["unique"][target])}```'
            f'```{rolldice(cubestable[cubetype]["legendary"][target]) if probably(0.05) else rolldice(cubestable[cubetype]["unique"][target])}```'
            )
        
    # 閃耀鏡射
    if cubetype == "mirror_cube": 
        firstaffix = f'```{rolldice(cubestable[cubetype]["legendary"][target])}```'  
        if probably(0.2):
            secondaffix = firstaffix
        else:
            secondaffix = f'```{rolldice(cubestable[cubetype]["legendary"][target]) if probably(0.2) else rolldice(cubestable[cubetype]["unique"][target])}```'
        
        content = (
            f'{firstaffix}'     
            f'{secondaffix}'
            f'```{rolldice(cubestable[cubetype]["legendary"][target]) if probably(0.05) else rolldice(cubestable[cubetype]["unique"][target])}```'
            )       
    
    # 閃炫方塊
    if cubetype == "violet_cube":
        content = (
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target])}```'     
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target]) if probably(0.2) else rolldice(cubestable["renew_cube"]["unique"][target])}```'
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target]) if probably(0.15) else rolldice(cubestable["renew_cube"]["unique"][target])}```'
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target])}```'     
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target]) if probably(0.2) else rolldice(cubestable["renew_cube"]["unique"][target])}```'
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target]) if probably(0.15) else rolldice(cubestable["renew_cube"]["unique"][target])}```'
            )
        
    #新對等方塊
    if cubetype == "equality_cube":
        content = (
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target])}```'     
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target])}```'
            f'```{rolldice(cubestable["renew_cube"]["legendary"][target])}```'
            )
    
    #附加恢復方塊 / 珍貴附加方塊
    if cubetype == "bonus_cube" or cubetype == "bonus_renew_cube":
        content = (
            f'```{rolldice(cubestable["bonus_renew_cube"]["legendary"][target])}```'     
            f'```{rolldice(cubestable["bonus_renew_cube"]["legendary"][target]) if probably(0.005) else rolldice(cubestable["bonus_renew_cube"]["unique"][target])}```'
            f'```{rolldice(cubestable["bonus_renew_cube"]["legendary"][target]) if probably(0.005) else rolldice(cubestable["bonus_renew_cube"]["unique"][target])}```'
            )
        
    #閃亮附加方塊
    if cubetype == "shiney_bonus_cube":
        content = (
            f'```{rolldice(cubestable["shiney_bonus_cube"]["legendary"][target])}```'     
            f'```{rolldice(cubestable["shiney_bonus_cube"]["legendary"][target]) if probably(0.005) else rolldice(cubestable["shiney_bonus_cube"]["unique"][target])}```'
            f'```{rolldice(cubestable["shiney_bonus_cube"]["legendary"][target]) if probably(0.005) else rolldice(cubestable["shiney_bonus_cube"]["unique"][target])}```'
            )
    
    #絕對附加方塊
    if cubetype == "abs_bonus_cube":
        content = (
            f'```{rolldice(cubestable["abs_bonus_cube"]["legendary"][target])}```'     
            f'```{rolldice(cubestable["abs_bonus_cube"]["legendary"][target])}```'
            f'```{rolldice(cubestable["abs_bonus_cube"]["unique"][target])}```'
            )
        
        
           
    return content
   
def uni_cube(cubetype, target, secondaffix): 
    # 結合方塊
    if cubetype == "uni_cube":
        
        chosenaffix = random.choice([1, 2, 3])
        
        if  chosenaffix == 2:
            secondaffix = f'{rolldice(cubestable[cubetype]["legendary"][target]) if probably(0.15) else rolldice(cubestable[cubetype]["unique"][target])}'
        
        
        firstattribute = (
            f'```{"fix" if chosenaffix == 1 else "" }\n'  
            f'{"-"*10}```' 
            )
        secondattribute = (
            f'```{"fix" if chosenaffix == 2 else "" }\n'  
            f'{secondaffix}```' 
            )
        thirdattribute = (
            f'```{"fix" if chosenaffix == 3 else "" }\n'  
            f'{"-"*10}```' 
            )   
        content = (
            f'{firstattribute}'     
            f'{secondattribute}'
            f'{thirdattribute}'
            )
        
    return content, secondaffix
   
def roll_equipment_cube(cubetype, target):
    
    target, targetname, cubename, cubecolor, cubeemoji = Convert_cubeandtarget(cubetype, target) 

    content = create_rollcube_content(target, cubetype)
    
    if cubetype == "uni_cube":
        secondaffix = 'MP + 10%'
        content, secondaffix = uni_cube(cubetype, target, secondaffix)
    
        
    usedcubecount = 1
    embed = discord.Embed(
        title="洗方塊模擬器", 
        description=f"{cubename}→{targetname}",
        color=cubecolor,
        )      
    embed.add_field(
        name=f"{cubename}x{usedcubecount}",
        value = content,
        inline = True,
    )
    
    button = Button(label=cubename, style=discord.ButtonStyle.primary, emoji=cubeemoji)
    
    async def button_callback(interaction: discord.Interaction):
        content = create_rollcube_content(target, cubetype)
        nonlocal secondaffix
        nonlocal usedcubecount
        usedcubecount += 1
        
        if cubetype == "uni_cube":
            content, secondaffix = uni_cube(cubetype, target, secondaffix)
        
        
        embed = discord.Embed(
        title="洗方塊模擬器", 
        color=cubecolor,
        description=f"{cubename}→{targetname}",
        )  
        embed.add_field(
            name=f"{cubename}x{usedcubecount}",
            value = content,
            inline = True,
        )
        if cubetype == "shiney_bonus_cube":
            UnitoLegchance = round(0.003 + 0.00005*usedcubecount,5)
            if probably(UnitoLegchance):
                embed.add_field(
                    name=f"",
                    value = "**跳框了**",
                    inline = False,
                )
                usedcubecount = 1
            embed.set_footer(text=f'罕跳傳機率 : {UnitoLegchance*100:.3f}%')
        
        await interaction.response.edit_message(embed=embed, view=view)

    button.callback = button_callback
    
    view = View(timeout=60)
    view.add_item(button)
    
    return embed, view

