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
        #print(data)
    else:
        # 請求失敗，處理錯誤
        print(f"Error: {response.status_code}, {response.text}")

    # Assuming 'data' is the response dictionary you received
    if data['Code'] == 1:
        character_data = data['Data']
        '''print(f"Character Name: {character_data['CharacterName']}")
        print(f"Rank: {character_data['Rank']}")
        print(f"Game World Name: {character_data['GameWorldName']}")
        print(f"Job Name: {character_data['JobName']}")
        print(f"Union DPS: {character_data['UnionDPS']}")
        print(f"Union Total Level: {character_data['UnionTotalLevel']}")
        print(f"Level: {character_data['UnionLevel']}")
        print(f"Guild: {character_data['Guild']}")'''

        CharacterName = character_data['CharacterName']
        CharacterJob = character_data['JobName']
        Level = character_data['UnionLevel']
        UnionTotalLevel = character_data['UnionTotalLevel']
        UnionDPS = character_data['UnionDPS']
        Guild = character_data['Guild']
        Rank = character_data['Rank']
        GameWorldName = character_data['GameWorldName']
        CharacterLookUrl = character_data['CharacterLookUrl']
        RequestSuccess = 'True'
        
        return CharacterName, CharacterJob, Level, UnionTotalLevel, UnionDPS, Guild, Rank, GameWorldName, CharacterLookUrl, RequestSuccess

    else:
        RequestSuccess = 'False'
        CharacterName = ''
        CharacterJob = ''
        Level = ''
        UnionTotalLevel = ''
        UnionDPS = ''
        Guild = ''
        Rank = ''
        GameWorldName = ''
        CharacterLookUrl = ''
        return CharacterName, CharacterJob, Level, UnionTotalLevel, UnionDPS, Guild, Rank, GameWorldName, CharacterLookUrl, RequestSuccess
    

def Create_UnionRank_embed(playername):

    CharacterName, CharacterJob, Level, UnionTotalLevel, UnionDPS, Guild, Rank, GameWorldName, CharacterLookUrl, RequestSuccess = Request_UnionRank(playername)
    nowtime = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')

    if RequestSuccess == 'False':
        embed = discord.Embed(
            title=f"**發生錯誤**", 
            description = f'{playername} 不存在或請求錯誤', 
            color=0xff0000,
            )        
        return embed
    else:     

        embed = discord.Embed(
            title=f"**{CharacterName}**", 
            description = f'[TMS聯盟戰地排行榜](https://tw-event.beanfun.com/MapleStory/UnionWebRank/Index.aspx)', 
            color=0x6f00d2,
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

if __name__ == "__main__":
    Request_UnionRank("諭諭0")
