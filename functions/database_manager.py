import sqlite3
import datetime
from typing import Optional, Dict, List

class GuildFunctionDB:
    def __init__(self, db_path: str = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\Guild_Function.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化資料庫並建立表格"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS guild_functions (
                    guild_id TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    mention_role TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def get_guild_config(self, guild_id: str) -> Optional[Dict]:
        """取得單一 Guild 的設定"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guild_id, channel_id, mention_role, updated_at 
                FROM guild_functions 
                WHERE guild_id = ?
            ''', (guild_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'ServerCheck_Channel': row[1],
                    'ServerCheck_mention': row[2],
                    'updated_at': row[3]
                }
            return None
    
    def get_all_guild_configs(self) -> Dict[str, Dict]:
        """取得所有 Guild 的設定，格式與原本 JSON 相容"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guild_id, channel_id, mention_role, updated_at 
                FROM guild_functions
            ''')
            
            result = {}
            for row in cursor.fetchall():
                guild_id = row[0]
                result[guild_id] = {
                    'ServerCheck_Channel': row[1],
                    'ServerCheck_mention': row[2],
                    'updated_at': row[3]
                }
            
            return result
    
    def set_guild_config(self, guild_id: str, channel_id: int, mention_role: str = "None"):
        """設定或更新 Guild 的設定"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO guild_functions 
                (guild_id, channel_id, mention_role, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, channel_id, mention_role, datetime.datetime.now()))
            conn.commit()
    
    def remove_guild(self, guild_id: str) -> bool:
        """移除 Guild 設定"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM guild_functions WHERE guild_id = ?', (guild_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def backup_to_json(self, backup_path: str):
        """將資料庫備份為 JSON 格式"""
        import json
        data = self.get_all_guild_configs()
        
        # 移除 updated_at 以保持與原格式相容
        for guild_id in data:
            if 'updated_at' in data[guild_id]:
                del data[guild_id]['updated_at']
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    
    def import_from_json(self, json_path: str):
        """從 JSON 檔案匯入資料"""
        import json
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for guild_id, config in data.items():
                channel_id = config.get('ServerCheck_Channel', 0)
                mention_role = config.get('ServerCheck_mention', 'None')
                self.set_guild_config(guild_id, channel_id, mention_role)
            
            return True
        except Exception as e:
            print(f"匯入 JSON 失敗: {e}")
            return False
    
    def get_guild_list(self) -> List[str]:
        """取得所有 Guild ID 列表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT guild_id FROM guild_functions')
            return [row[0] for row in cursor.fetchall()]


class UserDataDB:
    # 欄位名稱對應：slot 1=1本, 2~6=2本~6本
    SLOT_COLUMNS = {
        1: 'character_name',
        2: 'character_name_2',
        3: 'character_name_3',
        4: 'character_name_4',
        5: 'character_name_5',
        6: 'character_name_6',
    }
    SLOT_NAMES = {1: '1本', 2: '2本', 3: '3本', 4: '4本', 5: '5本', 6: '6本'}

    def __init__(self, db_path: str = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\Function\\Discord_UserData.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化資料庫並建立表格"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_data (
                    user_id TEXT PRIMARY KEY,
                    character_name TEXT,
                    character_name_2 TEXT,
                    character_name_3 TEXT,
                    character_name_4 TEXT,
                    character_name_5 TEXT,
                    character_name_6 TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # 遷移：為舊資料庫新增欄位（若欄位已存在則忽略）
            for i in range(2, 7):
                try:
                    cursor.execute(f'ALTER TABLE user_data ADD COLUMN character_name_{i} TEXT')
                except sqlite3.OperationalError:
                    pass

            # 遷移：移除舊 character_name 的 NOT NULL 約束
            cursor.execute("PRAGMA table_info(user_data)")
            columns_info = cursor.fetchall()
            for col_info in columns_info:
                # col_info: (cid, name, type, notnull, default, pk)
                if col_info[1] == 'character_name' and col_info[3] == 1:  # notnull == 1
                    # 需要重建表以移除 NOT NULL
                    cursor.execute('''
                        CREATE TABLE user_data_new (
                            user_id TEXT PRIMARY KEY,
                            character_name TEXT,
                            character_name_2 TEXT,
                            character_name_3 TEXT,
                            character_name_4 TEXT,
                            character_name_5 TEXT,
                            character_name_6 TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    cursor.execute('''
                        INSERT INTO user_data_new
                        SELECT user_id, character_name,
                               character_name_2, character_name_3,
                               character_name_4, character_name_5,
                               character_name_6, updated_at
                        FROM user_data
                    ''')
                    cursor.execute('DROP TABLE user_data')
                    cursor.execute('ALTER TABLE user_data_new RENAME TO user_data')
                    print("[UserDataDB] 已遷移：移除 character_name NOT NULL 約束")
                    break

            conn.commit()

    # ---------- 單一 slot 操作 ----------

    def get_user_character_slot(self, user_id: str, slot: int) -> Optional[str]:
        """取得使用者指定 slot 的角色ID"""
        col = self.SLOT_COLUMNS.get(slot)
        if not col:
            return None
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT {col} FROM user_data WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_user_character_slot(self, user_id: str, slot: int, character_name: str):
        """設定或更新使用者指定 slot 的角色ID"""
        col = self.SLOT_COLUMNS.get(slot)
        if not col:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM user_data WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                cursor.execute(
                    f'UPDATE user_data SET {col} = ?, updated_at = ? WHERE user_id = ?',
                    (character_name, datetime.datetime.now(), user_id)
                )
            else:
                cursor.execute(
                    f'INSERT INTO user_data (user_id, {col}, updated_at) VALUES (?, ?, ?)',
                    (user_id, character_name, datetime.datetime.now())
                )
            conn.commit()

    def remove_user_slot(self, user_id: str, slot: int) -> bool:
        """清除使用者指定 slot 的角色ID（設為 NULL）"""
        col = self.SLOT_COLUMNS.get(slot)
        if not col:
            return False
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'UPDATE user_data SET {col} = NULL, updated_at = ? WHERE user_id = ?',
                (datetime.datetime.now(), user_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_all_user_characters(self, user_id: str) -> Dict[int, Optional[str]]:
        """取得使用者所有 slot 的角色ID"""
        cols = ', '.join(self.SLOT_COLUMNS.values())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT {cols} FROM user_data WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if not row:
                return {i: None for i in range(1, 7)}
            return {i: row[i - 1] for i in range(1, 7)}

    # ---------- 向後相容方法（操作 slot 1 = 1本）----------

    def get_user_character(self, user_id: str) -> Optional[str]:
        """取得使用者的遊戲角色ID（1本，slot 1）"""
        return self.get_user_character_slot(user_id, 1)

    def set_user_character(self, user_id: str, character_name: str):
        """設定或更新使用者的遊戲角色ID（1本，slot 1）"""
        self.set_user_character_slot(user_id, 1, character_name)

    def remove_user(self, user_id: str) -> bool:
        """移除使用者整筆資料"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_data WHERE user_id = ?', (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_all_users(self) -> Dict[str, str]:
        """取得所有使用者的1本角色ID對應"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, character_name FROM user_data')
            return {row[0]: row[1] for row in cursor.fetchall()}