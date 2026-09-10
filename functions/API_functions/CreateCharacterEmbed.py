import discord
from discord import app_commands
from discord.ext import commands

from tmsapi.request import get_character_ocid, request_character_basic, request_character_stat, request_character_hexamatrix, request_character_symbolequipment, request_character_hexamatrix_stat
from functions.API_functions.API_Request_union import request_user_union
# 30 日最高戰力需要寫入 Equip_Stat.db，而寫入權已收歸管線（階段 4）。
# 改呼叫 server.py 的內部 API；服務沒開時回 (None, None, 0)，這一行就不顯示。
from tmsapi.internal import sample_and_get_cp
import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from functions.Cogs.Slash_CreateSolErdaFragmentEmbed import Calculatefragment, common_cores_open
from Data.BotEmojiList import EmojiList


def apply_look_params(image_url: str, action: str = None, emotion: str = None, wmotion: str = None) -> str:
    """將角色動作參數 (action/emotion/wmotion) 套用到 Nexon 角色外型圖片 URL，保留原有參數(如 width/height)"""
    if not image_url:
        return image_url
    try:
        parts = urlparse(image_url)
        query = parse_qs(parts.query)
        if action:
            query['action'] = [action]
        if emotion:
            query['emotion'] = [emotion]
        if wmotion:
            query['wmotion'] = [wmotion]
        return urlunparse(parts._replace(query=urlencode(query, doseq=True)))
    except Exception:
        return image_url


def create_character_basic_embed(character_name: str, return_data: bool = False, action_params: dict = None):

    try:
        ocid = get_character_ocid(character_name)
        
        if not ocid:
            embed = discord.Embed(
                title="錯誤",
                description=f"無法找到角色 '{character_name}' 的資訊",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            return embed
    except Exception as e:
        embed = discord.Embed(
            title="錯誤",
            description=f"查詢角色時發生錯誤: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return embed
    
    try:
        character_basic_data = request_character_basic(ocid)  # Do not use cache, get data directly from API
        character_stat_data = request_character_stat(ocid)
        character_hexamatrix_data = request_character_hexamatrix(ocid)
        character_hexamatrix_stat_data = request_character_hexamatrix_stat(ocid)
        character_symbolequipment_data = request_character_symbolequipment(ocid)
        user_union_data = request_user_union(ocid)
        
    except Exception as e:
        embed = discord.Embed(
            title="錯誤",
            description=f"獲取角色資料時發生錯誤: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return embed
    
    # Handle seven days ago data separately, failure does not affect other functions
    character_basic_data_7days_ago = None
    try:
        seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        character_basic_data_7days_ago = request_character_basic(ocid, date=seven_days_ago)
    except Exception as e:
        print(f"獲取七天前資料失敗: {e}")
        character_basic_data_7days_ago = None 

    if not character_basic_data or not character_stat_data:
        # If unable to get basic character information, return error embed
        embed = discord.Embed(
            title="錯誤",
            description=f"無法獲取角色 '{character_name}' 的詳細資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return embed  

    # basic info
    character_info = []
    guild_name = character_basic_data.get('character_guild_name')

    # info
    character_info.append(f"伺服器　： {character_basic_data.get('world_name', '未知')}")
    character_info.append(f"公會　　： {guild_name if guild_name else '-'}")  

    
    # Format character class (limit to 9 characters and fix bracket issues)
    character_class = character_basic_data.get('character_class', '未知')
    character_class = character_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
    character_class = character_class.replace('大魔導士(火、毒)', '大魔導士（火、毒）')
    character_class = character_class[:9] if len(character_class) > 9 else character_class
    
    # Format experience rate as ab.c%
    exp_rate = character_basic_data.get('character_exp_rate', 0)
    
    # Safely handle exp_rate to ensure it's a number
    try:
        if exp_rate is None:
            exp_rate = 0.0
        else:
            exp_rate = float(exp_rate)
    except (ValueError, TypeError):
        exp_rate = 0.0
    
    exp_display = f"{exp_rate:.1f}%" if exp_rate > 0 else "0.0%"
    

    character_info.append(f"職業　　： {character_class}")
    character_info.append(f"等級　　： {character_basic_data.get('character_level', 0)}({exp_display})")
    
    # Calculate seven-day growth rate
    def calculate_seven_day_growth():
        if not character_basic_data_7days_ago:
            return "無資料"
        
        # Current data
        current_level = character_basic_data.get('character_level', 0)
        current_exp_rate = character_basic_data.get('character_exp_rate', 0)
        
        # Seven days ago data
        old_level = character_basic_data_7days_ago.get('character_level', 0)
        old_exp_rate = character_basic_data_7days_ago.get('character_exp_rate', 0)

        # Check if old_level is None (no valid data from 7 days ago)
        if old_level is None:
            return "無資料"

        # Safely handle level and experience values
        try:
            current_level = int(current_level) if current_level is not None else 0
            old_level = int(old_level) if old_level is not None else 0
            current_exp_rate = float(current_exp_rate) if current_exp_rate is not None else 0.0
            old_exp_rate = float(old_exp_rate) if old_exp_rate is not None else 0.0
        except (ValueError, TypeError):
            current_level = 0
            old_level = 0
            current_exp_rate = 0.0
            old_exp_rate = 0.0
  
        # Calculate total experience growth percentage
        if current_level == old_level:
            # Same level, only calculate experience difference
            growth_exp = current_exp_rate - old_exp_rate
    
        else:           
            remaining_old_exp = 100.0 - old_exp_rate
            level_difference = current_level - old_level - 1  # Number of levels upgraded in between      
            growth_exp = remaining_old_exp + (level_difference * 100.0) + current_exp_rate
            
        # Format growth rate display
        if growth_exp >= 0:
            if growth_exp > 100:
                # Over 100%, display as X(XX.XX%) format
                levels = int(growth_exp // 100)
                remaining_percent = growth_exp % 100
                growth_display = f"{levels}({remaining_percent:.2f}%)"
            else:
                # Within 100%, directly display percentage
                growth_display = f"{growth_exp:.2f}%"
        else:
            growth_display = "0.00%"
        
        return f"{growth_display}"
    
    seven_day_growth = calculate_seven_day_growth()
    character_info.append(f"七日成長： {seven_day_growth}")
    
    if user_union_data:
        union_level = user_union_data.get('union_level') or 0
        union_artifact_level = user_union_data.get('union_artifact_level') or 0
        # Only add union info if there's valid data
        if union_level and union_level > 0:
            character_info.append(f"聯盟戰地： {union_level:,}")
            character_info.append(f"神器等級： {union_artifact_level}")


    # final_stat to dict
    stat_dict = {}
    if character_stat_data and character_stat_data.get('final_stat'):
        for stat in character_stat_data['final_stat']:
            stat_name = stat.get('stat_name')
            stat_value = stat.get('stat_value')
            if stat_name and stat_value:
                stat_dict[stat_name] = stat_value
    

    def safe_str(value, default="0"):
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip()
        return str(value)
    
    # Helper function: Convert numbers to Chinese yi-wan format (omit last 4 digits)
    def format_chinese_number(number_str):
        try:
            num = int(number_str)
            num = num // 10000
            
            if num >= 10000:  # >=100 million
                yi = num // 10000
                wan = (num % 10000)
                if wan > 0:
                    return f"{yi}億{wan}萬"
                else:
                    return f"{yi}億"
            elif num > 0:  # >=10 thousand
                return f"{num}萬"
            else:
                return "0"
        except (ValueError, TypeError):
            return number_str
    
    # stat info 
    stat_info = []
    
    combat_power = safe_str(stat_dict.get('戰鬥力', '0'))
    starforce = safe_str(stat_dict.get('星力', '0'))
    arcaneforce = safe_str(stat_dict.get('神秘力量', '0'))
    authenticforce = safe_str(stat_dict.get('真實之力', '0'))
    maximumattstat = safe_str(stat_dict.get('最高屬性攻擊力', '0'))
    damage = safe_str(stat_dict.get('傷害', '0.0'))
    bossmonsterdamage = safe_str(stat_dict.get('BOSS怪物傷害', '0.0'))
    finaldamage = safe_str(stat_dict.get('最終傷害', '0.0'))
    critdamage = safe_str(stat_dict.get('爆擊傷害', '0.0'))
    ingroedefense = safe_str(stat_dict.get('無視防禦率', '0.0'))
    cooldown_sec = safe_str(stat_dict.get('冷卻時間減少(秒)', '0.0'))
    cooldown_percent = safe_str(stat_dict.get('冷卻時間減少(％)', '0.0'))
    cooldown_unaffected = safe_str(stat_dict.get('未套用冷卻時間', '0.0'))

    
    stat_info.append(f"戰鬥力　　： {format_chinese_number(combat_power)}")

    # 30 日最高戰力：/character 本來就打了 /character/stat，
    # 所以這次查詢會順便被記成一筆取樣，不額外消耗 API 額度。
    try:
        cp_max30, cp_max30_at, _cp_slots = sample_and_get_cp(
            ocid, character_name, character_stat_data,
            character_level=character_basic_data.get('character_level'),
            character_class=character_basic_data.get('character_class'))
        if cp_max30:
            when = ''
            if cp_max30_at:
                try:
                    d = (datetime.datetime.now().date()
                         - datetime.datetime.strptime(cp_max30_at, '%Y-%m-%d').date()).days
                    when = '（今日測得）' if d <= 0 else f'（{d}天前測得）'
                except (ValueError, TypeError):
                    when = ''
            stat_info.append(f"３０日最高： {format_chinese_number(str(cp_max30))}{when}")
    except Exception as e:
        print(f"取得 30 日最高戰力失敗: {e}")

    stat_info.append(f"屬性攻擊力： {int(maximumattstat):,}")
    stat_info.append(f"總傷害　　： {damage}%")
    stat_info.append(f"ＢＯＳＳ傷： {bossmonsterdamage}%")
    stat_info.append(f"爆擊傷害　： {critdamage}%")
    stat_info.append(f"最終傷害　： {finaldamage}%")
    stat_info.append(f"無視防禦　： {ingroedefense}%")
    stat_info.append(f"冷卻減免　： {cooldown_sec}秒｜{cooldown_percent}%")
    stat_info.append(f"無視冷卻　： {cooldown_unaffected}%")    
    stat_info.append(f"星力＆符文： {int(starforce)}｜{int(arcaneforce):,}｜{int(authenticforce):,}")
    

    # hexa info INFO
    hexa_dict = {}
    hexa_equipment = None
    
    # Safely check hexa core data
    
    if (character_hexamatrix_data and 
        character_hexamatrix_data.get('character_hexa_core_equipment') is not None):
        hexa_equipment = character_hexamatrix_data['character_hexa_core_equipment']
    
    
    if hexa_equipment:
        type_counters = {
            '技能核心': 0,
            '精通核心': 0,
            '強化核心': 0,
            '共用核心': 0
        }
        
        for core in hexa_equipment:
            core_type = core.get('hexa_core_type')
            core_level = core.get('hexa_core_level', 0)
            
            # Only process cores with level > 0
            if core_type in type_counters and core_level > 0:
                type_counters[core_type] += 1
                
                if core_type == '技能核心':
                    key = f"SkillCore{type_counters[core_type]}"
                elif core_type == '精通核心':
                    key = f"MasteryCore{type_counters[core_type]}"
                elif core_type == '強化核心':
                    key = f"EnhanceCore{type_counters[core_type]}"
                elif core_type == '共用核心':
                    key = f"CommonCore{type_counters[core_type]}"
                
                hexa_dict[key] = core_level

    # Extract core levels from hexa_dict for calculation
    SkillNodes1 = hexa_dict.get('SkillCore1', 0)
    SkillNodes2 = hexa_dict.get('SkillCore2', 0)
    MasteryNodes1 = hexa_dict.get('MasteryCore1', 0)
    MasteryNodes2 = hexa_dict.get('MasteryCore2', 0)
    MasteryNodes3 = hexa_dict.get('MasteryCore3', 0)
    MasteryNodes4 = hexa_dict.get('MasteryCore4', 0)
    BoostNode1 = hexa_dict.get('EnhanceCore1', 0)
    BoostNode2 = hexa_dict.get('EnhanceCore2', 0)
    BoostNode3 = hexa_dict.get('EnhanceCore3', 0)
    BoostNode4 = hexa_dict.get('EnhanceCore4', 0)
    # 共用核心2/共通核心3 未達開放日先隱藏（不列入完成度分母）
    c2_open, c3_open = common_cores_open()
    CommonNode1 = hexa_dict.get('CommonCore1', 0)
    CommonNode2 = hexa_dict.get('CommonCore2', 0) if c2_open else -1
    CommonNode3 = hexa_dict.get('CommonCore3', 0) if c3_open else -1

    # Calculate hexa core completion rate
    totalcount, maxfragment = Calculatefragment(
        SkillNodes1, SkillNodes2,
        MasteryNodes1, MasteryNodes2, MasteryNodes3, MasteryNodes4,
        BoostNode1, BoostNode2, BoostNode3, BoostNode4,
        CommonNode1,
        extrafragment=0,
        CommonNode2=CommonNode2, CommonNode3=CommonNode3
    )
    percentage = (totalcount / maxfragment * 100) if maxfragment > 0 else 0

    if hexa_dict:
        hexa_info = []
        
        # Collect core levels by type, only include cores with level > 0
        skill_cores = []
        mastery_cores = []
        enhance_cores = []
        common_cores = []
        
        for key, level in hexa_dict.items():
            if key.startswith('SkillCore') and level > 0:
                skill_cores.append(level)
            elif key.startswith('MasteryCore') and level > 0:
                mastery_cores.append(level)
            elif key.startswith('EnhanceCore') and level > 0:
                enhance_cores.append(level)
            elif key.startswith('CommonCore') and level > 0:
                common_cores.append(level)
        
        # Helper function to format core levels with spacing for alignment
        def format_core_level(level):
            return f"{level:2d}"
        
        # Display in standard format: 1 skill cores, 4 mastery cores, 4 enhance cores, 1 common core
        # Fill with 0 if insufficient
        
        # Skill cores: ensure 1 are displayed
        while len(skill_cores) < 2:
            skill_cores.append(0)
        skill_cores = skill_cores[:2]  # Only take first 2
        formatted_skill_cores = [format_core_level(level) for level in skill_cores]
        hexa_info.append(f"技能核心　： {' | '.join(formatted_skill_cores)}")
        
        # Mastery cores: ensure 4 are displayed
        while len(mastery_cores) < 4:
            mastery_cores.append(0)
        mastery_cores = mastery_cores[:4]  # Only take first 4
        formatted_mastery_cores = [format_core_level(level) for level in mastery_cores]
        hexa_info.append(f"精通核心　： {' | '.join(formatted_mastery_cores)}")
        
        # Enhance cores: ensure 4 are displayed
        while len(enhance_cores) < 4:
            enhance_cores.append(0)
        enhance_cores = enhance_cores[:4]  # Only take first 4
        formatted_enhance_cores = [format_core_level(level) for level in enhance_cores]
        hexa_info.append(f"強化核心　： {' | '.join(formatted_enhance_cores)}")
        
        # Common cores: 依開放狀態決定顯示數量（共用1固定，共用2/共通核心3 未開放先隱藏）
        common_slots = 1 + (1 if c2_open else 0) + (1 if c3_open else 0)
        while len(common_cores) < common_slots:
            common_cores.append(0)
        common_cores = common_cores[:common_slots]
        formatted_common_cores = [format_core_level(level) for level in common_cores]
        hexa_info.append(f"共用核心　： {' | '.join(formatted_common_cores)}")

    # Process hexa-stat information
    hexa_stat_info = []
    try:
        if character_hexamatrix_stat_data:
            # Process hexa-stat cores (preset 1, 2, 3)
            for i in range(1, 4):
                preset_key = f'preset_hexa_stat_core_{i}' if i > 1 else 'preset_hexa_stat_core'
                core_array = character_hexamatrix_stat_data.get(preset_key, [])
                
                # Each preset contains an array of cores (slot_id 0 and 1)
                slot_0_data = None
                slot_1_data = None
                
                for core_data in core_array:
                    if core_data.get('slot_id') == '0':
                        slot_0_data = core_data
                    elif core_data.get('slot_id') == '1':
                        slot_1_data = core_data
                
                # Helper function to format numbers with spacing for alignment
                def format_stat_with_spacing(main, sub1, sub2):
                    main_str = f"{main:2d}"
                    sub1_str = f"{sub1:2d}" 
                    sub2_str = f"{sub2:2d}"
                    
                    return f"{main_str}/{sub1_str}/{sub2_str}"
                
                # Format slot 0 (left side)
                if slot_0_data:
                    main_0 = slot_0_data.get('main_stat_level', 0)
                    sub1_0 = slot_0_data.get('sub_stat_level_1', 0)
                    sub2_0 = slot_0_data.get('sub_stat_level_2', 0)
                else:
                    main_0, sub1_0, sub2_0 = 0, 0, 0
                
                format_0 = format_stat_with_spacing(main_0, sub1_0, sub2_0)
                
                # Format slot 1 (right side)  
                if slot_1_data:
                    main_1 = slot_1_data.get('main_stat_level', 0)
                    sub1_1 = slot_1_data.get('sub_stat_level_1', 0)
                    sub2_1 = slot_1_data.get('sub_stat_level_2', 0)
                else:
                    main_1, sub1_1, sub2_1 = 0, 0, 0
                
                format_1 = format_stat_with_spacing(main_1, sub1_1, sub2_1)
                
                equipped_preset_key = f'character_hexa_stat_core_{i}' if i > 1 else 'character_hexa_stat_core'
                equipped_cores = character_hexamatrix_stat_data.get(equipped_preset_key, [])
                
                # Check which slot is currently equipped
                equipped_slot_id = None
                if equipped_cores:
                    # Usually there's only one equipped core, get its slot_id
                    equipped_slot_id = equipped_cores[0].get('slot_id')
                
                # Create display string with status indicators
                if equipped_slot_id == '0':
                    left_indicator = "✅"
                    right_indicator = "❌"
                elif equipped_slot_id == '1':
                    left_indicator = "❌"
                    right_indicator = "✅"
                else:
                    left_indicator = "❌"
                    right_indicator = "❌"
                
                # Convert number to full-width for better alignment
                full_width_number = {'1': '１', '2': '２', '3': '３'}.get(str(i), str(i))
                hexa_stat_info.append(f"屬性核心{full_width_number}：{format_0}{left_indicator}|{right_indicator}{format_1}")
    except Exception as e:
        hexa_stat_info = []


    # symbole
    symbol_info = []
    if character_symbolequipment_data and character_symbolequipment_data.get('symbol'):
        symbols = character_symbolequipment_data.get('symbol', [])
        
        arcane_symbols = []  # Arcane symbols
        sacred_symbols = []  # Sacred symbols  
        luxury_symbols = []  # Luxury sacred symbols
        
        for symbol in symbols:
            symbol_name = symbol.get('symbol_name', '未知符文')
            symbol_level = symbol.get('symbol_level', 0)
            
            if '祕法符文：' in symbol_name:
                arcane_symbols.append(str(symbol_level))
            elif '豪華真實符文：' in symbol_name:
                luxury_symbols.append(str(symbol_level))    
            elif '真實符文：' in symbol_name:
                sacred_symbols.append(str(symbol_level))            
            else:
                sacred_symbols.append(str(symbol_level))
        
        if arcane_symbols:
            symbol_info.append(f"ARC ：{' | '.join(arcane_symbols)}")
        if sacred_symbols:
            symbol_info.append(f"AUT ：{' | '.join(sacred_symbols)}")
        if luxury_symbols:
            symbol_info.append(f"GAUT：{' | '.join(luxury_symbols)}")


    # Create embed
    embed = discord.Embed(
        title=f"{character_basic_data.get('character_name', '未知角色')}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    # character_image（套用使用者設定的動作/表情/武器動作）
    if character_basic_data.get('character_image'):
        image_url = character_basic_data['character_image']
        if action_params:
            image_url = apply_look_params(
                image_url,
                action_params.get('action'),
                action_params.get('emotion'),
                action_params.get('wmotion'),
            )
            # 寫回 dict，讓裝備頁等共用此資料的地方也套用同一姿勢
            character_basic_data['character_image'] = image_url
        embed.set_thumbnail(url=image_url)
             
    # access_flag：官方 2024-06-07 加進 /character/basic 的欄位，語意是
    # 「最近 7 天內是否登入過」。回傳是字串 'true'/'false'；查無或舊資料
    # 可能是 None，那種情況不標記 —— 寧可少說也不要說錯。
    _access = character_basic_data.get('access_flag')
    if _access is None or str(_access).strip() == '':
        _access_tag = ''
    elif str(_access).lower() == 'true':
        _access_tag = ' (🟢7日內登入)'
    else:
        _access_tag = ' (🔴7日未登入)'

    embed.add_field(
        name=f"基本資訊{_access_tag}",
        value=f"```ml\n{'\n'.join(character_info)}```",
        inline=False
    )
    embed.add_field(
        name="機體資訊",
        value=f"```ml\n{'\n'.join(stat_info)}```",
        inline=False
    )
    
    # Display hexa core information, show standard format even if no valid cores
    if hexa_equipment is not None:  # Display as long as there is core equipment data
        if not hexa_info:  # If no valid cores, create default format
            common_default = ' | '.join(['  0'] * (1 + (1 if c2_open else 0) + (1 if c3_open else 0)))
            hexa_info = [
                "技能核心　：  0 |  0",
                "精通核心　：  0 |  0 |  0 |  0",
                "強化核心　：  0 |  0 |  0 |  0",
                f"共用核心　： {common_default}"
            ]
        
        embed.add_field(
            name=f"{EmojiList.get('hexamatrix', '')}六轉核心 ({percentage:.2f}%)",
            value=f"```ml\n{'\n'.join(hexa_info)}\n{'\n'.join(hexa_stat_info)}```",
            inline=False
        )
       
    if symbol_info:
        embed.add_field(
            name=f"{EmojiList.get('Aut0', '')}符文{EmojiList.get('Arc0', '')}",
            value=f"```ml\n{'\n'.join(symbol_info)}```",
            inline=False
        )

    # create_date
    # 預設純虛線，避免無創建日期資料時 character_create_date 未定義導致 NameError
    character_create_date = f"{'-'*19}　　　　　　　　　　{'-'*19}"
    create_date = character_basic_data.get('character_date_create')
    if create_date:
        try:
            date_obj = datetime.datetime.fromisoformat(create_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%Y-%m-%d')
            
            # Calculate day difference from today
            today = datetime.datetime.now()
            # Only compare date part, ignore time
            create_date_only = date_obj.date()
            today_date_only = today.date()
            days_diff = (today_date_only - create_date_only).days
            
            # Check if it's the character's birthday (same month and day)
            is_birthday = (create_date_only.month == today_date_only.month and 
                          create_date_only.day == today_date_only.day)
            
            if is_birthday:
                character_create_date = f"{'-'*19}創建日期: {formatted_date} ({days_diff}天) 🎉生日快樂！🎂{'-'*19}"
            else:
                character_create_date = f"{'-'*19}創建日期: {formatted_date} ({days_diff}天){'-'*19}"
        except:
            character_create_date = f"{'-'*19}創建日期: {create_date}{'-'*19}"

    embed.set_footer(
        text=f"{character_create_date}"
    )
    
    if return_data:
        return {
            "embed": embed,
            "character_basic_data": character_basic_data
        }
    else:
        return embed



