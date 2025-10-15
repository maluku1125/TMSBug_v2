import requests
from typing import Optional
import datetime
import configparser
from functions.API_functions.API_DataBase_Guild import save_guildid_db, get_guildid_db, init_Guild_ID_database

try:
    _TMSBot_CONF = configparser.ConfigParser()
    config_path = rf'C:\Users\User\Desktop\DiscordBot\Config\TMSBug_v2_config.ini'
    _TMSBot_CONF.read(config_path, encoding="utf-8")

    api_key = _TMSBot_CONF["api"]["api_key"]
    
except FileNotFoundError:
    print("`config.ini` file missing.")

# 初始化資料庫
init_Guild_ID_database()

def get_guildid_from_cache(guild_name_server: str, cache_days: int = 7) -> Optional[str]:    
    try:
        db_result = get_guildid_db(guild_name_server)
        
        if db_result:
            guildid, refresh_time_str = db_result
            
            try:
                refresh_time = datetime.datetime.strptime(refresh_time_str, '%Y-%m-%d %H:%M:%S')
                current_time = datetime.datetime.now()
                time_diff = current_time - refresh_time
                
                if time_diff.days < cache_days:
                    print(f"cache hit: '{guild_name_server}' -> {guildid} ( {time_diff.days} days ago)")
                    return guildid
                else:
                    print(f"cache expired: ({time_diff.days} days ago)")
                    return None
                    
            except ValueError:
                print(f"time format error for '{guild_name_server}': {refresh_time_str}")
                return None
        else:
            print(f"Cannot find '{guild_name_server}'")
            return None
            
    except Exception as e:
        print(f"cache error: {e}")
        return None

def get_guildid(guild_name: str, world_name: str) -> Optional[str]:
    print(f"guildid: '{guild_name}, {world_name}'")

    # Construct guild_name_server
    guild_name_server = f"{guild_name}_{world_name}"

    # 1. 先嘗試從快取獲取
    cached_guildid = get_guildid_from_cache(guild_name_server)
    if cached_guildid:
        return cached_guildid
    
    # 2. 快取無效，從 API 請求
    api_guildid = request_guildid(guild_name, world_name)
    if api_guildid:
        return api_guildid
    
    # 3. API 失敗，嘗試使用過期的快取資料作為備用
    print(f"API request failed, trying to use expired cache...")
    fallback_guildid = get_guildid_from_cache(guild_name_server, cache_days=365)  # 擴大快取範圍到一年
    
    if fallback_guildid:
        print(f"use expired cache: {fallback_guildid}")
        return fallback_guildid

    print(f"cannot find '{guild_name_server}' 的 GUILDID")
    return None

def request_guildid(guild_name: str, world_name: str) -> Optional[str]:
   
    headers = {
        "x-nxopen-api-key": api_key
    }
    
    url_string = f"https://open.api.nexon.com/maplestorytw/v1/guild/id?guild_name={guild_name}&world_name={world_name}"
    
    try:
        response = requests.get(url_string, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        guildid = data.get('oguild_id')
        
        if guildid:
            print(f"API request success: '{guild_name}, {world_name}' -> {guildid}")
            
            # 將結果儲存到資料庫
            print(f"save to database...")

            guild_name_server = f"{guild_name}_{world_name}"
            save_success = save_guildid_db(guild_name_server, guildid)

            if save_success:
                print(f"data has been saved to cache")
            else:
                print(f"failed to save to cache")

            return guildid
        else:
            print(f"API response does not contain GUILDID")
            return None
        
    except Exception as e:
        print(f"API request failed: {e}")
        return None
    

def request_guild_basic(oguildid: str) -> Optional[dict]:
    
    headers = {
        "x-nxopen-api-key": api_key
    }

    url_string = f"https://open.api.nexon.com/maplestorytw/v1/guild/basic?oguild_id={oguildid}"

    try:
        response = requests.get(url_string, headers=headers)
        
        response.raise_for_status()
                
        guild_basic_data = response.json()

        return guild_basic_data

    except Exception as e:
        print(f"error occurred while fetching guild basic info: {e}")
        return None


