import json
import discord


def Create_FashionBox_embed():
    with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\FashionBoxProbabilityTable.json', 'r', encoding='utf-8') as f:

        data = json.load(f)

        FashionBoxProbabilityTableDate = list(data.keys())[-1]
        fashion_box_chance_dict = data[FashionBoxProbabilityTableDate]

        fashionbox_table=[]
        for unit, value in fashion_box_chance_dict.items():
            fashionbox_table.append(f"{unit}: {value}")

        fashionboxValue = '\n'.join(fashionbox_table)

        embed = discord.Embed(
            title=f"**時尚隨機箱**", 
            description = f'開始日期{FashionBoxProbabilityTableDate}', 
            color=0xfbe222,
            )
        

        embed.add_field(name="**機率表**", value = fashionboxValue, inline = False)
        
    return embed

def Create_Apple_embed():
    with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json', 'r', encoding='utf-8') as f:

        data = json.load(f)

        AppleProbabilityTableDate = list(data.keys())[-1]

        Apple_chance_dict = data[AppleProbabilityTableDate]['apple_chance']
        box_chance_dict = data[AppleProbabilityTableDate]['box_chance']

        Apple_table=[]
        for unit, value in Apple_chance_dict.items():
            Apple_table.append(f"{unit}: {value}")

        AppleValue = '\n'.join(Apple_table)

        BOX_table=[]
        for unit, value in box_chance_dict.items():
            BOX_table.append(f"{unit}: {value}")

        BoxValue = '\n'.join(BOX_table)

        embed = discord.Embed(
            title=f"**黃金蘋果**", 
            description = f'開始日期{AppleProbabilityTableDate}', 
            color=0xfbe222,
            )
        

        embed.add_field(name="**蘋果機率**", value = AppleValue, inline = True)

        embed.add_field(name="**金箱機率**", value = BoxValue, inline = True)
    return embed

