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