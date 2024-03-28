import requests
import json
import discord
import datetime

serverlogo = {
    "艾麗亞" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/ai_li_ya.png",
    "普力特" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/pu_li_te.png",
    "琉德" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/liu_de.png",
    "優依娜" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/you_yi_na.png",
    "愛麗西亞" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/ai_li_xi_ya.png",
    "殺人鯨" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/sha_ren_jing.png",
    "Reboot" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/reboot.png",
}
worldnumber = {
    "艾麗亞" : 0,
    "普力特" : 1,
    "琉德" : 4,
    "優依娜" : 3,
    "愛麗西亞" : 4,
    "殺人鯨" : 6,
    "Reboot" : 45,
}

def Request_UnionRank(target):

    url = "https://tw-event.beanfun.com/MapleStory/api/UnionWebRank/GetRank"

    # 設置請求酬載
    payload = {
        "RankType": "3", #3 = 總等級排行 1 = 攻擊力排行
        "GameWorldId": "-1", 
        "CharacterName": f"{target}",
        #"page": "4"
        }

    # 設置標頭
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 發送POST請求
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    # 檢查響應
    if response.status_code == 200:
        # 請求成功，處理響應
        data = response.json()
        RequestSuccess = 'True'
    else:
        # 請求失敗，處理錯誤
        RequestSuccess = 'False'
        data = None

    return data, RequestSuccess

def Request_serverUnionRank(server, target):

    url = "https://tw-event.beanfun.com/MapleStory/api/UnionWebRank/GetRank"

    # 設置請求酬載
    payload = {
        "RankType": "2", #3 = 總等級排行 2 = 角色等級排行 1 = 攻擊力排行
        "GameWorldId": f"{server}", 
        "CharacterName": f"{target}",
        #"page": "4"
        }

    # 設置標頭
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 發送POST請求
    response = requests.post(url, data=json.dumps(payload), headers=headers)

    # 檢查響應
    if response.status_code == 200:
        # 請求成功，處理響應
        data = response.json()
        character_data = data['Data']
        Rank = character_data['Rank']
    else:
        # 請求失敗，處理錯誤
        data = None
        Rank = 999999

    return Rank
    
def Create_UnionRank_embed(playername):

    data, RequestSuccess = Request_UnionRank(playername)
    nowtime = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')

    # Assuming 'data' is the response dictionary you received
    if data.get('Code', -1) != 1 or RequestSuccess == 'False':
        embed = discord.Embed(
            title = f"**{playername}**", 
            description = f'查無此角色ID或該名角色ID未在10000名排行榜名單內', 
            color = 0xff0000,
            )       
        embed.set_footer(text=f'查詢時間:{nowtime}')
        return embed

    else:
        character_data = data['Data']

        CharacterName = character_data['CharacterName']
        CharacterJob = character_data['JobName']
        Level = character_data['UnionLevel']
        UnionTotalLevel = character_data['UnionTotalLevel']
        UnionDPS = character_data['UnionDPS']
        Guild = character_data['Guild']
        Rank = character_data['Rank']
        GameWorldName = character_data['GameWorldName']
        CharacterLookUrl = character_data['CharacterLookUrl']

        server_lv_rank = Request_serverUnionRank(worldnumber[GameWorldName], playername)

        embed = discord.Embed(
            title = f"", 
            description = f'[TMS聯盟戰地排行榜](https://tw-event.beanfun.com/MapleStory/UnionWebRank/Index.aspx)', 
            color = 0x6f00d2,
            )
        
        embed.set_author(name=f"{CharacterName}", icon_url=serverlogo[GameWorldName])

        embed.add_field(
            name="基本資料",
            value=(
                "```autohotkey\n"
                f"等級: {Level}\n"
                f"職業: {CharacterJob}\n"
                f"公會: {Guild}\n```"
            ),
            inline=False,
        )
        
        embed.add_field(
            name="聯盟戰地",
            value=(
                "```autohotkey\n"
                f"聯盟等級: {UnionTotalLevel}\n"
                f"攻擊力　: {UnionDPS:<9,}\n"
                f"戰地硬幣: {round(UnionDPS/1251251.26,1)}\n```"
                
            ),
            inline=False,
        )

        embed.add_field(
            name="排行",
            value=(
                "```autohotkey\n"
                f"全服聯盟總等級: {Rank}\n"
                f"伺服器角色等級: {server_lv_rank}\n```"                
            ),
            inline=False,
        )
        #embed.add_field(name="等級", value=f"{Level}", inline = True) 
        #embed.add_field(name="職業", value=f"{CharacterJob}", inline = True)

        #embed.add_field(name="戰地排名", value=f"{Rank}", inline = False)
        #embed.add_field(name="戰地等級", value=f"{UnionTotalLevel}", inline = True)
        #embed.add_field(name="戰地攻擊力", value=f"{UnionDPS}", inline = True)

        #embed.add_field(name="每日戰地硬幣", value=f"{round(UnionDPS/1251251.26,1)}", inline = False)   

        #embed.add_field(name="伺服器", value=f"{GameWorldName}", inline = True)
        #embed.add_field(name="公會", value=f"{Guild}", inline = True)

        embed.set_thumbnail(url=CharacterLookUrl)
        embed.set_footer(text=f'查詢時間 : {nowtime}')

        return embed