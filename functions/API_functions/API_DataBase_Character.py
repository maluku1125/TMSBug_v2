import sqlite3
import datetime
from typing import Optional
import os

file_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Character_ocid.db'

def init_Character_Ocid_database():
    try:
        # 確保目錄存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 連接資料庫
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            # 建立資料表
            # 第1欄：角色ID (character_id)
            # 第2欄：ocid 
            # 第3欄：刷新時間 (refresh_time)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_ocid (
                    character_id TEXT PRIMARY KEY,
                    ocid TEXT NOT NULL,
                    refresh_time TIMESTAMP NOT NULL
                )
            ''')
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"database initialization failed: {e}")
        return False

def get_character_ocid_db(character_id: str) -> Optional[tuple]:

    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            # 查詢角色資料
            cursor.execute('''
                SELECT ocid, refresh_time 
                FROM character_ocid 
                WHERE character_id = ?
            ''', (character_id,))
            
            result = cursor.fetchone()
            
            if result:
                ocid, refresh_time = result
                print(f"found '{character_id}': OCID={ocid}, time={refresh_time}")
                return (ocid, refresh_time)
            else:
                print(f"cannot find '{character_id}' data")
                return None
                
    except Exception as e:
        print(f"database query failed: {e}")
        return None


def save_character_ocid_db(character_id: str, ocid: str) -> bool:
    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 使用 INSERT OR REPLACE 來處理新增或更新
            cursor.execute('''
                INSERT OR REPLACE INTO character_ocid 
                (character_id, ocid, refresh_time) 
                VALUES (?, ?, ?)
            ''', (character_id, ocid, current_time))
            
            conn.commit()
            print(f"successfully saved character data: '{character_id}' -> OCID: {ocid}, time: {current_time}")
            return True
            
    except Exception as e:
        print(f"failed to save character data: {e}")
        return False


