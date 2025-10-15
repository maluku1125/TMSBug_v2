import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Character import get_character_ocid, request_character_itemequipment, request_character_cashitemequipment
import datetime


class EquipmentView(discord.ui.View):
    def __init__(self, character_name: str, character_equipment_data: dict, character_cashitem_equipment_data: dict = None, current_preset: str = "preset_1"):
        super().__init__(timeout=300)  # 5 minute timeout
        self.character_name = character_name
        self.character_equipment_data = character_equipment_data
        self.character_cashitem_equipment_data = character_cashitem_equipment_data
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
        other_slots = ['口袋道具', '胸章', '勳章', '機器人', '機器心臟']
        
        # Reset grouping
        self.weapon_info = []
        self.armor_info = []
        self.accessory_info = []
        self.other_info = []
        
        for equipment in preset_equipment:
            item_name = equipment.get('item_name', '未知裝備')
            item_slot = equipment.get('item_equipment_slot', '未知部位')
            starforce = equipment.get('starforce', '0')
            
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
                        equipment_text += f" 📜{scroll_avg:.1f}"
                        
            equipment_text += "\n"
            
            # Check if it's a ring and has special_ring_level
            special_ring_level = equipment.get('special_ring_level')
            if item_slot in ['戒指1', '戒指2', '戒指3', '戒指4'] and special_ring_level:
                try:
                    ring_level = int(special_ring_level)
                    if ring_level > 0:
                        equipment_text += f"```LV {ring_level}\n```"
                except (ValueError, TypeError):
                    pass
            
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
            
            equipment_text += "\n"  # Add separator blank line
            
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
        
    def create_embed(self, category: str) -> discord.Embed:
        """Create corresponding embed based on category"""
        category_names = {
            "weapon": "武器",
            "armor": "防具", 
            "accessory": "飾品",
            "other": "其他",
            "cashitem": "時裝外觀",
            "cashitem_base": "時裝"
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
        
        if category == "weapon":
            # Weapons only
            if self.weapon_info:
                text = ''.join(self.weapon_info)
                if len(text) > 1024:
                    # Split long text
                    chunks = []
                    current_chunk = ""
                    for item in self.weapon_info:
                        if len(current_chunk + item) > 1000: 
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
                        if len(current_chunk + item) > 1000:
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
                        if len(current_chunk + item) > 1000:
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
                        if len(current_chunk + item) > 1000:
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
                        if len(current_chunk + item) > 1000:
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
                        if len(current_chunk + item) > 1000:
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
        
        return embed
    
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
                label="其他",
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
                def __init__(self, character_name: str):
                    super().__init__(timeout=300)
                    self.character_name = character_name
                
                @discord.ui.button(label="角色", style=discord.ButtonStyle.primary, emoji="👤")
                async def character_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.defer()
                
                @discord.ui.button(label="預設1", style=discord.ButtonStyle.success)
                async def preset_1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    result = create_character_equipment_embed(self.character_name)
                    embed = result["embed"]
                    view = result["view"]
                    if view and embed:
                        view.current_preset = "preset_1"
                        view._process_equipment_data()
                        embed = view.create_embed("weapon")
                        await interaction.response.edit_message(embed=embed, view=view)
                
                @discord.ui.button(label="預設2", style=discord.ButtonStyle.success)
                async def preset_2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    result = create_character_equipment_embed(self.character_name)
                    embed = result["embed"]
                    view = result["view"]
                    if view and embed:
                        view.current_preset = "preset_2"
                        view._process_equipment_data()
                        embed = view.create_embed("weapon")
                        await interaction.response.edit_message(embed=embed, view=view)
                
                @discord.ui.button(label="預設3", style=discord.ButtonStyle.success)
                async def preset_3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    result = create_character_equipment_embed(self.character_name)
                    embed = result["embed"]
                    view = result["view"]
                    if view and embed:
                        view.current_preset = "preset_3"
                        view._process_equipment_data()
                        embed = view.create_embed("weapon")
                        await interaction.response.edit_message(embed=embed, view=view)
            
            view = SimpleCharacterView(self.character_name)
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


def create_character_equipment_embed(character_name: str) -> dict:
 
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
    view = EquipmentView(character_name, character_equipment_data, character_cashitem_equipment_data)
    initial_embed = view.create_embed("weapon")  # Default display weapons
    
    return {"embed": initial_embed, "view": view}