import requests
import json
import discord
import datetime

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

        embed = discord.Embed(
            title = f"**{CharacterName}**", 
            description = f'[TMS聯盟戰地排行榜](https://tw-event.beanfun.com/MapleStory/UnionWebRank/Index.aspx)', 
            color = 0x6f00d2,
            )
        embed.add_field(name="等級", value=f"{Level}", inline = True) 
        embed.add_field(name="職業", value=f"{CharacterJob}", inline = True)

        embed.add_field(name="戰地排名", value=f"{Rank}", inline = False)
        embed.add_field(name="戰地等級", value=f"{UnionTotalLevel}", inline = True)
        embed.add_field(name="戰地攻擊力", value=f"{UnionDPS}", inline = True)

        embed.add_field(name="每日戰地硬幣", value=f"{round(UnionDPS/1251251.26,1)}", inline = False)   

        embed.add_field(name="伺服器", value=f"{GameWorldName}", inline = True)
        embed.add_field(name="公會", value=f"{Guild}", inline = True)

        embed.set_thumbnail(url=CharacterLookUrl)
        embed.set_footer(text=f'查詢時間:{nowtime}')

        return embed