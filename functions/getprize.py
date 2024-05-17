import random
import json
import discord

from functions.tinyfunctions import probably

with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\FashionBoxProbabilityTable.json', 'r', encoding='utf-8') as fashionfile:
    fashiondata = json.load(fashionfile)

with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json', 'r', encoding='utf-8') as applefile:
    appledata = json.load(applefile)

def reloaddata():
    global fashiondata, appledata
    with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\FashionBoxProbabilityTable.json', 'r', encoding='utf-8') as fashionfile:
        fashiondata = json.load(fashionfile)

    with open(f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json', 'r', encoding='utf-8') as applefile:
        appledata = json.load(applefile)

def use_apple(messageauthor):

    AppleProbabilityTableDate = list(appledata.keys())[-1]

    apple_chance_dict = appledata[AppleProbabilityTableDate]['appletable']
    box_chance_dict = appledata[AppleProbabilityTableDate]['boxtable']

    applecnt = 0
    boxcnt = 0
    boxgetprize = False

    while True:
        randnumber = random.random()

        if applecnt == 100:  # apple > 100抽箱子
            boxcnt += 1
            applecnt = 0
            randnumber = random.random()

            totalchanceupper = 0
            totalchancelower = 0
            for i in box_chance_dict:
                totalchanceupper += box_chance_dict[i]
                if randnumber < totalchanceupper and totalchancelower < randnumber:
                    prize = i
                    boxgetprize = True
                    totalchancelower += box_chance_dict[i]
                    break  # 箱子抽到break for迴圈
            else:
                continue
            break

        applecnt += 1
        totalchanceupper = 0
        totalchancelower = 0
        for i in apple_chance_dict:
            totalchanceupper += apple_chance_dict[i]
            if randnumber < totalchanceupper and totalchancelower < randnumber:
                prize = i
                totalchancelower += apple_chance_dict[i]
                break
        else:
            continue
        break
    total_count = boxcnt*100 + applecnt
    if boxgetprize == True:
        GoldAppleMessage = f"{messageauthor}在第{boxcnt}箱金箱子中，抽到了{prize}"
    else:
        GoldAppleMessage = f"{messageauthor}在第{total_count}顆蘋果中，抽到了{prize}"

    return GoldAppleMessage

def use_apple_FrenzyTotem(messageauthor):
  
    AppleProbabilityTableDate = '00000000'

    apple_chance_dict = appledata[AppleProbabilityTableDate]['appletable']
    box_chance_dict = appledata[AppleProbabilityTableDate]['boxtable']

    applecnt = 0
    boxcnt = 0
    boxgetprize = False

    while True:
        randnumber = random.random()

        if applecnt == 100:  # apple > 100抽箱子
            boxcnt += 1
            applecnt = 0
            randnumber = random.random()

            totalchanceupper = 0
            totalchancelower = 0
            for i in box_chance_dict:
                totalchanceupper += box_chance_dict[i]
                if randnumber < totalchanceupper and totalchancelower < randnumber:
                    prize = i
                    boxgetprize = True
                    totalchancelower += box_chance_dict[i]
                    break  # 箱子抽到break for迴圈
            else:
                continue
            break

        applecnt += 1
        totalchanceupper = 0
        totalchancelower = 0
        for i in apple_chance_dict:
            totalchanceupper += apple_chance_dict[i]
            if randnumber < totalchanceupper and totalchancelower < randnumber:
                prize = i
                totalchancelower += apple_chance_dict[i]
                break
        else:
            continue
        break
    total_count = boxcnt*100 + applecnt
    if boxgetprize == True:
        GoldAppleMessage = f"{messageauthor}在第{boxcnt}箱金箱子中，抽到了{prize}"
    else:
        GoldAppleMessage = f"{messageauthor}在第{total_count}顆蘋果中，抽到了{prize}"

    return GoldAppleMessage

def use_fashionbox(messageauthor):

    FashionBoxProbabilityTableDate = list(fashiondata.keys())[-1]

    fashion_box_chance_dict = fashiondata[FashionBoxProbabilityTableDate]['table']    

    boxcnt = 0
    boxgetprize = False
    while True:
        randnumber = random.random()
        if boxcnt == 10:
            prize = 0
            break
                    
        boxcnt += 1
        totalchanceupper = 0
        totalchancelower = 0
        for item in fashion_box_chance_dict:
            totalchanceupper += fashion_box_chance_dict[item]
            if randnumber < totalchanceupper and totalchancelower < randnumber:
                prize = item
                boxgetprize = True                    
                break                
            totalchancelower += fashion_box_chance_dict[item]
        else:
            continue
        break     

    if boxgetprize == True:
        FashionboxMessage = f"{messageauthor}在第{boxcnt}箱時尚隨機箱中，抽到了**{prize}**"
    else:
        FashionboxMessage = f"{messageauthor}<a:pootong_gif:802915645670293514>"

    return FashionboxMessage

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



