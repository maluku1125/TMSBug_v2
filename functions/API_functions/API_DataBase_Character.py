import sqlite3
import datetime
from typing import Optional
import os

file_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Character_ocid.db'
character_basic_info_path = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\Ocid_CharacterBasicInfo.db'

def init_Character_Ocid_database():
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Connect to database
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            # Create table
            # Column 1: character_id
            # Column 2: ocid 
            # Column 3: refresh_time
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
        print(f"Database initialization failed: {e}")
        return False

def get_character_ocid_db(character_id: str) -> Optional[tuple]:

    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            # Query character data
            cursor.execute('''
                SELECT ocid, refresh_time 
                FROM character_ocid 
                WHERE character_id = ?
            ''', (character_id,))
            
            result = cursor.fetchone()
            
            if result:
                ocid, refresh_time = result
                return (ocid, refresh_time)
            else:
                print(f"Cannot find '{character_id}' data")
                return None
                
    except Exception as e:
        print(f"Database query failed: {e}")
        return None

def save_character_ocid_db(character_id: str, ocid: str) -> bool:
    try:
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Use INSERT OR REPLACE to handle insert or update
            cursor.execute('''
                INSERT OR REPLACE INTO character_ocid 
                (character_id, ocid, refresh_time) 
                VALUES (?, ?, ?)
            ''', (character_id, ocid, current_time))
            
            conn.commit()
            print(f"Successfully saved character data: '{character_id}' -> OCID: {ocid}, time: {current_time}")
            return True
            
    except Exception as e:
        print(f"Failed to save character data: {e}")
        return False

def init_character_basic_info_database():
    """Initialize character basic info database"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(character_basic_info_path), exist_ok=True)
        
        # Connect to database
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # Create table
            # Column 1: ocid (PRIMARY KEY)
            # Column 2: character_name
            # Column 3: world_name
            # Column 4: character_class
            # Column 5: character_level
            # Column 6: character_exp_rate
            # Column 7: character_image
            # Column 8: refresh_time
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_basic_info (
                    ocid TEXT PRIMARY KEY,
                    character_name TEXT NOT NULL,
                    world_name TEXT NOT NULL,
                    character_class TEXT NOT NULL,
                    character_level INTEGER NOT NULL,
                    character_exp_rate REAL NOT NULL,
                    character_image TEXT,
                    refresh_time TIMESTAMP NOT NULL
                )
            ''')
            
            conn.commit()
            print("Character basic info database initialized successfully")
            return True
            
    except Exception as e:
        print(f"Character basic info database initialization failed: {e}")
        return False

def get_character_basic_info_db(ocid: str, cache_days: int = 7) -> Optional[dict]:
    """Get character basic info from database"""
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # Query character basic info
            cursor.execute('''
                SELECT ocid, character_name, world_name, character_class, 
                       character_level, character_exp_rate, character_image, refresh_time
                FROM character_basic_info 
                WHERE ocid = ?
            ''', (ocid,))
            
            result = cursor.fetchone()
            
            if result:
                ocid, character_name, world_name, character_class, character_level, character_exp_rate, character_image, refresh_time_str = result
                
                # Check if data is expired
                try:
                    refresh_time = datetime.datetime.strptime(refresh_time_str, '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.datetime.now()
                    time_diff = current_time - refresh_time
                    
                    if time_diff.days < cache_days:
                        print(f"Retrieved character basic info from cache: '{character_name}' ({time_diff.days} days old)")
                        return {
                            'ocid': ocid,
                            'character_name': character_name,
                            'world_name': world_name,
                            'character_class': character_class,
                            'character_level': character_level,
                            'character_exp_rate': character_exp_rate,
                            'character_image': character_image,
                            'refresh_time': refresh_time_str
                        }
                    else:
                        print(f"Character basic info cache expired ({time_diff.days} days old)")
                        return None
                        
                except ValueError:
                    print(f"Time format error: {refresh_time_str}")
                    return None
            else:
                print(f"Cannot find character basic info for OCID '{ocid}'")
                return None
                
    except Exception as e:
        print(f"Failed to query character basic info: {e}")
        return None

def save_character_basic_info_db(character_basic_data: dict) -> bool:
    """Save character basic info to database"""
    try:
        # Ensure database is initialized
        init_character_basic_info_database()
        
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Extract required fields from input data
            ocid = character_basic_data.get('ocid')  # Assume ocid is provided externally
            character_name = character_basic_data.get('character_name', '')
            world_name = character_basic_data.get('world_name', '')
            character_class = character_basic_data.get('character_class', '')
            character_level = character_basic_data.get('character_level', 0)
            character_exp_rate = float(character_basic_data.get('character_exp_rate', 0.0))
            character_image = character_basic_data.get('character_image', '')
            
            if not ocid:
                print("Error: Missing OCID information")
                return False
            
            # Use INSERT OR REPLACE to handle insert or update
            cursor.execute('''
                INSERT OR REPLACE INTO character_basic_info 
                (ocid, character_name, world_name, character_class, 
                 character_level, character_exp_rate, character_image, refresh_time) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ocid, character_name, world_name, character_class, 
                  character_level, character_exp_rate, character_image, current_time))
            
            conn.commit()
            # print(f"Successfully saved character basic info: '{character_name}' (Lv.{character_level} {character_class}) -> OCID: {ocid}")
            return True
            
    except Exception as e:
        print(f"Failed to save character basic info: {e}")
        return False

def get_character_basic_info_with_fallback(ocid: str, cache_days: int = 7) -> Optional[dict]:
    """Get character basic info with fallback to expired cache"""
    # 1. Try to get valid cached data first
    cached_data = get_character_basic_info_db(ocid, cache_days)
    if cached_data:
        return cached_data
    
    # 2. If no valid cache, try using expired cache data as fallback
    print(f"Trying to use expired character basic info cache...")
    fallback_data = get_character_basic_info_db(ocid, cache_days=365)  # Extend cache range to one year
    
    if fallback_data:
        print(f"Using expired cache for character basic info: {fallback_data['character_name']}")
        return fallback_data
    
    print(f"Cannot find any character basic info cache for OCID '{ocid}'")
    return None

def get_all_expired_character_lists(refresh_days: int = 9999) -> dict:
    result = {
        'total_records': 0,
        'fresh_records': 0,
        'expired_records': 0,
        'error_records': 0,
        'expired_ocid_list': [],  # 過期的 OCID 清單
        'fresh_ocid_list': [],    # 新鮮的 OCID 清單
        'error_ocid_list': []     # 錯誤的 OCID 清單
    }
    
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # 查詢所有角色基本資訊
            cursor.execute('''
                SELECT ocid, character_name, refresh_time
                FROM character_basic_info
                ORDER BY refresh_time ASC
            ''')
            
            all_records = cursor.fetchall()
            result['total_records'] = len(all_records)
            
            if not all_records:
                print("No character data found in database")
                return result
            
            print(f"Found {len(all_records)} character records, checking for expired data...")
            
            for ocid, character_name, refresh_time_str in all_records:
                try:
                    # 檢查刷新時間
                    refresh_time = datetime.datetime.strptime(refresh_time_str, '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.datetime.now()
                    time_diff = current_time - refresh_time
                    
                    if time_diff.days < refresh_days:
                        print(f"✓ '{character_name}' is fresh ({time_diff.days} days old)")
                        result['fresh_records'] += 1
                        result['fresh_ocid_list'].append({
                            'ocid': ocid,
                            'character_name': character_name,
                            'days_old': time_diff.days
                        })
                    else:
                        # 資料過期
                        print(f"⏰ '{character_name}' is expired ({time_diff.days} days old)")
                        result['expired_records'] += 1
                        result['expired_ocid_list'].append({
                            'ocid': ocid,
                            'character_name': character_name,
                            'days_old': time_diff.days
                        })
                        
                except ValueError:
                    print(f"✗ Invalid time format for '{character_name}': {refresh_time_str}")
                    result['error_records'] += 1
                    result['error_ocid_list'].append({
                        'ocid': ocid,
                        'character_name': character_name,
                        'error': 'Invalid time format'
                    })
                except Exception as e:
                    print(f"✗ Error processing '{character_name}': {e}")
                    result['error_records'] += 1
                    result['error_ocid_list'].append({
                        'ocid': ocid,
                        'character_name': character_name,
                        'error': str(e)
                    })
            
            # 輸出統計結果
            print("\n=== 過期資料檢查結果 ===")
            print(f"總記錄數: {result['total_records']}")
            print(f"新鮮記錄: {result['fresh_records']}")
            print(f"過期記錄: {result['expired_records']}")
            print(f"錯誤記錄: {result['error_records']}")
            print("========================")
            
            return result
                
    except Exception as e:
        print(f"Error during expired check: {e}")
        result['error_records'] = result['total_records']
        return result




