import sqlite3
import datetime
from typing import List, Dict, Optional

character_basic_info_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Ocid_CharacterBasicInfo.db'

def get_all_characters_level_exp_ranking(sort_by: str = 'level', ascending: bool = False) -> List[Dict]:
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # 查詢所有角色的基本資訊
            cursor.execute('''
                SELECT ocid, character_name, world_name, character_class, 
                       character_level, character_exp_rate, character_image, refresh_time
                FROM character_basic_info
            ''')
            
            all_records = cursor.fetchall()
            
            if not all_records:
                print("資料庫中沒有找到任何角色資料")
                return []
            
            # 將查詢結果轉換為字典列表
            characters_data = []
            for record in all_records:
                ocid, character_name, world_name, character_class, character_level, character_exp_rate, character_image, refresh_time = record
                
                character_info = {
                    'ocid': ocid,
                    'character_name': character_name,
                    'world_name': world_name,
                    'character_class': character_class,
                    'character_level': character_level,
                    'character_exp_rate': character_exp_rate,
                    'character_image': character_image,
                    'refresh_time': refresh_time
                }
                characters_data.append(character_info)
            
            # 根據指定條件排序
            if sort_by == 'level':
                # 先按等級排序，等級相同時按經驗值排序
                characters_data.sort(
                    key=lambda x: (x['character_level'], x['character_exp_rate']), 
                    reverse=not ascending
                )
                print(f"已按等級{'升序' if ascending else '降序'}排序 (等級相同時按經驗值排序)")
            elif sort_by == 'exp':
                # 按經驗值排序
                characters_data.sort(
                    key=lambda x: x['character_exp_rate'], 
                    reverse=not ascending
                )
                print(f"已按經驗值{'升序' if ascending else '降序'}排序")
            else:
                print(f"警告: 不支援的排序依據 '{sort_by}'，使用預設等級排序")
                characters_data.sort(
                    key=lambda x: (x['character_level'], x['character_exp_rate']), 
                    reverse=not ascending
                )
            
            print(f"成功撈取並排序 {len(characters_data)} 個角色資料")
            return characters_data
            
    except Exception as e:
        print(f"撈取角色等級經驗排序時發生錯誤: {e}")
        return []

