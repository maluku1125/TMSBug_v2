from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import json
import re
import os


def Get_Website_data(page):
    # 創建Chrome瀏覽器選項
    chrome_options = Options()
    chrome_options.add_argument('--headless')

    # 啟動Chromium瀏覽器
    browser = webdriver.Chrome(options=chrome_options)
    # 導航到網頁
    browser.get(f'https://tw-event.beanfun.com/MapleStory/eventad/EventAD.aspx?EventADID={page}')    
    # 等待一些時間，以確保網頁加載完成（您可以根據需要調整等待時間）
    browser.implicitly_wait(10)
    # 獲取網頁內容
    page_source = browser.page_source

    # 使用Beautiful Soup解析網頁內容
    soup = BeautifulSoup(page_source, 'html.parser')

    event_time_text = soup.text.strip()

    match = re.search(r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2})\s*~\s*(\d{4}/\d{2}/\d{2} \d{2}:\d{2})', event_time_text)

    if match:
        event_start_time, event_end_time = match.groups()
    else:
        event_start_time = '2000/01/01 00:00'
        event_end_time = '2999/12/31 23:59'

    table_data = []
    for row in soup.find_all('tr'): # 抓取所有表格"列"
        data = [cell.text.strip() for cell in row.find_all('td')] # 整理每列的資料
        if not data[1]: 
            data[1] = ''
        if data[0] == '道具名稱':
            table_data.append([]) # 如果資料是標頭則新增arr 
        table_data[-1].append(data) # 新增資料至最新的arr

    browser.quit()

    return event_start_time, event_end_time, table_data

def GetGoldAppleData():

    page = 8369
    event_start_time, event_end_time, table_data = Get_Website_data(page)
    print("-"*50)
    print(event_start_time)
    print("-"*50)
    print(event_end_time)
    print("-"*50)

    appledata_json ={}
    boxdata_json ={}

    for i, table in enumerate(table_data):
        if i == 0:
            # Convert the list to a dictionary
            for item in table[1:]:
                prize = item[0]
                if prize == '漆黑的BOSS飾品碎片':
                    break
                try:
                    chance = float(item[1].replace('%', ''))/100
                    chance = round(chance, 5)
                except ValueError:
                    chance = 0
                appledata_json[prize] = chance

            # Convert the dictionary to a JSON string
            data_json = json.dumps(appledata_json, ensure_ascii=False)

            print(data_json)
            print("-"*50)

            saved_data_dict = appledata_json.copy()
        
        if i == 2:
            # Convert the list to a dictionary
            for item in table[1:]:
                prize = item[0]
                if prize in saved_data_dict:                       
                    try:
                        chance = float(item[1].replace('%', ''))/100
                        chance = round(chance, 5)
                    except ValueError:
                        chance = 0

                    boxdata_json[prize] = chance

            # Convert the dictionary to a JSON string
            data_json = json.dumps(boxdata_json, ensure_ascii=False)

            print(data_json)

    return event_start_time, event_end_time, appledata_json, boxdata_json

def GetFashionBoxData():
    page = 8373

    event_start_time, event_end_time, table_data = Get_Website_data(page)
    print("-"*50)
    print(event_start_time)
    print("-"*50)
    print(event_end_time)
    print("-"*50)
    data_dict = {}

    for i, table in enumerate(table_data):
        if i == 0:
            # Convert the list to a dictionary
            for item in table[1:]:
                prize = item[0]
                if prize == '普通彩色稜鏡':
                    break
                try:
                    chance = float(item[1].replace('%', ''))/100
                    chance = round(chance, 5)
                except ValueError:
                    chance = 0
                data_dict[prize] = chance

            # Convert the dictionary to a JSON string
            data_json = json.dumps(data_dict, ensure_ascii=False)

            print(data_json)
            print("-"*50)

    return event_start_time, event_end_time, data_dict
            
def Format_FashionBoxPrizeData():
    event_start_time, event_end_time, data_dict = GetFashionBoxData()
    # 將日期轉換為你想要的格式
    date_key = event_start_time.replace('/', '').split(' ')[0]

    # 建立你想要的數據結構
    formatted_data = {
        date_key: {
            'starttime': event_start_time,
            'endtime': event_end_time,
            'table': data_dict
        }
    }

    # 將數據轉換為 JSON 格式
    formatted_data_json = json.dumps(formatted_data, ensure_ascii=False)
    
    print(formatted_data_json)
    return formatted_data

def Format_ApplePrizeData():
    event_start_time, event_end_time, appledata_json, boxdata_json = GetGoldAppleData()
    # 將日期轉換為你想要的格式
    date_key = event_start_time.replace('/', '').split(' ')[0]

    # 建立你想要的數據結構
    formatted_data = {
        date_key: {
            'starttime': event_start_time,
            'endtime': event_end_time,
            'appletable': appledata_json,
            'boxtable': boxdata_json
        }
    }

    # 將數據轉換為 JSON 格式
    formatted_data_json = json.dumps(formatted_data, ensure_ascii=False)
    
    print(formatted_data_json)
    return formatted_data

def save_apple_json_file():

    formatted_data = Format_ApplePrizeData()
    filename = f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\GoldAppleProbabilityTable.json'
    result = '未知錯誤'

    # 檢查文件是否存在
    if os.path.exists(filename):
        # 讀取現有的數據
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        # 檢查新的數據的 date_key 是否已經存在
        if list(formatted_data.keys())[0] in existing_data:
            print('Data already exists in the file.')
            result = 'Data already exists in the file.'
            return result
        # 如果 date_key 不存在，添加新的數據
        existing_data.update(formatted_data)
    else:
        # 如果文件不存在，創建一個新的數據
        existing_data = formatted_data
    
    # 將數據寫入文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False)
    print('Data saved to the file.')
    result = 'Data saved to the file.'
    return result


def save_fashionbox_json_file():

    formatted_data = Format_FashionBoxPrizeData()
    filename = f'C:\\Users\\User\\Desktop\DiscordBot\\TMSBug_v2\\Data\\FashionBoxProbabilityTable.json'
    result = '未知錯誤'

    # 檢查文件是否存在
    if os.path.exists(filename):
        # 讀取現有的數據
        with open(filename, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
        # 檢查新的數據的 date_key 是否已經存在
        if list(formatted_data.keys())[0] in existing_data:
            print('Data already exists in the file.')
            result = 'Data already exists in the file.'
            return result
        # 如果 date_key 不存在，添加新的數據
        existing_data.update(formatted_data)
    else:
        # 如果文件不存在，創建一個新的數據
        existing_data = formatted_data
    
    # 將數據寫入文件
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False)
    print('Data saved to the file.')
    result = 'Data saved to the file.'
    return result










