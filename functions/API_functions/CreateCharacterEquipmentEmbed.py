import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Character import get_character_ocid, request_character_itemequipment, request_character_cashitemequipment, request_character_pet_equipment, request_character_beauty_equipment, request_character_ability, request_character_hyper_stat
import datetime

from functions.Cogs.Slash_CalculateScrolls import scrolls_fitting

from Data.SmallData import class_main_stat
from Data.BotEmojiList import EmojiList

class EquipmentView(discord.ui.View):
    def __init__(self, character_name: str, character_equipment_data: dict, character_cashitem_equipment_data: dict = None, character_pet_equipment_data: dict = None, character_beauty_equipment_data: dict = None, character_ability_data: dict = None, character_hyper_stat_data: dict = None, current_preset: str = "preset_1", character_basic_data: dict = None):
        super().__init__(timeout=300)  # 5 minute timeout
        self.character_name = character_name
        self.character_equipment_data = character_equipment_data
        self.character_cashitem_equipment_data = character_cashitem_equipment_data
        self.character_pet_equipment_data = character_pet_equipment_data
        self.character_beauty_equipment_data = character_beauty_equipment_data
        self.character_ability_data = character_ability_data
        self.character_hyper_stat_data = character_hyper_stat_data
        self.character_basic_data = character_basic_data
        self.current_preset = current_preset
    
        self.current_category = "weapon"  # Default category
        
        # Process current preset equipment data
        self._process_equipment_data()
        # Update button colors
        self._update_preset_button_styles()
    
    def _update_preset_button_styles(self):
        """Update button colors based on current preset"""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "預設1":
                    item.style = discord.ButtonStyle.primary if self.current_preset == "preset_1" else discord.ButtonStyle.success
                elif item.label == "預設2":
                    item.style = discord.ButtonStyle.primary if self.current_preset == "preset_2" else discord.ButtonStyle.success
                elif item.label == "預設3":
                    item.style = discord.ButtonStyle.primary if self.current_preset == "preset_3" else discord.ButtonStyle.success
    
    def _process_equipment_data(self):
        """Process equipment data and categorize"""
        preset_key = f'item_equipment_{self.current_preset}'
        preset_equipment = self.character_equipment_data.get(preset_key, [])

        # Equipment slot categorization
        weapon_slots = ['武器', '輔助武器', '徽章']
        armor_slots = ['帽子', '上衣', '褲/裙', '鞋子', '手套', '披風', '肩膀裝飾']
        accessory_slots = ['臉飾', '眼飾', '耳環', '墜飾', '墜飾2', '腰帶', '戒指1', '戒指2', '戒指3', '戒指4']
        # 其他裝備：口袋/胸章/勳章/機器心臟 + 圖騰1/2/3（馴服的怪物 / 馬鞍 / 怪物裝備）
        other_slots = ['口袋道具', '胸章', '勳章', '機器人', '機器心臟', '馴服的怪物', '馬鞍', '怪物裝備']

        # 圖騰與寶玉不隨 preset 切換，只存在於頂層 item_equipment，補進來一起處理（歸入「其他裝備」）
        totem_slots = ('馴服的怪物', '馬鞍', '怪物裝備')
        top_level_equipment = self.character_equipment_data.get('item_equipment', [])
        extra_equipment = [
            e for e in top_level_equipment
            if e.get('item_equipment_slot') in totem_slots or '寶玉' in e.get('item_name', '')
        ]
        combined_equipment = list(preset_equipment) + extra_equipment

        # Reset grouping
        self.weapon_info = []
        self.armor_info = []
        self.accessory_info = []
        self.other_info = []

        for equipment in combined_equipment:
            item_name = equipment.get('item_name', '未知裝備')
            item_slot = equipment.get('item_equipment_slot', '未知部位')
            starforce = equipment.get('starforce', '0')

            # 寶玉（伊妮絲的寶玉）特別處理：與墜飾共用部位，改以名稱辨識並歸入「其他裝備」
            # 只列出 item_total_option 中不為零的屬性（例如 INT+6775）
            if '寶玉' in item_name:
                total_option = equipment.get('item_total_option', {})
                gem_stat_mapping = {
                    'str': 'STR', 'dex': 'DEX', 'int': 'INT', 'luk': 'LUK',
                    'max_hp': 'HP', 'max_mp': 'MP',
                    'attack_power': '物攻', 'magic_power': '魔攻',
                    'armor': '防禦', 'speed': '移動速度', 'jump': '跳躍力',
                    'boss_damage': 'Boss傷害', 'damage': '傷害', 'all_stat': '全屬性',
                    'ignore_monster_armor': '無視防禦率',
                    'max_hp_rate': 'HP%', 'max_mp_rate': 'MP%',
                }
                percent_stats = {'boss_damage', 'damage', 'all_stat',
                                 'ignore_monster_armor', 'max_hp_rate', 'max_mp_rate'}
                gem_stats = []
                for stat_key, stat_label in gem_stat_mapping.items():
                    stat_value = total_option.get(stat_key, '0')
                    try:
                        if int(stat_value) != 0:
                            suffix = '%' if stat_key in percent_stats else ''
                            gem_stats.append(f"{stat_label}+{stat_value}{suffix}")
                    except (ValueError, TypeError):
                        pass
                gem_text = f"**{item_name}**\n"
                if gem_stats:
                    gem_text += f"```{' / '.join(gem_stats)}```"
                gem_text += "\n"
                self.other_info.append(gem_text)
                continue

            # Potential options
            potential_grade = equipment.get('potential_option_grade', 'None')
            potential_1 = equipment.get('potential_option_1')
            potential_2 = equipment.get('potential_option_2')
            potential_3 = equipment.get('potential_option_3')
            
            # Additional potential options
            add_potential_grade = equipment.get('additional_potential_option_grade', 'None')
            add_potential_1 = equipment.get('additional_potential_option_1')
            add_potential_2 = equipment.get('additional_potential_option_2')
            add_potential_3 = equipment.get('additional_potential_option_3')
            
            # Format equipment information - detailed display
            equipment_text = f"**{item_name}**"
            
            # Add exceptional upgrade information
            item_exceptional_option = equipment.get('item_exceptional_option', {})
            exceptional_upgrade = int(item_exceptional_option.get('exceptional_upgrade', 0))
            if exceptional_upgrade > 0:
                equipment_text += f" {EmojiList.get('Exceptional_Hammer', '')}{exceptional_upgrade}"
            
            if int(starforce) > 0:
                equipment_text += f" ⭐{starforce}"
                
                # Add scroll upgrade information
                scroll_upgrade = equipment.get('scroll_upgrade', '0')
                if int(scroll_upgrade) > 0:
                    item_etc_option = equipment.get('item_etc_option', {})
                    attack_power = int(item_etc_option.get('attack_power', 0))
                    magic_power = int(item_etc_option.get('magic_power', 0))
                    max_power = max(attack_power, magic_power)
                    
                    if max_power > 0:
                        scroll_avg = max_power / int(scroll_upgrade)
                        
                        # Determine equipment category for scrolls_fitting
                        if item_slot == '武器':
                            equipment_type = "武器"
                        elif item_slot == '手套':
                            equipment_type = "手套"
                        else:
                            equipment_type = "其他"
                        
                        # Get scroll type from scrolls_fitting function
                        scroll_type = scrolls_fitting(equipment_type, scroll_avg)
                        
                        if scroll_type is None:
                            equipment_text += f" {EmojiList.get('Scroll_60', '')}{scroll_upgrade} ({scroll_avg:.1f})"
                        else:
                            equipment_text += f" {EmojiList.get('Scroll_60', '')}{scroll_upgrade} ({scroll_type})"
            
            # Add item_add_option information (non-zero values)
            item_add_option = equipment.get('item_add_option', {})
            etc_stats = []
                        
            # Xenon fuck u
            special_exclude_stats = {
                "傑諾": ["int"]  
            }
            
            # Get character class from character_basic_data
            character_class = ""
            if self.character_basic_data:
                character_class = self.character_basic_data.get('character_class', '')
            
            # Find the main stat for current character class
            character_main_stat = ""
            for stat_key, class_list in class_main_stat.items():
                if character_class in class_list:
                    character_main_stat = stat_key
                    break
            
            # Define the stats we want to check and their abbreviations
            stat_mapping = {
                'str': 'S',
                'dex': 'D', 
                'int': 'I',
                'luk': 'L',
                'max_hp': 'HP',
                'attack_power': '物',
                'magic_power': '魔',
                "boss_damage": "B",
                "damage": "總",
                "all_stat": "全",
            }
            
            # Define stats that are always shown regardless of class
            always_show_stats = ['attack_power', 'magic_power', 'boss_damage', 'damage', 'all_stat']
            
            # Process stats based on class and configuration
            for stat_key, stat_abbr in stat_mapping.items():
                stat_value = item_add_option.get(stat_key, '0')
                try:
                    if int(stat_value) > 0:
                        # Always show certain stats regardless of class
                        if stat_key in always_show_stats:
                            etc_stats.append(f"{stat_abbr}{stat_value}")
                        # For main stats (STR/DEX/INT/LUK/HP)
                        elif stat_key in ['str', 'dex', 'int', 'luk', 'max_hp']:
                            # Check if this stat should be excluded for special classes
                            excluded_stats = special_exclude_stats.get(character_class, [])
                            if stat_key in excluded_stats:
                                continue
                                
                            # If character has a specific main stat, only show that one
                            if character_main_stat:
                                if stat_key == character_main_stat:
                                    etc_stats.append(f"{stat_abbr}{stat_value}")
                            # If character is not in class_main_stat, show all main stats
                            else:
                                etc_stats.append(f"{stat_abbr}{stat_value}")
                except (ValueError, TypeError):
                    pass
            
            if etc_stats:
                equipment_text += f" {EmojiList.get('flame_rainbow', '')}{' '.join(etc_stats)}"
            
            equipment_text += "\n"  # Add separator blank line
            
            # Check if it's a ring and has special_ring_level
            special_ring_level = equipment.get('special_ring_level')
            if item_slot in ['戒指1', '戒指2', '戒指3', '戒指4'] and special_ring_level:
                try:
                    ring_level = int(special_ring_level)
                    if ring_level > 0:
                        equipment_text += f"```LV {ring_level}\n```"
                except (ValueError, TypeError):
                    pass
            
            # Soul information (for weapons only)
            if item_slot in weapon_slots:
                soul_name = equipment.get('soul_name')
                soul_option = equipment.get('soul_option')
                if soul_name and soul_option:
                    equipment_text += f"```{soul_name}｜{soul_option}\n```"             

            # Potential information (detailed display)
            if potential_grade != 'None' and potential_1:
                potentials = [p for p in [potential_1, potential_2, potential_3] if p]
                if potentials:
                    # Add color icon based on potential grade
                    grade_icon = ""
                    if potential_grade == "傳說":
                        grade_icon = "🟢"  # Green
                    elif potential_grade == "罕見":
                        grade_icon = "🟡"  # Yellow
                    elif potential_grade == "稀有":
                        grade_icon = "🟣"  # Purple
                    elif potential_grade == "特殊":
                        grade_icon = "🔵"  # Blue
                    
                    equipment_text += f"```{grade_icon}{' / '.join(potentials)}\n```"
            
            # Additional potential information (detailed display)
            if add_potential_grade != 'None' and add_potential_1:
                add_potentials = [p for p in [add_potential_1, add_potential_2, add_potential_3] if p]
                if add_potentials:
                    # Add color icon based on additional potential grade
                    add_grade_icon = ""
                    if add_potential_grade == "傳說":
                        add_grade_icon = "🟢"  # Green
                    elif add_potential_grade == "罕見":
                        add_grade_icon = "🟡"  # Yellow
                    elif add_potential_grade == "稀有":
                        add_grade_icon = "🟣"  # Purple
                    elif add_potential_grade == "特殊":
                        add_grade_icon = "🔵"  # Blue
                    
                    equipment_text += f"```{add_grade_icon}{' / '.join(add_potentials)}\n```"
                       
            
            # Categorize equipment (using item_equipment_slot)
            if item_slot in weapon_slots:
                self.weapon_info.append(equipment_text)
            elif item_slot in armor_slots:
                self.armor_info.append(equipment_text)
            elif item_slot in accessory_slots:
                self.accessory_info.append(equipment_text)
            elif item_slot in other_slots:
                self.other_info.append(equipment_text)
        
        # Process cash item equipment info (Fashion Appearance - by preset configuration)
        self.cashitem_info = []
        
        # Add beauty equipment info at the top
        if self.character_beauty_equipment_data:
            beauty_info = []
            
            # Hair information
            hair_data = self.character_beauty_equipment_data.get('character_hair', {})
            if hair_data:
                hair_name = hair_data.get('hair_name', '未知髮型')
                base_color = hair_data.get('base_color', '')
                mix_color = hair_data.get('mix_color')
                mix_rate = hair_data.get('mix_rate', '0')
                
                if mix_color and int(mix_rate) > 0:
                    remaining_rate = 100 - int(mix_rate)
                    hair_info = f"髮型：{hair_name} ({base_color}{remaining_rate}-{mix_color}{mix_rate})"
                else:
                    hair_info = f"髮型：{hair_name} ({base_color})"
                beauty_info.append(hair_info)
            
            # Face information
            face_data = self.character_beauty_equipment_data.get('character_face', {})
            if face_data:
                face_name = face_data.get('face_name', '未知臉型')
                base_color = face_data.get('base_color', '')
                mix_color = face_data.get('mix_color')
                mix_rate = face_data.get('mix_rate', '0')
                
                if mix_color and int(mix_rate) > 0:
                    remaining_rate = 100 - int(mix_rate)
                    face_info = f"臉型：{face_name}({base_color}{remaining_rate}-{mix_color}{mix_rate})"
                else:
                    face_info = f"臉型：{face_name}({base_color})"
                beauty_info.append(face_info)
            
            # Skin information
            skin_data = self.character_beauty_equipment_data.get('character_skin', {})
            if skin_data:
                skin_name = skin_data.get('skin_name', '未知皮膚')
                skin_info = f"皮膚：{skin_name}"
                beauty_info.append(skin_info)
            
            # Add beauty info to cashitem_info
            if beauty_info:
                beauty_text = '\n'.join(beauty_info) + '\n\n'
                self.cashitem_info.append(beauty_text)
        
        if self.character_cashitem_equipment_data:
            # Select corresponding preset configuration
            preset_number = self.current_preset.split('_')[1]  # Extract 1 from preset_1
            cashitem_preset_key = f'cash_item_equipment_preset_{preset_number}'
            
            preset_cashitem = self.character_cashitem_equipment_data.get(cashitem_preset_key, [])
            
            for cashitem in preset_cashitem:
                item_name = cashitem.get('cash_item_name', '未知外觀')
                item_slot = cashitem.get('cash_item_equipment_slot', '未知部位')
                
                cashitem_text = f"**{item_slot}**： {item_name}\n"
                self.cashitem_info.append(cashitem_text)
        
        # Process base fashion info (Fashion - shared by all presets)
        self.cashitem_base_info = []
        if self.character_cashitem_equipment_data:
            base_cashitem = self.character_cashitem_equipment_data.get('cash_item_equipment_base', [])
            
            for cashitem in base_cashitem:
                item_name = cashitem.get('cash_item_name', '未知時裝')
                item_slot = cashitem.get('cash_item_equipment_slot', '未知部位')
                
                cashitem_text = f"**{item_slot}**： {item_name}\n"
                self.cashitem_base_info.append(cashitem_text)
        
        # Process pet equipment info (shared by all presets)
        self.pet_info = []
        if self.character_pet_equipment_data:
            for pet_num in [1, 2, 3]:
                pet_name = self.character_pet_equipment_data.get(f'pet_{pet_num}_name')
                pet_equipment = self.character_pet_equipment_data.get(f'pet_{pet_num}_equipment')
                
                if pet_name and pet_equipment:
                    equipment_name = pet_equipment.get('item_name', '無裝備')
                    pet_text = f"**{pet_name}** ({equipment_name})\n"
                    
                    # Add item options
                    item_options = pet_equipment.get('item_option', [])
                    for option in item_options:
                        option_type = option.get('option_type', '')
                        option_value = option.get('option_value', '')
                        if option_type and option_value:
                            pet_text += f"```{option_type} {option_value}```"
                    
                    pet_text += "\n"  # Add separator blank line
                    self.pet_info.append(pet_text)
        
        # Process hyper stat data (極限屬性) - only current preset
        self.hyper_stat_info = []
        if self.character_hyper_stat_data:
            # Get current preset number from current_preset (preset_1 -> 1)
            current_preset_num = int(self.current_preset.split('_')[1])
            preset_key = f"hyper_stat_preset_{current_preset_num}"
            preset_data = self.character_hyper_stat_data.get(preset_key, [])
            
            if preset_data:
                # Create mapping for stat types with padding to align colons
                stat_type_mapping = {
                    'STR': '　　ＳＴＲ　　　',
                    'DEX': '　　ＤＥＸ　　　',
                    'INT': '　　ＩＮＴ　　　',
                    'LUK': '　　ＬＵＫ　　　',
                    'HP': '　　ＨＰ　　　　',
                    'MP': '　　ＭＰ　　　　',
                    'DF/TF/PP': 'ＤＦ／ＴＦ／ＰＰ',
                    '爆擊機率': '　　爆擊機率　　',
                    '爆擊傷害': '　　爆擊傷害　　',
                    '無視防禦率': '　　無視防禦率　',
                    '傷害': '　　傷害　　　　',
                    'Boss傷害': '　　Ｂｏｓｓ傷害',
                    '異常狀態耐性': '　　異常狀態耐性',
                    '攻擊力／魔力': '　　攻擊力／魔力',
                    '獲得經驗值': '　　獲得經驗值　',
                    '神秘力量': '　　神秘力量　　',
                    '一般傷害': '　　一般傷害　　'
                }
                
                hyper_stat_texts = []
                for stat in preset_data:
                    stat_type = stat.get('stat_type', '')
                    stat_level = stat.get('stat_level', 0)
                    
                    # Only show stats with level > 0
                    if stat_level and int(stat_level) > 0:
                        # Get formatted stat type with padding
                        formatted_stat_type = stat_type_mapping.get(stat_type, stat_type)
                        hyper_stat_texts.append(f"{formatted_stat_type}：Lv {stat_level}")
                
                if hyper_stat_texts:
                    hyper_stat_text = "```\n" + "\n".join(hyper_stat_texts) + "\n```"
                    self.hyper_stat_info.append(hyper_stat_text)

        # Process ability data (內在潛能) - only current preset
        self.ability_info = []
        if self.character_ability_data:
            # Helper function to get grade emoji
            def get_grade_emoji(grade):
                if grade == "傳說":
                    return "🟢"  # Green
                elif grade == "罕見":
                    return "🟡"  # Yellow
                elif grade == "稀有":
                    return "🟣"  # Purple
                elif grade == "特殊":
                    return "🔵"  # Blue
                else:
                    return ""
            
            # Get current preset number from current_preset (preset_1 -> 1)
            current_preset_num = int(self.current_preset.split('_')[1])
            preset_key = f"ability_preset_{current_preset_num}"
            preset_data = self.character_ability_data.get(preset_key)
            
            if preset_data and preset_data.get('ability_info'):
                ability_texts = []
                for ability in preset_data['ability_info']:
                    grade = ability.get('ability_grade', '')
                    value = ability.get('ability_value', '')
                    grade_emoji = get_grade_emoji(grade)
                    ability_texts.append(f"{grade_emoji}{value}")
                
                if ability_texts:
                    ability_text = "```\n" + "\n".join(ability_texts) + "\n```"
                    
                    # Add fame value
                    remain_fame = self.character_ability_data.get('remain_fame', 0)
                    if remain_fame:
                        fame_text = f"名聲值：{remain_fame:,}"
                        ability_text += f"\n{fame_text}"
                    
                    self.ability_info.append(ability_text)
        
    def create_embed(self, category: str) -> discord.Embed:
        """Create corresponding embed based on category"""
        category_names = {
            "weapon": "武器",
            "armor": "防具", 
            "accessory": "飾品",
            "other": "其他",
            "cashitem": "時裝外觀",
            "cashitem_base": "時裝",
            "pet": "寵物",
            "ability": "極限屬性/內在潛能"
        }
        
        preset_names = {
            "preset_1": "裝備預設 1",
            "preset_2": "裝備預設 2", 
            "preset_3": "裝備預設 3"
        }
        
        embed = discord.Embed(
            title=f"{self.character_name} 的裝備資訊",
            description=f"**{preset_names.get(self.current_preset, '未知配置')} - {category_names.get(category, '未知分類')}**",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        # Add character image if available
        if self.character_basic_data and self.character_basic_data.get('character_image'):
            embed.set_thumbnail(url=self.character_basic_data['character_image'])
        
        if category == "weapon":
            # Weapons only
            if self.weapon_info:
                text = ''.join(self.weapon_info)
                if len(text) > 1024:
                    # Split long text
                    chunks = []
                    current_chunk = ""
                    for item in self.weapon_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無裝備資料", inline=False)
                
        elif category == "armor":
            if self.armor_info:
                text = ''.join(self.armor_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.armor_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無裝備資料", inline=False)
                
        elif category == "accessory":
            if self.accessory_info:
                text = ''.join(self.accessory_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.accessory_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無裝備資料", inline=False)
                
        elif category == "other":
            if self.other_info:
                text = ''.join(self.other_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.other_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無裝備資料", inline=False)
                
        elif category == "cashitem":
            if self.cashitem_info:
                text = ''.join(self.cashitem_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.cashitem_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無時裝外觀資料", inline=False)
                
        elif category == "cashitem_base":
            if self.cashitem_base_info:
                text = ''.join(self.cashitem_base_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.cashitem_base_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無時裝資料", inline=False)
                
        elif category == "pet":
            if self.pet_info:
                text = ''.join(self.pet_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.pet_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="\u200b", value=text, inline=False)
            else:
                embed.add_field(name="\u200b", value="無寵物資料", inline=False)
                
        elif category == "ability":
            # Add hyper stat info first (極限屬性)
            if self.hyper_stat_info:
                hyper_stat_text = ''.join(self.hyper_stat_info)
                embed.add_field(name="極限屬性", value=hyper_stat_text, inline=False)
            
            # Then add ability info
            if self.ability_info:
                text = ''.join(self.ability_info)
                if len(text) > 1024:
                    chunks = []
                    current_chunk = ""
                    for item in self.ability_info:
                        if len(current_chunk + item) > 800:  # Reduced threshold to prevent overflow
                            chunks.append(current_chunk)
                            current_chunk = item
                        else:
                            current_chunk += item
                    if current_chunk:
                        chunks.append(current_chunk)
                    
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            embed.add_field(name="內在潛能", value=chunk, inline=False)
                        else:
                            embed.add_field(name="\u200b", value=chunk, inline=False)
                else:
                    embed.add_field(name="內在潛能", value=text, inline=False)
            else:
                embed.add_field(name="內在潛能", value="無內在潛能資料", inline=False)

        # Footer 虛線：與角色頁一致，撐住 embed 寬度，避免切換分頁時跑版
        embed.set_footer(text=self._build_footer_text())

        return embed

    def _build_footer_text(self) -> str:
        """產生與角色頁相同格式的「創建日期＋虛線」footer，維持 embed 寬度避免跑版"""
        # 無創建日期資料時，退回純虛線（仍維持寬度）
        fallback = f"{'-'*19}　　　　　　　　　　{'-'*19}"
        if not (self.character_basic_data and self.character_basic_data.get('character_date_create')):
            return fallback

        create_date = self.character_basic_data['character_date_create']
        try:
            date_obj = datetime.datetime.fromisoformat(create_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime('%Y-%m-%d')

            today_date_only = datetime.datetime.now().date()
            create_date_only = date_obj.date()
            days_diff = (today_date_only - create_date_only).days

            is_birthday = (create_date_only.month == today_date_only.month and
                           create_date_only.day == today_date_only.day)

            if is_birthday:
                return f"{'-'*19}創建日期: {formatted_date} ({days_diff}天) 🎉生日快樂！🎂{'-'*19}"
            return f"{'-'*19}創建日期: {formatted_date} ({days_diff}天){'-'*19}"
        except Exception:
            return f"{'-'*19}創建日期: {create_date}{'-'*19}"
    
    @discord.ui.select(
        placeholder="選擇要查看的裝備分類...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="武器",
                description="",
                emoji="⚔️",
                value="weapon"
            ),
            discord.SelectOption(
                label="防具",
                description="",
                emoji="🛡️",
                value="armor"
            ),
            discord.SelectOption(
                label="飾品",
                description="",
                emoji="💍",
                value="accessory"
            ),
            discord.SelectOption(
                label="其他裝備",
                description="",
                emoji="🎖️",
                value="other"
            ),
            discord.SelectOption(
                label="時裝",
                description="",
                emoji="💰",
                value="cashitem_base"
            ),
            discord.SelectOption(
                label="時裝外觀",
                description="",
                emoji="👗",
                value="cashitem"
            ),
            discord.SelectOption(
                label="寵物",
                description="",
                emoji="🐾",
                value="pet"
            ),
            discord.SelectOption(
                label="極限屬性/內在潛能",
                description="",
                emoji="✨",
                value="ability"
            )
        ]
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.current_category = select.values[0]
        embed = self.create_embed(self.current_category)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="預設1", style=discord.ButtonStyle.success)
    async def preset_1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_preset != "preset_1":
            self.current_preset = "preset_1"
            self._process_equipment_data()
            self._update_preset_button_styles()
            embed = self.create_embed(self.current_category)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="預設2", style=discord.ButtonStyle.success)
    async def preset_2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_preset != "preset_2":
            self.current_preset = "preset_2"
            self._process_equipment_data()
            self._update_preset_button_styles()
            embed = self.create_embed(self.current_category)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="預設3", style=discord.ButtonStyle.success)
    async def preset_3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_preset != "preset_3":
            self.current_preset = "preset_3"
            self._process_equipment_data()
            self._update_preset_button_styles()
            embed = self.create_embed(self.current_category)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="返回角色資料", style=discord.ButtonStyle.secondary, emoji="🔙", row=2)
    async def back_to_character_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Return to character basic information
        try:
            from functions.API_functions.CreateCharacterEmbed import create_character_basic_embed
            embed = create_character_basic_embed(self.character_name)
            
            # Create a simple view that only displays buttons for users to choose return to equipment or re-query
            class SimpleCharacterView(discord.ui.View):
                def __init__(self, character_name: str, character_basic_data: dict = None):
                    super().__init__(timeout=300)
                    self.character_name = character_name
                    self.character_basic_data = character_basic_data
                
                @discord.ui.button(label="角色", style=discord.ButtonStyle.primary, emoji="👤")
                async def character_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.defer()
                
                @discord.ui.button(label="預設1", style=discord.ButtonStyle.success)
                async def preset_1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                    embed = result["embed"]
                    view = result["view"]
                    if view and embed:
                        view.current_preset = "preset_1"
                        view._process_equipment_data()
                        view._update_preset_button_styles()
                        embed = view.create_embed("weapon")
                        await interaction.response.edit_message(embed=embed, view=view)
                
                @discord.ui.button(label="預設2", style=discord.ButtonStyle.success)
                async def preset_2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                    embed = result["embed"]
                    view = result["view"]
                    if view and embed:
                        view.current_preset = "preset_2"
                        view._process_equipment_data()
                        view._update_preset_button_styles()
                        embed = view.create_embed("weapon")
                        await interaction.response.edit_message(embed=embed, view=view)
                
                @discord.ui.button(label="預設3", style=discord.ButtonStyle.success)
                async def preset_3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                    embed = result["embed"]
                    view = result["view"]
                    if view and embed:
                        view.current_preset = "preset_3"
                        view._process_equipment_data()
                        view._update_preset_button_styles()
                        embed = view.create_embed("weapon")
                        await interaction.response.edit_message(embed=embed, view=view)
            
            view = SimpleCharacterView(self.character_name, self.character_basic_data)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            error_embed = discord.Embed(
                title="錯誤",
                description=f"返回角色資料時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=error_embed)
    
    async def on_timeout(self):
        # Disable all components after timeout
        for item in self.children:
            item.disabled = True


def create_character_equipment_embed(character_name: str, character_basic_data: dict = None) -> dict:
 
    ocid = get_character_ocid(character_name)
    
    if not ocid:
        embed = discord.Embed(
            title="錯誤",
            description=f"無法找到角色 '{character_name}' 的資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    # Get equipment data
    character_equipment_data = request_character_itemequipment(ocid)
    character_cashitem_equipment_data = request_character_cashitemequipment(ocid)
    character_pet_equipment_data = request_character_pet_equipment(ocid)
    character_beauty_equipment_data = request_character_beauty_equipment(ocid)
    character_ability_data = request_character_ability(ocid)
    character_hyper_stat_data = request_character_hyper_stat(ocid)
    
    if not character_equipment_data:
        embed = discord.Embed(
            title="錯誤",
            description=f"無法獲取角色 '{character_name}' 的裝備資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    # Check if at least one preset has data
    has_preset_data = False
    for preset_num in [1, 2, 3]:
        preset_key = f'item_equipment_preset_{preset_num}'
        if character_equipment_data.get(preset_key):
            has_preset_data = True
            break
    
    if not has_preset_data:
        embed = discord.Embed(
            title="錯誤", 
            description=f"角色 '{character_name}' 沒有任何裝備預設配置資料",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    # Create View and initial embed
    view = EquipmentView(character_name, character_equipment_data, character_cashitem_equipment_data, character_pet_equipment_data, character_beauty_equipment_data, character_ability_data, character_hyper_stat_data, current_preset="preset_1", character_basic_data=character_basic_data)
    initial_embed = view.create_embed("weapon")  # Default display weapons
    
    return {"embed": initial_embed, "view": view}