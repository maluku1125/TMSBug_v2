import random
import json
import os
import glob

from functions.tinyfunctions import probably


def use_apple(messageauthor):

    # open file
    AplleProbabilityFile = f'C:\\Users\\User\\Desktop\\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json'

    with open(AplleProbabilityFile, 'r', encoding='utf-8') as file:
        data = json.load(file)

        AppleProbabilityTableDate = list(data.keys())[-1]

        apple_chance_dict = data[AppleProbabilityTableDate]['apple_chance']
        box_chance_dict = data[AppleProbabilityTableDate]['box_chance']

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

    # open file
    AplleProbabilityFile = f'C:\\Users\\User\\Desktop\\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json'

    with open(AplleProbabilityFile, 'r', encoding='utf-8') as file:
        data = json.load(file)

        AppleProbabilityTableDate = '000000'

        apple_chance_dict = data[AppleProbabilityTableDate]['apple_chance']
        box_chance_dict = data[AppleProbabilityTableDate]['box_chance']

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
     
    FashionBoxProbabilityFile = f'C:\\Users\\User\\Desktop\\DiscordBot\\TMSBug_v2\\Data\\FashionBoxProbabilityTable.json'

    with open(FashionBoxProbabilityFile, 'r', encoding='utf-8') as file:
        
        data = json.load(file)

        FashionBoxProbabilityTableDate = list(data.keys())[-1]

        fashion_box_chance_dict = data[FashionBoxProbabilityTableDate]    

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



