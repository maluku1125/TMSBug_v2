import requests
from typing import Optional
import datetime
import configparser
from functions.API_functions.API_DataBase_Character import save_character_ocid_db, get_character_ocid_db

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
    print(f"OCID: '{character_name}'")
    
    # 1. 先嘗試從快取獲取
    cached_ocid = get_ocid_from_cache(character_name)
    if cached_ocid:
        return cached_ocid
    
    # 2. 快取無效，從 API 請求
    api_ocid = request_character_ocid(character_name)
    if api_ocid:
        return api_ocid
    
    # 3. API 失敗，嘗試使用過期的快取資料作為備用
    print(f"API request failed, trying to use expired cache...")
    fallback_ocid = get_ocid_from_cache(character_name, cache_days=365)  # 擴大快取範圍到一年
    
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
            
            # 將結果儲存到資料庫
            print(f"save to database...")
            save_success = save_character_ocid_db(character_name, ocid)
            
            if save_success:
                print(f"data has been saved to cache")
            else:
                print(f"failed to save to cache")

            return ocid
        else:
            print(f"API response does not contain OCID")
            return None
        
    except Exception as e:
        print(f"API request failed: {e}")
        return None
    

def request_character_basic(ocid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }
    
    url_string = f"https://open.api.nexon.com/{serveraddress}/v1/character/basic?ocid={ocid}"
    
    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()
        
        character_basic_data = response.json()
        return character_basic_data
        
    except Exception as e:
        print(f"error occurred while fetching character basic info: {e}")
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