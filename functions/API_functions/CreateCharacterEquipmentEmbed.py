import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Character import get_character_ocid, request_character_itemequipment
import datetime


class EquipmentView(discord.ui.View):
    def __init__(self, character_name: str, character_equipment_data: dict, current_preset: str = "preset_1"):
        super().__init__(timeout=300)  # 5分鐘超時
        self.character_name = character_name
        self.character_equipment_data = character_equipment_data
        self.current_preset = current_preset
        self.current_category = "weapon"  # 預設分類
        
        # 處理當前 preset 的裝備數據
        self._process_equipment_data()
        # 更新按鈕顏色
        self._update_preset_button_styles()
    
    def _update_preset_button_styles(self):
        """根據當前 preset 更新按鈕顏色"""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "預設1":
                    item.style = discord.ButtonStyle.primary if self.current_preset == "preset_1" else discord.ButtonStyle.success
                elif item.label == "預設2":
                    item.style = discord.ButtonStyle.primary if self.current_preset == "preset_2" else discord.ButtonStyle.success
                elif item.label == "預設3":
                    item.style = discord.ButtonStyle.primary if self.current_preset == "preset_3" else discord.ButtonStyle.success
    
    def _process_equipment_data(self):
        """處理裝備數據並分類"""
        preset_key = f'item_equipment_{self.current_preset}'
        preset_equipment = self.character_equipment_data.get(preset_key, [])
        
        # 裝備部位分類
        weapon_slots = ['武器', '輔助武器', '徽章']
        armor_slots = ['帽子', '上衣', '褲/裙', '鞋子', '手套', '披風', '肩膀裝飾']
        accessory_slots = ['臉飾', '眼飾', '耳環', '墜飾', '墜飾2', '腰帶', '戒指1', '戒指2', '戒指3', '戒指4']
        other_slots = ['口袋道具', '胸章', '勳章', '機器人', '機器心臟']
        
        # 重置分組
        self.weapon_info = []
        self.armor_info = []
        self.accessory_info = []
        self.other_info = []
        
        for equipment in preset_equipment:
            item_name = equipment.get('item_name', '未知裝備')
            item_slot = equipment.get('item_equipment_slot', '未知部位')
            starforce = equipment.get('starforce', '0')
            
            # 潛能選項
            potential_grade = equipment.get('potential_option_grade', 'None')
            potential_1 = equipment.get('potential_option_1')
            potential_2 = equipment.get('potential_option_2')
            potential_3 = equipment.get('potential_option_3')
            
            # 附加潛能選項
            add_potential_grade = equipment.get('additional_potential_option_grade', 'None')
            add_potential_1 = equipment.get('additional_potential_option_1')
            add_potential_2 = equipment.get('additional_potential_option_2')
            add_potential_3 = equipment.get('additional_potential_option_3')
            
            # 格式化裝備資訊 - 詳細顯示
            equipment_text = f"**{item_name}**"
            if int(starforce) > 0:
                equipment_text += f" ⭐{starforce}"
                
                # 添加卷軸升級資訊
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
            
            # 檢查是否為戒指並且有 special_ring_level
            special_ring_level = equipment.get('special_ring_level')
            if item_slot in ['戒指1', '戒指2', '戒指3', '戒指4'] and special_ring_level:
                try:
                    ring_level = int(special_ring_level)
                    if ring_level > 0:
                        equipment_text += f"```LV {ring_level}\n```"
                except (ValueError, TypeError):
                    pass
            
            # 潛能資訊（詳細顯示）
            if potential_grade != 'None' and potential_1:
                potentials = [p for p in [potential_1, potential_2, potential_3] if p]
                if potentials:
                    # 根據潛能等級添加顏色圖標
                    grade_icon = ""
                    if potential_grade == "傳說":
                        grade_icon = "🟢"  # 綠色
                    elif potential_grade == "罕見":
                        grade_icon = "🟡"  # 黃色
                    elif potential_grade == "稀有":
                        grade_icon = "🟣"  # 紫色
                    elif potential_grade == "特殊":
                        grade_icon = "🔵"  # 藍色
                    
                    equipment_text += f"```{grade_icon}{' / '.join(potentials)}\n```"
            
            # 附加潛能資訊（詳細顯示）
            if add_potential_grade != 'None' and add_potential_1:
                add_potentials = [p for p in [add_potential_1, add_potential_2, add_potential_3] if p]
                if add_potentials:
                    # 根據附加潛能等級添加顏色圖標
                    add_grade_icon = ""
                    if add_potential_grade == "傳說":
                        add_grade_icon = "🟢"  # 綠色
                    elif add_potential_grade == "罕見":
                        add_grade_icon = "🟡"  # 黃色
                    elif add_potential_grade == "稀有":
                        add_grade_icon = "🟣"  # 紫色
                    elif add_potential_grade == "特殊":
                        add_grade_icon = "🔵"  # 藍色
                    
                    equipment_text += f"```{add_grade_icon}{' / '.join(add_potentials)}\n```"
            
            equipment_text += "\n"  # 添加分隔空行
            
            # 分類裝備（使用 item_equipment_slot）
            if item_slot in weapon_slots:
                self.weapon_info.append(equipment_text)
            elif item_slot in armor_slots:
                self.armor_info.append(equipment_text)
            elif item_slot in accessory_slots:
                self.accessory_info.append(equipment_text)
            elif item_slot in other_slots:
                self.other_info.append(equipment_text)
        
    def create_embed(self, category: str) -> discord.Embed:
        """根據分類創建對應的 embed"""
        category_names = {
            "weapon": "武器",
            "armor": "防具", 
            "accessory": "飾品",
            "other": "其他"
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
            # 僅武器
            if self.weapon_info:
                text = ''.join(self.weapon_info)
                if len(text) > 1024:
                    # 分割長文本
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
        
        return embed
    
    @discord.ui.select(
        placeholder="選擇要查看的裝備分類...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(
                label="武器",
                description="主武器、副手武器",
                emoji="⚔️",
                value="weapon"
            ),
            discord.SelectOption(
                label="防具",
                description="帽子、上衣、下裝等",
                emoji="🛡️",
                value="armor"
            ),
            discord.SelectOption(
                label="飾品",
                description="戒指、項鍊、耳環等",
                emoji="💎",
                value="accessory"
            ),
            discord.SelectOption(
                label="其他",
                description="徽章、機械心臟、肩章等",
                emoji="🎖️",
                value="other"
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
        # 返回到角色基本資料
        try:
            from functions.API_functions.CreateCharacterEmbed import create_character_basic_embed
            embed = create_character_basic_embed(self.character_name)
            
            # 創建一個簡單的 view，只顯示按鈕讓用戶選擇返回裝備或重新查詢
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
        # 超時後禁用所有組件
        for item in self.children:
            item.disabled = True


def create_character_equipment_embed(character_name: str) -> dict:
    """
    創建角色裝備資訊的 Discord embed 和 View
    
    Args:
        character_name: 角色名稱
    
    Returns:
        dict: 包含 'embed' 和 'view' 的字典
    """
    ocid = get_character_ocid(character_name)
    
    if not ocid:
        embed = discord.Embed(
            title="錯誤",
            description=f"無法找到角色 '{character_name}' 的資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    # 獲取裝備資料
    character_equipment_data = request_character_itemequipment(ocid)
    
    if not character_equipment_data:
        embed = discord.Embed(
            title="錯誤",
            description=f"無法獲取角色 '{character_name}' 的裝備資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    # 檢查是否至少有一個 preset 的資料
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
    
    # 創建 View 和初始 embed
    view = EquipmentView(character_name, character_equipment_data)
    initial_embed = view.create_embed("weapon")  # 預設顯示武器
    
    return {"embed": initial_embed, "view": view}