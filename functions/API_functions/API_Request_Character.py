import requests
import aiohttp
import asyncio
from typing import Optional
import datetime
import configparser
from functions.API_functions.API_DataBase_Character import (
    save_character_ocid_db, get_character_ocid_db, 
    save_character_basic_info_db, get_character_basic_info_with_fallback, get_all_expired_character_lists,
    delete_character_data_by_ocid
)


try:
    _TMSBot_CONF = configparser.ConfigParser()
    config_path = 'C:\\Users\\User\\Desktop\\DiscordBot\\Config\\TMSBug_v2_config.ini'
    _TMSBot_CONF.read(config_path, encoding="utf-8")

    api_key = _TMSBot_CONF["api"]["api_key"]
    
except FileNotFoundError:
    print("`config.ini` file missing.")

serveraddress = "maplestorytw"

def get_ocid_from_cache(character_name: str, cache_days: int = 7) -> Optional[str]:    
    try:
        db_result = get_character_ocid_db(character_name)
        
        if db_result:
            ocid, refresh_time_str = db_result
            
            try:
                refresh_time = datetime.datetime.strptime(refresh_time_str, '%Y-%m-%d %H:%M:%S')
                current_time = datetime.datetime.now()
                time_diff = current_time - refresh_time
                
                if time_diff.days < cache_days:
                    print(f"cache hit: '{character_name}' -> {ocid} ( {time_diff.days} days ago)")
                    return ocid
                else:
                    print(f"cache expired: ({time_diff.days} days ago)")
                    return None
                    
            except ValueError:
                print(f"time format error for '{character_name}': {refresh_time_str}")
                return None
        else:
            print(f"Cannot find '{character_name}'")
            return None
            
    except Exception as e:
        print(f"cache error: {e}")
        return None

def get_character_ocid(character_name: str) -> Optional[str]:
    
    # 1. First try to get from cache
    cached_ocid = get_ocid_from_cache(character_name)
    if cached_ocid:
        return cached_ocid
    
    # 2. Cache invalid, request from API
    api_ocid = request_character_ocid(character_name)
    if api_ocid:
        return api_ocid
    
    # 3. API failed, try to use expired cache data as fallback
    print(f"API request failed, trying to use expired cache...")
    fallback_ocid = get_ocid_from_cache(character_name, cache_days=365)  # Extend cache range to one year
    
    if fallback_ocid:
        print(f"use expired cache: {fallback_ocid}")
        return fallback_ocid

    print(f"cannot find '{character_name}' 的 OCID")
    return None

def request_character_ocid(character_name: str) -> Optional[str]:
       
    headers = {
        "x-nxopen-api-key": api_key
    }
    
    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/id?character_name={character_name}"
    
    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        ocid = data.get('ocid')
        
        if ocid:
            print(f"API request success: '{character_name}' -> {ocid}")
            
            # Save result to database
            print(f"save {character_name} ocid to database...")
            save_success = save_character_ocid_db(character_name, ocid)
            
            if not save_success:
                print(f"failed to save to cache")

            return ocid
        else:
            print(f"API response does not contain OCID")
            return None
        
    except Exception as e:
        print(f"API request failed: {e}")
        return None
    

def request_character_basic(ocid: str, use_cache: bool = False, date = None) -> Optional[dict]:
    
    # 1. If cache is enabled, try to get from cache first
    if use_cache:
        cached_data = get_character_basic_info_with_fallback(ocid)
        if cached_data:
            # Remove refresh_time field to maintain consistency with API response format
            api_format_data = {k: v for k, v in cached_data.items() if k != 'refresh_time'}
            return api_format_data
    
    # 2. Cache invalid or not using cache, request from API
    
    headers = {
        "x-nxopen-api-key": api_key
    }
    
    # Build URL based on whether date is specified
    if date:
        url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/basic?ocid={ocid}&date={date}"
        # print(f"requesting data for specific date: {date}")
    else:
        url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/basic?ocid={ocid}"
    
    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()
        
        character_basic_data = response.json()
        
        if character_basic_data:
            # Only save to database when no specific date is specified
            if not date:
                # Add OCID to data for saving
                character_basic_data_with_ocid = character_basic_data.copy()
                character_basic_data_with_ocid['ocid'] = ocid
                
                # Save to database (provides cache for other functions, like guild queries)
                save_success = save_character_basic_info_db(character_basic_data_with_ocid)
                
                if not save_success:
                    print(f"{ocid} save character_basic_info to db failed")
            
        return character_basic_data
        
    except Exception as e:
        print(f"Failed to request character basic info from API: {e}")               
        return None
    
def request_character_stat(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/stat?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_stat_data = response.json()
        return character_stat_data

    except Exception as e:
        print(f"error occurred while fetching character stat info: {e}")
        return None
    
def request_character_hexamatrix(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/hexamatrix?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_hexamatrix_data = response.json()
        return character_hexamatrix_data

    except Exception as e:
        print(f"error occurred while fetching character hexamatrix info: {e}")
        return None
    
def request_character_hexamatrix_stat(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/hexamatrix-stat?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_hexamatrix_stat_data = response.json()
        return character_hexamatrix_stat_data
    

    except Exception as e:
        print(f"error occurred while fetching character hexamatrix stat info: {e}")
        return None

def request_character_itemequipment(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/item-equipment?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_itemequipment_data = response.json()
        return character_itemequipment_data

    except Exception as e:
        print(f"error occurred while fetching character item equipment info: {e}")
        return None

def request_character_symbolequipment(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/symbol-equipment?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_symbolequipment_data = response.json()
        return character_symbolequipment_data

    except Exception as e:
        print(f"error occurred while fetching character symbol equipment info: {e}")
        return None
    
def request_character_cashitemequipment(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/cashitem-equipment?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_cashitemequipment_data = response.json()
        return character_cashitemequipment_data

    except Exception as e:
        print(f"error occurred while fetching character cash item equipment info: {e}")
        return None

def request_character_pet_equipment(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/pet-equipment?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_pet_equipment_data = response.json()
        return character_pet_equipment_data

    except Exception as e:
        print(f"error occurred while fetching character pet equipment info: {e}")
        return None
    

def request_character_beauty_equipment(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/beauty-equipment?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_beauty_equipment_data = response.json()
        return character_beauty_equipment_data

    except Exception as e:
        print(f"error occurred while fetching character beauty equipment info: {e}")
        return None
    
def request_character_ability(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/ability?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_ability_data = response.json()
        return character_ability_data

    except Exception as e:
        print(f"error occurred while fetching character ability info: {e}")
        return None

def request_character_hyper_stat(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/hyper-stat?ocid={ocid}"

    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()

        character_hyper_stat_data = response.json()
        return character_hyper_stat_data

    except Exception as e:
        print(f"error occurred while fetching character hyper stat info: {e}")
        return None





async def request_character_basic_async(session: aiohttp.ClientSession, ocid: str, semaphore: asyncio.Semaphore, date = None) -> Optional[dict]:
    """
    非同步版本的 request_character_basic，用於併行處理
    
    Args:
        session: aiohttp ClientSession
        ocid: 角色 OCID
        semaphore: 用於控制併發數量的信號量
        date: 可選的日期參數
    
    Returns:
        角色基本資料或 None
    """
    headers = {
        "x-nxopen-api-key": api_key
    }
    
    if date:
        url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/basic?ocid={ocid}&date={date}"
    else:
        url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/basic?ocid={ocid}"
    
    async with semaphore:  # 控制併發數量
        try:
            async with session.get(url_string, headers=headers) as response:
                response.raise_for_status()
                character_basic_data = await response.json()
                
                if character_basic_data and not date:
                    # 添加 OCID 並保存到資料庫
                    character_basic_data_with_ocid = character_basic_data.copy()
                    character_basic_data_with_ocid['ocid'] = ocid
                    save_character_basic_info_db(character_basic_data_with_ocid)
                
                return character_basic_data
                
        except Exception as e:
            print(f"Failed to request character basic info from API (async): {e}")
            return None


async def refresh_single_character_async(session: aiohttp.ClientSession, item: dict, semaphore: asyncio.Semaphore) -> dict:
    """
    非同步刷新單一角色資料
    
    Args:
        session: aiohttp ClientSession
        item: 包含 ocid 和 character_name 的字典
        semaphore: 用於控制併發數量的信號量
    
    Returns:
        處理結果字典
    """
    ocid = item['ocid']
    character_name = item['character_name']
    result = {
        'ocid': ocid,
        'character_name': character_name,
        'status': 'pending'
    }
    
    try:
        print(f"⟳ Refreshing '{character_name}'...")
        
        fresh_data = await request_character_basic_async(session, ocid, semaphore)
        
        if fresh_data:
            # 檢查是否所有欄位都是 null（無效資料）
            all_null = all(
                fresh_data.get(key) is None 
                for key in ['character_name', 'world_name', 'character_gender', 
                           'character_class', 'character_class_level', 'character_level',
                           'character_exp', 'character_exp_rate', 'character_guild_name',
                           'character_image', 'character_date_create', 'access_flag',
                           'liberation_quest_clear', 'date']
            )
            
            if all_null:
                print(f"⚠ Data for '{character_name}' (OCID: {ocid}) contains all null values, deleting...")
                if delete_character_data_by_ocid(ocid):
                    result['status'] = 'deleted'
                else:
                    result['status'] = 'delete_failed'
            else:
                print(f"✓ Successfully refreshed '{character_name}'")
                result['status'] = 'success'
        else:
            print(f"✗ Failed to fetch fresh data for '{character_name}' from API")
            result['status'] = 'failed'
            
    except Exception as e:
        print(f"✗ Error refreshing '{character_name}': {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


async def refresh_all_expired_character_data_async(refresh_days: int = 9999, max_concurrent: int = 10) -> dict:
    """
    非同步批次刷新過期角色資料（併行處理版本）
    
    Args:
        refresh_days: 資料過期門檻（天數），預設 9999 天
        max_concurrent: 最大併發請求數量，預設 10（避免超過 API 限制）

    Returns:
        包含處理結果統計的字典
    """
    # 取得過期 OCID 列表
    expired_check_result = get_all_expired_character_lists(refresh_days)
    
    # 準備結果統計
    result_stats = {
        'total_records': expired_check_result['total_records'],
        'fresh_records': expired_check_result['fresh_records'],
        'expired_records': expired_check_result['expired_records'],
        'error_records': expired_check_result['error_records'],
        'successfully_refreshed': 0,
        'failed_refreshes': 0,
        'deleted_invalid_records': 0
    }
    
    # 如果沒有過期資料，直接返回
    if not expired_check_result['expired_ocid_list']:
        print("No expired data needs to be refreshed")
        return result_stats
    
    print(f"\nStarting to refresh {len(expired_check_result['expired_ocid_list'])} expired records (concurrent mode, max={max_concurrent})...")
    
    # 創建信號量來控制併發數量
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 使用 aiohttp 進行非同步請求
    async with aiohttp.ClientSession() as session:
        # 創建所有任務
        tasks = [
            refresh_single_character_async(session, item, semaphore)
            for item in expired_check_result['expired_ocid_list']
        ]
        
        # 併行執行所有任務
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 統計結果
        for result in results:
            if isinstance(result, Exception):
                result_stats['failed_refreshes'] += 1
            elif isinstance(result, dict):
                status = result.get('status')
                if status == 'success':
                    result_stats['successfully_refreshed'] += 1
                elif status == 'deleted':
                    result_stats['deleted_invalid_records'] += 1
                elif status in ['failed', 'error', 'delete_failed']:
                    result_stats['failed_refreshes'] += 1
    
    # 輸出統計資訊
    print("\n=== Batch Refresh Results (Concurrent) ===")
    print(f"Total records: {result_stats['total_records']}")
    print(f"Fresh records: {result_stats['fresh_records']}")
    print(f"Expired records: {result_stats['expired_records']}")
    print(f"Successfully refreshed: {result_stats['successfully_refreshed']}")
    print(f"Failed refreshes: {result_stats['failed_refreshes']}")
    print(f"Deleted invalid records: {result_stats['deleted_invalid_records']}")
    print(f"Error records: {result_stats['error_records']}")
    print("==========================================")
    
    return result_stats


def refresh_all_expired_character_data(refresh_days: int = 9999, max_concurrent: int = 5, use_async: bool = True) -> dict:
    """
    批次刷新過期角色資料（支援同步/非同步模式）
    
    Args:
        refresh_days: 資料過期門檻（天數），預設 9999 天
        max_concurrent: 最大併發請求數量，預設 5（僅在非同步模式生效）
        use_async: 是否使用非同步併行處理，預設 True

    Returns:
        包含處理結果統計的字典
    """
    if use_async:
        # 使用非同步併行處理
        return asyncio.run(refresh_all_expired_character_data_async(refresh_days, max_concurrent))
    else:
        # 傳統的同步處理方式（保留作為後備選項）
        return _refresh_all_expired_character_data_sync(refresh_days)


def _refresh_all_expired_character_data_sync(refresh_days: int = 9999) -> dict:
    """
    同步版本的批次刷新（原始實作，保留作為後備）
    
    Args:
        refresh_days: 資料過期門檻（天數），預設 9999 天

    Returns:
        包含處理結果統計的字典
    """
    # Get expired OCID list
    expired_check_result = get_all_expired_character_lists(refresh_days)
    
    # Prepare result statistics
    result_stats = {
        'total_records': expired_check_result['total_records'],
        'fresh_records': expired_check_result['fresh_records'],
        'expired_records': expired_check_result['expired_records'],
        'error_records': expired_check_result['error_records'],
        'successfully_refreshed': 0,
        'failed_refreshes': 0,
        'deleted_invalid_records': 0
    }
    
    # If no expired data, return directly
    if not expired_check_result['expired_ocid_list']:
        print("No expired data needs to be refreshed")
        return result_stats
    
    print(f"\nStarting to refresh {len(expired_check_result['expired_ocid_list'])} expired records (sync mode)...")
    
    # Batch refresh expired character data
    for item in expired_check_result['expired_ocid_list']:
        ocid = item['ocid']
        character_name = item['character_name']
        
        try:
            print(f"⟳ Refreshing '{character_name}'...")
            
            # Use API to refresh data (function will automatically save)
            fresh_data = request_character_basic(ocid, use_cache=False)
            
            if fresh_data:
                # Check if all fields are null (invalid data)
                all_null = all(
                    fresh_data.get(key) is None 
                    for key in ['character_name', 'world_name', 'character_gender', 
                               'character_class', 'character_class_level', 'character_level',
                               'character_exp', 'character_exp_rate', 'character_guild_name',
                               'character_image', 'character_date_create', 'access_flag',
                               'liberation_quest_clear', 'date']
                )
                
                if all_null:
                    print(f"⚠ Data for '{character_name}' (OCID: {ocid}) contains all null values, deleting...")
                    if delete_character_data_by_ocid(ocid):
                        result_stats['deleted_invalid_records'] += 1
                    else:
                        result_stats['failed_refreshes'] += 1
                else:
                    print(f"✓ Successfully refreshed '{character_name}'")
                    result_stats['successfully_refreshed'] += 1
            else:
                print(f"✗ Failed to fetch fresh data for '{character_name}' from API")
                result_stats['failed_refreshes'] += 1
                
        except Exception as e:
            print(f"✗ Error refreshing '{character_name}': {e}")
            result_stats['failed_refreshes'] += 1
    
    # Output statistics
    print("\n=== Batch Refresh Results (Sync) ===")
    print(f"Total records: {result_stats['total_records']}")
    print(f"Fresh records: {result_stats['fresh_records']}")
    print(f"Expired records: {result_stats['expired_records']}")
    print(f"Successfully refreshed: {result_stats['successfully_refreshed']}")
    print(f"Failed refreshes: {result_stats['failed_refreshes']}")
    print(f"Deleted invalid records: {result_stats['deleted_invalid_records']}")
    print(f"Error records: {result_stats['error_records']}")
    print("=====================================")
    
    return result_stats

