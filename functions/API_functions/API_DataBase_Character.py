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
                pass
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
            # 逐筆成功訊息會阻塞 event loop，改為靜默（批次工具自行統計）
            return True
            
    except Exception as e:
        print(f"Failed to save character data: {e}")
        return False

def get_all_existing_ocid_names() -> set:
    """一次撈出 Character_ocid.db 裡所有已存在的 character_id，用來過濾不必重查的名字。"""
    try:
        with sqlite3.connect(file_path) as conn:
            rows = conn.execute("SELECT character_id FROM character_ocid").fetchall()
        return {r[0] for r in rows}
    except Exception as e:
        print(f"Failed to load existing OCID names: {e}")
        return set()   # 撈失敗就回空集合 → 退化成全查，不會漏資料

def bulk_save_character_ocid_db(pairs) -> int:
    """批次寫入 (character_id, ocid)，單一 transaction，取代逐筆 connect+commit。

    pairs: List[Tuple[str, str]]  # [(name, ocid), ...]
    回傳實際寫入筆數。
    """
    if not pairs:
        return 0
    try:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(file_path) as conn:
            conn.executemany('''
                INSERT OR REPLACE INTO character_ocid
                (character_id, ocid, refresh_time)
                VALUES (?, ?, ?)
            ''', [(name, ocid, current_time) for name, ocid in pairs])
            conn.commit()
        print(f"Bulk saved {len(pairs)} OCID records")
        return len(pairs)
    except Exception as e:
        print(f"Failed to bulk save OCID data: {e}")
        return 0

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
            # Column 4: character_gender
            # Column 5: character_class
            # Column 6: character_class_level
            # Column 7: character_level
            # Column 8: character_exp
            # Column 9: character_exp_rate
            # Column 10: character_guild_name
            # Column 11: character_image
            # Column 12: character_date_create
            # Column 13: access_flag
            # Column 14: liberation_quest_clear
            # Column 15: query_date
            # Column 16: refresh_time
            # First, create table with basic structure if it doesn't exist
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
            
            # Check current table structure and add missing columns
            cursor.execute("PRAGMA table_info(character_basic_info)")
            columns = cursor.fetchall()
            existing_columns = [col[1] for col in columns]  # col[1] is column name
            
            # Define new columns to add (if they don't exist)
            new_columns = [
                ('character_gender', 'TEXT'),
                ('character_class_level', 'TEXT'),
                ('character_exp', 'INTEGER'),
                ('character_guild_name', 'TEXT'),
                ('character_date_create', 'TEXT'),
                ('access_flag', 'TEXT'),
                ('liberation_quest_clear', 'TEXT'),
                ('query_date', 'TEXT')
            ]
            
            # Add missing columns
            columns_added = False
            for column_name, column_type in new_columns:
                if column_name not in existing_columns:
                    try:
                        alter_sql = f"ALTER TABLE character_basic_info ADD COLUMN {column_name} {column_type}"
                        cursor.execute(alter_sql)
                        print(f"✓ Added new column: {column_name} {column_type}")
                        columns_added = True
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"Warning: Could not add column {column_name}: {e}")
            
            if columns_added:
                print("Database schema updated with new columns")
            
            conn.commit()
            
            return True
            
    except Exception as e:
        print(f"Character basic info database initialization failed: {e}")
        return False

def get_character_basic_info_db(ocid: str, cache_days: int = 7) -> Optional[dict]:
    """Get character basic info from database"""
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            
            # Query character basic info using Row factory for column name access
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ocid, character_name, world_name, character_gender, character_class, 
                       character_class_level, character_level, character_exp, character_exp_rate,
                       character_guild_name, character_image, character_date_create, 
                       access_flag, liberation_quest_clear, query_date, refresh_time
                FROM character_basic_info 
                WHERE ocid = ?
            ''', (ocid,))
            
            result = cursor.fetchone()
            
            if result:
                # Use column names instead of position-based unpacking
                ocid = result['ocid']
                character_name = result['character_name']
                world_name = result['world_name']
                character_gender = result['character_gender']
                character_class = result['character_class']
                character_class_level = result['character_class_level']
                character_level = result['character_level']
                character_exp = result['character_exp']
                character_exp_rate = result['character_exp_rate']
                character_guild_name = result['character_guild_name']
                character_image = result['character_image']
                character_date_create = result['character_date_create']
                access_flag = result['access_flag']
                liberation_quest_clear = result['liberation_quest_clear']
                query_date = result['query_date']
                refresh_time_str = result['refresh_time']
                
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
                            'character_gender': character_gender,
                            'character_class': character_class,
                            'character_class_level': character_class_level,
                            'character_level': character_level,
                            'character_exp': character_exp,
                            'character_exp_rate': character_exp_rate,
                            'character_guild_name': character_guild_name,
                            'character_image': character_image,
                            'character_date_create': character_date_create,
                            'access_flag': access_flag,
                            'liberation_quest_clear': liberation_quest_clear,
                            'date': query_date,
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
            character_name = character_basic_data.get('character_name') or ''
            world_name = character_basic_data.get('world_name') or ''
            character_gender = character_basic_data.get('character_gender') or ''
            character_class = character_basic_data.get('character_class') or ''
            character_class_level = character_basic_data.get('character_class_level') or ''
            character_level = character_basic_data.get('character_level') or 0
            character_exp = character_basic_data.get('character_exp') or 0
            try:
                character_exp_rate = float(character_basic_data.get('character_exp_rate') or 0.0)
            except (TypeError, ValueError):
                character_exp_rate = 0.0
            character_guild_name = character_basic_data.get('character_guild_name') or ''
            character_image = character_basic_data.get('character_image') or ''
            character_date_create = character_basic_data.get('character_date_create') or ''
            access_flag = character_basic_data.get('access_flag') or ''
            liberation_quest_clear = character_basic_data.get('liberation_quest_clear') or ''
            query_date = character_basic_data.get('date') or ''
            
            if not ocid:
                print("Error: Missing OCID information")
                return False
            # API 對已刪除角色會回 200 但欄位全為 None → 不寫入（避免 NOT NULL 違規）
            if not character_name:
                return False
            
            # Use INSERT OR REPLACE to handle insert or update
            cursor.execute('''
                INSERT OR REPLACE INTO character_basic_info 
                (ocid, character_name, world_name, character_gender, character_class, 
                 character_class_level, character_level, character_exp, character_exp_rate,
                 character_guild_name, character_image, character_date_create, 
                 access_flag, liberation_quest_clear, query_date, refresh_time) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ocid, character_name, world_name, character_gender, character_class, 
                  character_class_level, character_level, character_exp, character_exp_rate,
                  character_guild_name, character_image, character_date_create, 
                  access_flag, liberation_quest_clear, query_date, current_time))
            
            conn.commit()
            # print(f"Successfully saved character basic info: '{character_name}' (Lv.{character_level} {character_class}) -> OCID: {ocid}")
            return True
            
    except Exception as e:
        print(f"Failed to save character basic info: {e}")
        return False

def bulk_save_character_basic_info_db(records) -> int:
    """批次寫入角色基本資料，單一 transaction。

    records: [dict, ...]（每筆需含 'ocid'）
    回傳實際寫入筆數。取代逐筆 connect+commit（10 萬筆可省數分鐘）。
    """
    if not records:
        return 0
    init_character_basic_info_database()
    rows = []
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for d in records:
        ocid = d.get('ocid')
        # API 對已刪除角色會回 200 但所有欄位皆為 None → 無角色名者直接略過
        if not ocid or not d.get('character_name'):
            continue
        try:
            exp_rate = float(d.get('character_exp_rate') or 0.0)
        except (TypeError, ValueError):
            exp_rate = 0.0
        # NOT NULL 欄位需把 None 轉成預設值（.get 的預設值只在「缺鍵」時生效）
        rows.append((
            ocid, d.get('character_name') or '', d.get('world_name') or '',
            d.get('character_gender') or '', d.get('character_class') or '',
            d.get('character_class_level') or '', d.get('character_level') or 0,
            d.get('character_exp') or 0, exp_rate, d.get('character_guild_name') or '',
            d.get('character_image') or '', d.get('character_date_create') or '',
            d.get('access_flag') or '', d.get('liberation_quest_clear') or '',
            d.get('date') or '', now,
        ))
    if not rows:
        return 0
    sql = '''
        INSERT OR REPLACE INTO character_basic_info
        (ocid, character_name, world_name, character_gender, character_class,
         character_class_level, character_level, character_exp, character_exp_rate,
         character_guild_name, character_image, character_date_create,
         access_flag, liberation_quest_clear, query_date, refresh_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    try:
        with sqlite3.connect(character_basic_info_path) as conn:
            conn.executemany(sql, rows)
            conn.commit()
        return len(rows)
    except Exception as e:
        # 整批失敗時退回逐筆寫入，避免一筆壞資料拖垮整批
        print(f"Bulk save failed ({e})，改逐筆寫入…")
        written = 0
        try:
            with sqlite3.connect(character_basic_info_path) as conn:
                for r in rows:
                    try:
                        conn.execute(sql, r)
                        written += 1
                    except Exception:
                        pass
                conn.commit()
        except Exception as e2:
            print(f"Fallback save also failed: {e2}")
        return written


def init_dead_ocid_table():
    """已刪除/查無資料的 OCID 記錄表（避免每輪重複重試）"""
    with sqlite3.connect(file_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS dead_ocid (
                ocid TEXT PRIMARY KEY,
                checked_at TIMESTAMP NOT NULL
            )
        ''')
        conn.commit()


def mark_dead_ocids(ocids) -> int:
    """標記 OCID 為「查無角色」（API 回 200 但欄位全為 None）"""
    if not ocids:
        return 0
    try:
        init_dead_ocid_table()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect(file_path) as conn:
            conn.executemany('INSERT OR REPLACE INTO dead_ocid (ocid, checked_at) VALUES (?, ?)',
                             [(o, now) for o in ocids])
            conn.commit()
        return len(ocids)
    except Exception as e:
        print(f"Failed to mark dead OCIDs: {e}")
        return 0


def get_ocids_missing_basic_info(limit: int = 0, include_expired_days: int = 0) -> list:
    """找出「有 OCID 但缺少/過期角色詳細」的清單，未抓過的排在最前面。

    回傳 [(ocid, character_name), ...]
    include_expired_days > 0 時，同時納入超過該天數未更新者（排在未抓過的之後）。
    已標記為 dead_ocid（查無角色）者會被排除，除非 recheck_dead_days 內未複查過。
    """
    try:
        init_dead_ocid_table()
        with sqlite3.connect(file_path) as conn:   # file_path = Character_ocid.db
            conn.execute("ATTACH DATABASE ? AS b", (character_basic_info_path,))
            sql = '''
                SELECT o.ocid, o.character_id,
                       CASE WHEN b.ocid IS NULL THEN 0 ELSE 1 END AS has_info
                FROM character_ocid o
                LEFT JOIN b.character_basic_info b ON o.ocid = b.ocid
                LEFT JOIN dead_ocid d ON o.ocid = d.ocid
                WHERE d.ocid IS NULL AND (b.ocid IS NULL
            '''
            params = []
            if include_expired_days and include_expired_days > 0:
                sql += '''
                   OR b.refresh_time < datetime('now', 'localtime', ?)
                '''
                params.append(f'-{include_expired_days} days')
            sql += ') ORDER BY has_info ASC, b.refresh_time ASC'
            if limit and limit > 0:
                sql += ' LIMIT ?'
                params.append(limit)
            rows = conn.execute(sql, params).fetchall()
        return [(r[0], r[1]) for r in rows]
    except Exception as e:
        print(f"Failed to list OCIDs missing basic info: {e}")
        return []


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

def get_all_expired_character_lists(refresh_days: int = 9999, max_count: int = None,
                                    verbose: bool = False) -> dict:
    """掃描角色資料的新鮮度。

    max_count: 只取「最舊的 N 筆」過期資料（每日均分刷新用），None = 全部
    verbose:   逐筆列印（12萬筆時會嚴重拖慢，預設關閉）
    """
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
            conn.row_factory = sqlite3.Row
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
            
            for record in all_records:
                ocid = record['ocid']
                character_name = record['character_name']
                refresh_time_str = record['refresh_time']
                try:
                    # 檢查刷新時間
                    refresh_time = datetime.datetime.strptime(refresh_time_str, '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.datetime.now()
                    time_diff = current_time - refresh_time
                    
                    if time_diff.days < refresh_days:
                        if verbose:
                            print(f"✓ '{character_name}' is fresh ({time_diff.days} days old)")
                        result['fresh_records'] += 1
                        result['fresh_ocid_list'].append({
                            'ocid': ocid,
                            'character_name': character_name,
                            'days_old': time_diff.days
                        })
                    else:
                        # 資料過期
                        if verbose:
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
            
            # 每日均分：只取最舊的 N 筆（查詢已 ORDER BY refresh_time ASC，故清單本身由舊到新）
            total_expired = result['expired_records']
            if max_count and total_expired > max_count:
                result['expired_ocid_list'] = result['expired_ocid_list'][:max_count]
                result['capped_from'] = total_expired
                result['expired_records'] = max_count

            # 輸出統計結果
            print("\n=== 過期資料檢查結果 ===")
            print(f"總記錄數: {result['total_records']}")
            print(f"新鮮記錄: {result['fresh_records']}")
            if 'capped_from' in result:
                print(f"過期記錄: {total_expired}（本次只取最舊 {max_count} 筆）")
            else:
                print(f"過期記錄: {result['expired_records']}")
            print(f"錯誤記錄: {result['error_records']}")
            print("========================")

            return result
                
    except Exception as e:
        print(f"Error during expired check: {e}")
        result['error_records'] = result['total_records']
        return result

def delete_character_data_by_ocid(ocid: str) -> bool:
    """Delete character data by OCID from both databases
    
    Args:
        ocid: The OCID to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        # Delete from character_basic_info database
        with sqlite3.connect(character_basic_info_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM character_basic_info WHERE ocid = ?', (ocid,))
            conn.commit()
            basic_info_deleted = cursor.rowcount > 0
        
        # Delete from character_ocid database
        with sqlite3.connect(file_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM character_ocid WHERE ocid = ?', (ocid,))
            conn.commit()
            ocid_deleted = cursor.rowcount > 0
        
        if basic_info_deleted or ocid_deleted:
            print(f"✓ Successfully deleted OCID '{ocid}' from database")
            return True
        else:
            print(f"⚠ OCID '{ocid}' not found in database")
            return False
            
    except Exception as e:
        print(f"✗ Failed to delete OCID '{ocid}': {e}")
        return False



