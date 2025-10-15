import sqlite3
import datetime
from typing import Optional
import os

file_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Guild_id.db'

def init_Guild_ID_database():
    try:
        # 確保目錄存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 連接資料庫
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            # 建立資料表
            # 第1欄：公會名稱_伺服器 (guild_name_server)
            # 第2欄：guildid
            # 第3欄：刷新時間 (refresh_time)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_id (
                    guild_name_server TEXT PRIMARY KEY,
                    guildid TEXT NOT NULL,
                    refresh_time TIMESTAMP NOT NULL
                )
            ''')
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"database initialization failed: {e}")
        return False

def get_guildid_db(guild_name_server: str) -> Optional[tuple]:

    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            # 查詢公會資料
            cursor.execute('''
                SELECT guildid, refresh_time 
                FROM guild_id 
                WHERE guild_name_server = ?
            ''', (guild_name_server,))
            
            result = cursor.fetchone()
            
            if result:
                guildid, refresh_time = result
                print(f"found '{guild_name_server}': GUILDID={guildid}, time={refresh_time}")
                return (guildid, refresh_time)
            else:
                print(f"cannot find '{guild_name_server}' data")
                return None
                
    except Exception as e:
        print(f"database query failed: {e}")
        return None


def save_guildid_db(guild_name_server: str, guildid: str) -> bool:
    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 使用 INSERT OR REPLACE 來處理新增或更新
            cursor.execute('''
                INSERT OR REPLACE INTO guild_id 
                (guild_name_server, guildid, refresh_time) 
                VALUES (?, ?, ?)
            ''', (guild_name_server, guildid, current_time))
            
            conn.commit()
            print(f"successfully saved guild data: '{guild_name_server}' -> GUILDID: {guildid}, time: {current_time}")
            return True
            
    except Exception as e:
        print(f"failed to save guild data: {e}")
        return False

init_Guild_ID_database()