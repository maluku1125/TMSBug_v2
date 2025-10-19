import sqlite3
import datetime
from typing import List, Dict, Optional

character_basic_info_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Ocid_CharacterBasicInfo.db'

def get_all_characters_level_exp_ranking(sort_by: str = 'level', ascending: bool = False) -> List[Dict]:
    """
    從 Ocid_CharacterBasicInfo 資料庫撈出所有玩家的等級和經驗，並進行排序
    
    Args:
        sort_by (str): 排序依據，可選 'level' (等級) 或 'exp' (經驗值)
        ascending (bool): True為升序排列，False為降序排列 (預設為降序，即最高等級在前)
    
    Returns:
        List[Dict]: 排序後的玩家資料列表
    """
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

def print_level_exp_ranking(limit: int = 10, sort_by: str = 'level', ascending: bool = False) -> None:
    """
    列印等級經驗排行榜
    
    Args:
        limit (int): 顯示前幾名，預設為前10名
        sort_by (str): 排序依據，可選 'level' (等級) 或 'exp' (經驗值)
        ascending (bool): True為升序排列，False為降序排列
    """
    ranking_data = get_all_characters_level_exp_ranking(sort_by=sort_by, ascending=ascending)
    
    if not ranking_data:
        print("沒有可顯示的排行榜資料")
        return
    
    # 限制顯示數量
    display_data = ranking_data[:limit] if limit > 0 else ranking_data
    
    print(f"\n===== 角色{'等級' if sort_by == 'level' else '經驗值'}排行榜 (前 {len(display_data)} 名) =====")
    print(f"{'排名':<4} {'角色名稱':<15} {'伺服器':<10} {'職業':<15} {'等級':<6} {'經驗%':<8} {'更新時間'}")
    print("-" * 80)
    
    for i, character in enumerate(display_data, 1):
        print(f"{i:<4} {character['character_name']:<15} {character['world_name']:<10} "
              f"{character['character_class']:<15} {character['character_level']:<6} "
              f"{character['character_exp_rate']:<8.2f} {character['refresh_time']}")
    
    print("=" * 80)

def get_character_rank_by_name(character_name: str, sort_by: str = 'level') -> Optional[Dict]:
    """
    根據角色名稱查詢該角色在排行榜中的位置
    
    Args:
        character_name (str): 角色名稱
        sort_by (str): 排序依據，可選 'level' 或 'exp'
    
    Returns:
        Dict: 包含角色資訊和排名的字典，如果找不到則返回 None
    """
    ranking_data = get_all_characters_level_exp_ranking(sort_by=sort_by, ascending=False)
    
    for i, character in enumerate(ranking_data, 1):
        if character['character_name'] == character_name:
            character['rank'] = i
            character['total_characters'] = len(ranking_data)
            print(f"角色 '{character_name}' 在{'等級' if sort_by == 'level' else '經驗值'}排行榜中排名第 {i} 位 (共 {len(ranking_data)} 名)")
            return character
    
    print(f"找不到角色 '{character_name}' 的資料")
    return None

def get_top_level_characters(world_name: str = None, character_class: str = None, limit: int = 10) -> List[Dict]:
    """
    根據條件篩選並獲取頂級角色
    
    Args:
        world_name (str): 指定伺服器名稱，None 表示所有伺服器
        character_class (str): 指定職業，None 表示所有職業
        limit (int): 限制回傳數量
        
    Returns:
        List[Dict]: 符合條件的頂級角色列表
    """
    all_characters = get_all_characters_level_exp_ranking(sort_by='level', ascending=False)
    
    # 根據條件篩選
    filtered_characters = []
    for character in all_characters:
        # 檢查伺服器條件
        if world_name and character['world_name'] != world_name:
            continue
            
        # 檢查職業條件
        if character_class and character['character_class'] != character_class:
            continue
            
        filtered_characters.append(character)
        
        # 達到限制數量就停止
        if len(filtered_characters) >= limit:
            break
    
    filter_info = []
    if world_name:
        filter_info.append(f"伺服器: {world_name}")
    if character_class:
        filter_info.append(f"職業: {character_class}")
    
    filter_str = " & ".join(filter_info) if filter_info else "全部"
    print(f"篩選條件: {filter_str}，共找到 {len(filtered_characters)} 個角色")
    
    return filtered_characters