import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Character import get_character_ocid, request_character_basic, request_character_stat, request_character_hexamatrix, request_character_symbolequipment, request_character_hexamatrix_stat
from functions.API_functions.API_Request_union import request_user_union
import datetime
from functions.Cogs.Slash_CreateSolErdaFragmentEmbed import Calculatefragment


def create_character_basic_embed(character_name: str, return_data: bool = False):

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
        character_basic_data = request_character_basic(ocid, use_cache=False)  # 不使用快取，直接從 API 獲取
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

    if not character_basic_data or not character_stat_data:
        # 如果無法獲取基本角色資訊，返回錯誤 embed
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
    
    # 安全處理 exp_rate，確保它是數字
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

    if user_union_data:
        union_level = user_union_data.get('union_level', 0)
        union_artifact_level = user_union_data.get('union_artifact_level', 0)
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
    
    print(222)

    def safe_str(value, default="0"):
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip()
        return str(value)
    
    # 輔助函數：將數字轉換為中文億萬格式（省略最後4位數）
    def format_chinese_number(number_str):
        try:
            num = int(number_str)
            num = num // 10000
            
            if num >= 10000:  # >=1億
                yi = num // 10000
                wan = (num % 10000)
                if wan > 0:
                    return f"{yi}億{wan}萬"
                else:
                    return f"{yi}億"
            elif num > 0:  # >=0萬
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
    
    # 安全檢查六轉核心資料
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
            
            if core_type in type_counters:
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

    # 從 hexa_dict 提取各核心等級用於計算
    SkillNodes1 = hexa_dict.get('SkillCore1', 0)
    MasteryNodes1 = hexa_dict.get('MasteryCore1', 0)
    MasteryNodes2 = hexa_dict.get('MasteryCore2', 0)
    MasteryNodes3 = hexa_dict.get('MasteryCore3', 0)
    MasteryNodes4 = hexa_dict.get('MasteryCore4', 0)
    BoostNode1 = hexa_dict.get('EnhanceCore1', 0)
    BoostNode2 = hexa_dict.get('EnhanceCore2', 0)
    BoostNode3 = hexa_dict.get('EnhanceCore3', 0)
    BoostNode4 = hexa_dict.get('EnhanceCore4', 0)
    CommonNode1 = hexa_dict.get('CommonCore1', 0)

    # 計算六轉核心完成度
    totalcount, maxfragment = Calculatefragment(
        SkillNodes1, 
        MasteryNodes1, MasteryNodes2, MasteryNodes3, MasteryNodes4,
        BoostNode1, BoostNode2, BoostNode3, BoostNode4,
        CommonNode1,
        extrafragment=0
    )
    percentage = (totalcount / maxfragment * 100) if maxfragment > 0 else 0

    if hexa_dict:
        hexa_info = []
        
        skill_cores = []
        mastery_cores = []
        enhance_cores = []
        common_cores = []
        
        for key, level in hexa_dict.items():
            if key.startswith('SkillCore'):
                skill_cores.append(str(level))
            elif key.startswith('MasteryCore'):
                mastery_cores.append(str(level))
            elif key.startswith('EnhanceCore'):
                enhance_cores.append(str(level))
            elif key.startswith('CommonCore'):
                common_cores.append(str(level))
        
        # Helper function to format core levels with spacing for alignment
        def format_core_level(level_str):
            level = int(level_str)
            return f"{level:2d}"
        
        if skill_cores:
            formatted_skill_cores = [format_core_level(level) for level in skill_cores]
            hexa_info.append(f"技能核心　： {' | '.join(formatted_skill_cores)}")
        if mastery_cores:
            formatted_mastery_cores = [format_core_level(level) for level in mastery_cores]
            hexa_info.append(f"精通核心　： {' | '.join(formatted_mastery_cores)}")
        if enhance_cores:
            formatted_enhance_cores = [format_core_level(level) for level in enhance_cores]
            hexa_info.append(f"強化核心　： {' | '.join(formatted_enhance_cores)}")
        if common_cores:
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
        
        arcane_symbols = []  # 祕法符文
        sacred_symbols = []  # 真實符文
        luxury_symbols = []  # 豪華真實符文
        
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
    
    # character_image
    if character_basic_data.get('character_image'):
        embed.set_thumbnail(url=character_basic_data['character_image'])
             
    embed.add_field(
        name="基本資訊",
        value=f"```autohotkey\n{'\n'.join(character_info)}```",
        inline=False
    )
    embed.add_field(
        name="機體資訊",
        value=f"```autohotkey\n{'\n'.join(stat_info)}```",
        inline=False
    )
    
    if hexa_dict and hexa_info:
        embed.add_field(
            name=f"六轉核心 ({percentage:.2f}%)",
            value=f"```autohotkey\n{'\n'.join(hexa_info)}\n{'\n'.join(hexa_stat_info)}```",
            inline=False
        )
       
    if symbol_info:
        embed.add_field(
            name="符文",
            value=f"```autohotkey\n{'\n'.join(symbol_info)}```",
            inline=False
        )

    # create_date
    create_date = character_basic_data.get('character_date_create')
    if create_date:
        try:
            date_obj = datetime.datetime.fromisoformat(create_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%Y-%m-%d')
            character_create_date = f"創建日期: {formatted_date}"
        except:
            character_create_date = f"創建日期: {create_date}"

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



