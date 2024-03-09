import time
import pandas as pd
import csv

saveddate = ''
firstfile = False

def chat_log_save(SpeakCount, MessageChannel, MessageAuthor, MessageContent, MessageAttachments, MessageStickers):    
    global saveddate
    date = time.strftime('%Y%m%d', time.localtime(time.time()))

    if date != saveddate :
        saveddate = date
        firstfile = True
    else:
        firstfile = False

    ChatLog_output_path = 'C:\\Users\\User\\Desktop\\DiscordChatlog\\ChatLog'
    timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time()))

    if MessageContent == [] :
        MessageContent = '-'
    if MessageAttachments == [] :
        MessageAttachments = '-'
    if MessageStickers == [] :
        MessageStickers = '-'

    with open(f'{ChatLog_output_path}\\{date}_TMS新楓之谷_Chatlog.csv', 'a', newline='', encoding='utf-8') as csvfile:

        fieldnames = ['No.', 'Time', 'Chennal', 'Author', 'Content', 'Attachments', 'Stickers']        
        writer = csv.DictWriter(csvfile, fieldnames = fieldnames) # 將 dictionary 寫入 CSV 檔 
        if firstfile == True :
            firstfile = False
            writer.writeheader()

        # 寫入資料
        writer.writerow(
            {
            'No.': SpeakCount,
            'Time' : timestamp,
            'Chennal': MessageChannel,
            'Author': MessageAuthor,
            'Content' : MessageContent,
            'Attachments' :MessageAttachments,
            'Stickers' : MessageStickers        
            }
        ) 

def get_speak_count():
    date = time.strftime('%Y%m%d', time.localtime(time.time()))
    ChatLog_input_path = 'C:\\Users\\User\\Desktop\\DiscordChatlog\\ChatLog'

    try:
        Chat_log_df = pd.read_csv(f'{ChatLog_input_path}\\{date}_TMS新楓之谷_Chatlog.csv') 
        Chat_log_df['No.'] = pd.to_numeric(Chat_log_df['No.'], errors='coerce')
        speak_count = Chat_log_df['No.'].max()
    except FileNotFoundError:
        speak_count = 0
    
    return int(speak_count)


def chat_log_get():
    date = time.strftime('%Y%m%d', time.localtime(time.time()))

    ChatLog_input_path = 'C:\\Users\\User\\Desktop\\DiscordChatlog\\ChatLog'

    Chat_log_df = pd.read_csv(f'{ChatLog_input_path}\\{date}_TMS新楓之谷_Chatlog.csv') 

    return Chat_log_df