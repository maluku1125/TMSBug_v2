import json
import discord

with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\FashionBoxProbabilityTable.json', 'r', encoding='utf-8') as fashionfile:
    fashiondata = json.load(fashionfile)

with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json', 'r', encoding='utf-8') as applefile:
    appledata = json.load(applefile)

def Create_FashionBox_embed(): 

    FashionBoxProbabilityTableDate = list(fashiondata.keys())[-1]
    fashion_box_chance_dict = fashiondata[FashionBoxProbabilityTableDate]['table'] 

    max_length = max(len(unit) for unit in fashion_box_chance_dict.keys())

    fashionbox_table=[]
    totalchance = 0
    for unit, value in fashion_box_chance_dict.items():
        unit = unit.ljust(max_length).replace(' ', '\u2003')
        fashionbox_table.append(f"{unit}: {value*100:.2f}%")
        totalchance += value

    fashionboxValue = '```autohotkey\n' + '\n'.join(fashionbox_table) + '\n```'

    starttime = fashiondata[FashionBoxProbabilityTableDate]['starttime']
    endtime = fashiondata[FashionBoxProbabilityTableDate]['endtime']

    embed = discord.Embed(
        title=f"**時尚隨機箱**", 
        description = f'開始時間 : {starttime}\n結束時間 : {endtime}', 
        color=0xfbe222,
        )

    embed.add_field(name="**機率表**", value = fashionboxValue, inline = False)
    
    embed.set_footer(text=f'大獎總機率: {totalchance*100:.2f}%')
        
    return embed

def Create_Apple_embed():

    AppleProbabilityTableDate = list(appledata.keys())[-1]

    Apple_chance_dict = appledata[AppleProbabilityTableDate]['appletable']
    box_chance_dict = appledata[AppleProbabilityTableDate]['boxtable']

    max_length1 = max(len(unit) for unit in Apple_chance_dict.keys())
    max_length2 = max(len(unit) for unit in box_chance_dict.keys())

    Apple_table=[]
    totalchance1 = 0
    for unit, value in Apple_chance_dict.items():
        unit = unit.ljust(max_length1).replace(' ', '\u2003')
        Apple_table.append(f"{unit}: {value*100:.2f}%")
        totalchance1 += value

    AppleValue = '```autohotkey\n' + '\n'.join(Apple_table) + '\n```'

    BOX_table=[]
    totalchance2 = 0
    for unit, value in box_chance_dict.items():
        unit = unit.ljust(max_length2).replace(' ', '\u2003')
        BOX_table.append(f"{unit}: {value*100:.2f}%")
        totalchance2 += value

    BoxValue = '```autohotkey\n' + '\n'.join(BOX_table) + '\n```'

    starttime = appledata[AppleProbabilityTableDate]['starttime']
    endtime = appledata[AppleProbabilityTableDate]['endtime']

    embed = discord.Embed(
        title=f"**黃金蘋果**", 
        description = f'開始時間 : {starttime}\n結束時間 : {endtime}',  
        color=0xfbe222,
        )
    

    embed.add_field(name="**蘋果機率**", value = AppleValue, inline = False)

    embed.add_field(name="**金箱機率**", value = BoxValue, inline = False)

    embed.set_footer(text=f'蘋果總機率: {totalchance1*100:.2f}% 金箱總機率: {totalchance2*100:.2f}%')

    return embed

