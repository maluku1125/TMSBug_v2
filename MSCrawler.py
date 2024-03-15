from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import json


def Get_Website_data(page):
    # 創建Chrome瀏覽器選項
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 啟用無頭模式

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

    # 獲取文字資訊
    text_info = soup.find('div', {'class': 'text-info'})  # 假設文字在一個div標籤中的特定類別中
    if text_info:
        text = text_info.text
    else:
        text = "未找到文字資訊"

    # 找到所有表格
    tables = soup.find_all('table')  # 假設所有表格都是<table>標籤
    table_data = []

    for table in tables:
        # 進一步處理每個表格，例如提取表格中的數據
        table_data.append([])
        rows = table.find_all('tr')
        for row in rows:
            cell_data = [cell.text.strip() for cell in row.find_all('td')]
            table_data[-1].append(cell_data)

    # 關閉瀏覽器
    browser.quit()

    return text, table_data

def Print_Website_data_to_JSON(text, table_data, table_num, page):
    #print("文字資訊:")
    #print(text)
    # 創建一個空的字典，用於存儲轉換後的JSON數據
    result_json = {}

    previous_probability = None

    filtered_data = []
    skip_types = ['皇家美髮', '皇家整形']

    #print("\n所有表格資訊:")
    for i, table in enumerate(table_data):
        if table:
            if i == table_num: 
                if page == 8372: #皇家美容院
                    for row in table:                                               
                        if '皇家美髮' in row[0] or '皇家整形' in row[0]:  # 如果包含 '皇家美髮'，則只保留第二行
                            filtered_data.append([row[1], row[2]])
                        else:
                            filtered_data.append(row)
                    table2_data = filtered_data  
                else:
                    table2_data = table                  
            
        else:
            print("未找到表格資訊")
        print() 

    # 遍歷表格2的數據，從第二行開始，因為第一行是標題
    for row in table2_data[1:]:
        item_name = row[0]  # 道具名稱

        # 如果機率列不為空，則使用它；否則，使用前一個有效的機率值
        probability = row[1] if len(row) > 1 else previous_probability

        # 檢查機率是否為字符串且包含百分比字符，如果是，則去掉百分號並將機率轉換為浮點數
        if isinstance(probability, str) and '%' in probability:
            probability = float(probability.replace('%', '')) / 100.0
        
        if  type(probability) == float:
            probability = round(probability, 4) 
        else:
            probability = probability

        # 將道具名稱和機率添加到字典中
        result_json[item_name] = probability

        # 更新前一個有效的機率值
        previous_probability = probability

    # 轉換後的JSON
    print(json.dumps(result_json, indent=4, ensure_ascii=False))

page1 = 8373
table_num1 = 1
page2 = 8369
table_num2 = 1
page3 = 8369
table_num3 = 3


text1, table_data1 = Get_Website_data(page1)
text2, table_data2 = Get_Website_data(page2)
text3, table_data3 = Get_Website_data(page3)

Print_Website_data_to_JSON(text1, table_data1, table_num1, page1)
Print_Website_data_to_JSON(text2, table_data2, table_num2, page2)
Print_Website_data_to_JSON(text3, table_data3, table_num3, page3)







