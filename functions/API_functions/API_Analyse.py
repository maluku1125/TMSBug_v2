import sqlite3
import datetime
from typing import List, Dict, Optional

character_basic_info_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Ocid_CharacterBasicInfo.db'

def get_class_distribution_analysis(world_name: str = None) -> Dict:
    """
    Analyze class distribution statistics
    
    Args:
        world_name (str, optional): Specified world name, if None analyze all worlds
        
    Returns:
        Dict: Dictionary containing class analysis statistics
    """
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # First get total character count (only count class levels 4/5/6)
            if world_name:
                # Get total character count for this world (filter by class level)
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM character_basic_info 
                    WHERE world_name = ? AND character_class_level IN (4, 5, 6)
                ''', (world_name,))
                total_count_result = cursor.fetchone()
                
                # Get class statistics for this world (filter by class level)
                cursor.execute('''
                    SELECT character_class, COUNT(*) as count
                    FROM character_basic_info
                    WHERE world_name = ? AND character_class_level IN (4, 5, 6)
                    GROUP BY character_class
                    ORDER BY count DESC
                ''', (world_name,))
                class_records = cursor.fetchall()
            else:
                # Get total character count (filter by class level)
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM character_basic_info
                    WHERE character_class_level IN (4, 5, 6)
                ''')
                total_count_result = cursor.fetchone()
                
                # Get class statistics for all worlds (filter by class level)
                cursor.execute('''
                    SELECT character_class, COUNT(*) as count
                    FROM character_basic_info
                    WHERE character_class_level IN (4, 5, 6)
                    GROUP BY character_class
                    ORDER BY count DESC
                ''')
                class_records = cursor.fetchall()
            
            if not class_records:
                print(f"資料庫中沒有找到{'世界 ' + world_name if world_name else '任何'}的角色資料")
                return {
                    'success': False,
                    'message': f"沒有找到{'世界 ' + world_name if world_name else '任何'}的角色資料",
                    'data': [],
                    'total_characters': 0,
                    'world_name': world_name
                }
            
            if not total_count_result:
                print("無法獲取總角色數")
                return {
                    'success': False,
                    'message': "無法獲取總角色數",
                    'data': [],
                    'total_characters': 0,
                    'world_name': world_name
                }
            
            total_characters = total_count_result[0]
            
            # Process class statistics data
            class_stats = []
            for record in class_records:
                character_class, count = record
                percentage = (count / total_characters) * 100
                
                # Handle parentheses issues
                character_class = character_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
                character_class = character_class.replace('大魔導士(火、毒)', '大魔導士（火、毒）')
                
                class_stats.append({
                    'class_name': character_class,
                    'count': count,
                    'percentage': percentage
                })
            
            print(f"成功分析{'世界 ' + world_name if world_name else '全部世界'}的職業分布: {len(class_stats)} 個職業, 總計 {total_characters} 個角色")
            
            return {
                'success': True,
                'message': '職業分析成功',
                'data': class_stats,
                'total_characters': total_characters,
                'world_name': world_name
            }
            
    except Exception as e:
        error_message = f"分析職業分布時發生錯誤: {e}"
        print(error_message)
        return {
            'success': False,
            'message': error_message,
            'data': [],
            'total_characters': 0,
            'world_name': world_name
        }

def get_world_distribution_analysis() -> Dict:
    """
    Analyze world distribution statistics
    
    Returns:
        Dict: Dictionary containing world analysis statistics
    """
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # Query character count by world
            cursor.execute('''
                SELECT world_name, COUNT(*) as count
                FROM character_basic_info
                GROUP BY world_name
                ORDER BY count DESC
            ''')
            
            world_records = cursor.fetchall()
            
            # Get total character count
            cursor.execute('''
                SELECT COUNT(*) 
                FROM character_basic_info
            ''')
            
            total_count_result = cursor.fetchone()
            
            if not world_records or not total_count_result:
                print("資料庫中沒有找到任何世界資料")
                return {
                    'success': False,
                    'message': "沒有找到任何世界資料",
                    'data': [],
                    'total_characters': 0
                }
            
            total_characters = total_count_result[0]
            
            # Process world statistics data
            world_stats = []
            for record in world_records:
                world_name, count = record
                percentage = (count / total_characters) * 100
                
                world_stats.append({
                    'world_name': world_name,
                    'count': count,
                    'percentage': percentage
                })
            
            print(f"成功分析世界分布: {len(world_stats)} 個世界, 總計 {total_characters} 個角色")
            
            return {
                'success': True,
                'message': '世界分析成功',
                'data': world_stats,
                'total_characters': total_characters
            }
            
    except Exception as e:
        error_message = f"分析世界分布時發生錯誤: {e}"
        print(error_message)
        return {
            'success': False,
            'message': error_message,
            'data': [],
            'total_characters': 0
        }

def get_level_distribution_analysis(world_name: str = None) -> Dict:
    """
    Analyze level distribution statistics
    
    Args:
        world_name (str, optional): Specified world name, if None analyze all worlds
        
    Returns:
        Dict: Dictionary containing level analysis statistics
    """
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # Use same level range structure as guild embed
            level_ranges = [
                (300, 999, "300🏆"),
                (295, 299, "295⬆️"),
                (290, 294, "290⬆️"),
                (285, 289, "285⬆️"),
                (280, 284, "280⬆️"),
                (275, 279, "275⬆️"),
                (270, 274, "270⬆️"),
                (265, 269, "265⬆️"),
                (260, 264, "260⬆️"),
                (1, 259, "260⬇️")
            ]
            
            # Build query based on whether world is specified
            level_stats = []
            total_characters = 0
            
            for min_level, max_level, range_name in level_ranges:
                if world_name:
                    cursor.execute('''
                        SELECT COUNT(*) 
                        FROM character_basic_info 
                        WHERE world_name = ? AND character_level >= ? AND character_level <= ? 
                        AND character_class_level IN (4, 5, 6)
                    ''', (world_name, min_level, max_level))
                else:
                    cursor.execute('''
                        SELECT COUNT(*) 
                        FROM character_basic_info 
                        WHERE character_level >= ? AND character_level <= ? 
                        AND character_class_level IN (4, 5, 6)
                    ''', (min_level, max_level))
                
                count_result = cursor.fetchone()
                count = count_result[0] if count_result else 0
                total_characters += count
                
                level_stats.append({
                    'range_name': range_name,
                    'min_level': min_level,
                    'max_level': max_level,
                    'count': count,
                    'percentage': 0  # Calculate later
                })
            
            # Calculate percentages
            for stat in level_stats:
                if total_characters > 0:
                    stat['percentage'] = (stat['count'] / total_characters) * 100
            
            # Sort by level order (high to low: 300 -> 295 -> 290...)
            level_stats.sort(key=lambda x: x['min_level'], reverse=True)
            
            print(f"成功分析{'世界 ' + world_name if world_name else '全部世界'}的等級分布: 總計 {total_characters} 個角色")
            
            return {
                'success': True,
                'message': '等級分析成功',
                'data': level_stats,
                'total_characters': total_characters,
                'world_name': world_name
            }
            
    except Exception as e:
        error_message = f"分析等級分布時發生錯誤: {e}"
        print(error_message)
        return {
            'success': False,
            'message': error_message,
            'data': [],
            'total_characters': 0,
            'world_name': world_name
        }
