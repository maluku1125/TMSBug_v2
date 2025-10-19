import discord
import datetime
from Data.SmallData import worldlogo, worldemoji


class RankingView(discord.ui.View):
    def __init__(self, ranking_data: list = None, character_class: str = None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.ranking_data = ranking_data or []
        self.current_page = 0
        self.items_per_page = 20  # 每頁顯示20筆資料
        self.current_world = "全部"  # 目前選擇的世界
        self.character_class = character_class  # 指定的職業篩選
        
        # 初始化時設定為全伺服器前100名並計算並列排名
        if self.ranking_data:
            top_100 = self.ranking_data[:100]
            self.filtered_data = self._calculate_rankings(top_100)
        else:
            self.filtered_data = []
        
        self.total_pages = max(1, (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page)
        self._update_button_states()
    
    def _calculate_rankings(self, data: list) -> list:
        """計算並列排名"""
        if not data:
            return []
        
        ranked_data = []
        current_rank = 1
        
        for i, character in enumerate(data):
            # 如果不是第一筆資料，檢查是否與前一筆相同等級和經驗
            if i > 0:
                prev_char = data[i-1]
                if (character['character_level'] != prev_char['character_level'] or 
                    character['character_exp_rate'] != prev_char['character_exp_rate']):
                    # 等級或經驗不同，更新排名
                    current_rank = i + 1
            
            # 添加排名資訊到角色資料
            character_with_rank = character.copy()
            character_with_rank['display_rank'] = current_rank
            ranked_data.append(character_with_rank)
        
        return ranked_data
    
    def _filter_by_world(self, world_name: str):
        """根據世界名稱篩選資料"""
        if world_name == "全部":
            # 全伺服器取前100名，並計算並列排名
            top_100 = self.ranking_data[:100]
            self.filtered_data = self._calculate_rankings(top_100)
        else:
            # 特定伺服器取前100名，並計算並列排名
            world_characters = [char for char in self.ranking_data if char['world_name'] == world_name]
            top_100_world = world_characters[:100]
            self.filtered_data = self._calculate_rankings(top_100_world)
        
        self.current_world = world_name
        self.current_page = 0
        self.total_pages = max(1, (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page)
        self._update_button_states()
    
    def _update_button_states(self):
        """更新按鈕狀態"""
        # 找到上一頁和下一頁按鈕
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "⬅️ 上一頁":
                    item.disabled = self.current_page <= 0
                elif item.label == "下一頁 ➡️":
                    item.disabled = self.current_page >= self.total_pages - 1
    
    def create_ranking_embed(self):
        """創建排行榜 Embed"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.filtered_data))
        page_data = self.filtered_data[start_idx:end_idx]
        
        # 創建 Embed
        embed = discord.Embed(
            title='',
            color=discord.Color.gold()
        )
        
        # 設定標題和描述
        if self.current_world == "全部":
            if self.character_class:
                embed_title = f"{self.character_class} 職業等級經驗排行榜 TOP 100"
            else:
                embed_title = f"角色等級經驗排行榜 TOP 100"
            embed.set_author(name=embed_title)
        else:
            if self.character_class:
                embed_title = f"{self.current_world} {self.character_class} 職業排行榜 TOP 100"
            else:
                embed_title = f"{self.current_world} 排行榜 TOP 100"
            # 如果是特定世界，在 Embed 中顯示世界圖標
            if self.current_world in worldlogo:
                embed.set_author(name=embed_title, icon_url=worldlogo[self.current_world])
            else:
                embed.set_author(name=embed_title)
        
        embed.description = f"第 {self.current_page + 1} 頁 / 共 {self.total_pages} 頁"
        
        if not page_data:
            embed.add_field(
                name="📭 暫無資料",
                value="目前沒有符合條件的角色資料",
                inline=False
            )
            return embed
        
        # 添加排行榜資料 - 使用類似 CreateGuildEmbed 的格式
        formatted_characters = []
        for i, character in enumerate(page_data):
            # 使用計算好的並列排名
            display_rank = character.get('display_rank', start_idx + i + 1)
            
            level = character['character_level']
            exp_rate = character['character_exp_rate']
            character_class = character['character_class']
            character_name = character['character_name']
            world_name = character['world_name']
            
            # Fix bracket issues for specific classes (類似 CreateGuildEmbed 的處理)
            character_class = character_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
            character_class = character_class.replace('大魔導士(火、毒)', '大魔導士（火、毒）')
            
            # Format experience as fixed-width string (right-aligned to 5 characters including %)
            exp_text = f"{exp_rate:.1f}%" if exp_rate > 0 else "0.0%"
            exp_display = f"({exp_text:>5s})"
            
            # Limit class name to 9 characters and pad with full-width spaces
            short_class = character_class[:9] if len(character_class) > 9 else character_class
            # Calculate how many full-width spaces needed to pad to 9 characters
            padding_needed = 9 - len(short_class)
            padded_class = short_class + '　' * padding_needed  # Using full-width space (U+3000)
            
            # Limit character name to 10 characters
            short_name = character_name[:10] if len(character_name) > 10 else character_name
            
            # Get world abbreviation (first character)
            world_abbr = world_name[0] if world_name else "?"
            
            # Format the display string with world abbreviation at the front
            if self.current_world == "全部":
                # For all worlds, show world abbreviation
                formatted_characters.append(f"{display_rank:3d}. {world_abbr} Lv.{level:3d}{exp_display} {padded_class} {short_name}")
            else:
                # For specific world, no need to show world abbreviation since it's obvious
                formatted_characters.append(f"{display_rank:3d}. Lv.{level:3d}{exp_display} {padded_class} {short_name}")
        
        # Split into multiple fields if needed (20 characters per field, 分成兩欄)
        characters_per_field = 10  # 每個欄位顯示10筆，總共2欄 = 20筆
        total_characters = len(formatted_characters)
        total_fields = max(1, (total_characters + characters_per_field - 1) // characters_per_field)
        
        for i in range(total_fields):
            start_field_idx = i * characters_per_field
            end_field_idx = min(start_field_idx + characters_per_field, total_characters)
            
            characters_chunk = formatted_characters[start_field_idx:end_field_idx]
            
            # 為每個欄位計算實際的排名範圍
            if characters_chunk:
                first_rank = page_data[start_field_idx].get('display_rank', start_idx + start_field_idx + 1)
                last_rank = page_data[end_field_idx - 1].get('display_rank', start_idx + end_field_idx)
                
                if first_rank == last_rank:
                    field_name = f"🏆 排行榜 (第{first_rank}名)"
                else:
                    field_name = f"🏆 排行榜 (第{first_rank}-{last_rank}名)"
            else:
                field_name = f"🏆 排行榜"
            
            field_value = "```\n" + '\n'.join(characters_chunk) + "\n```"
            
            embed.add_field(
                name=field_name,
                value=field_value,
                inline=False  # 使用 inline=False 來並排顯示
            )
        
        # 添加說明欄位
        embed.add_field(
            name="📝 說明",
            value="1. 等級資料誤差一周\n2. 搜尋該角色可刷新排行\n3. 僅記錄本Bot搜尋過之角色",
            inline=False
        )
        
        # 設定時間戳
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text="TMSBug API 資料查詢")
        
        return embed
    
    @discord.ui.button(label="⬅️ 上一頁", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self._update_button_states()
            embed = self.create_ranking_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="下一頁 ➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_button_states()
            embed = self.create_ranking_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.select(
        placeholder="選擇世界篩選...",
        options=[
            discord.SelectOption(label="全部", value="全部", emoji="🌍"),
            discord.SelectOption(label="艾麗亞", value="艾麗亞", emoji=worldemoji.get("艾麗亞", "⚔️")),
            discord.SelectOption(label="普力特", value="普力特", emoji=worldemoji.get("普力特", "⚔️")),
            discord.SelectOption(label="琉德", value="琉德", emoji=worldemoji.get("琉德", "⚔️")),
            discord.SelectOption(label="優依娜", value="優依娜", emoji=worldemoji.get("優依娜", "⚔️")),
            discord.SelectOption(label="愛麗西亞", value="愛麗西亞", emoji=worldemoji.get("愛麗西亞", "⚔️")),
            discord.SelectOption(label="米特拉", value="米特拉", emoji=worldemoji.get("米特拉", "⚔️")),
            discord.SelectOption(label="殺人鯨", value="殺人鯨", emoji=worldemoji.get("殺人鯨", "⚔️")),
            discord.SelectOption(label="賽蓮", value="賽蓮", emoji=worldemoji.get("賽蓮", "⚔️")),
        ]
    )
    async def world_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_world = select.values[0]
        self._filter_by_world(selected_world)
        embed = self.create_ranking_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        # Disable all components after timeout
        for item in self.children:
            item.disabled = True


def create_ranking_embed(ranking_data: list, include_view: bool = True, character_class: str = None) -> dict:
    try:
        if include_view:
            view = RankingView(ranking_data, character_class)
            embed = view.create_ranking_embed()
            return {
                "embed": embed,
                "view": view,
                "success": True
            }
        else:
            # 創建簡單的 Embed（不含互動功能）
            if not ranking_data:
                embed = discord.Embed(
                    title="❌ 錯誤",
                    description="目前沒有任何角色資料可顯示",
                    color=discord.Color.red()
                )
                return {
                    "embed": embed,
                    "view": None,
                    "success": False
                }
            
            # 限制為前10名
            top_10_data = ranking_data[:10]
            
            embed = discord.Embed(
                title='',
                color=discord.Color.gold()
            )
            if character_class:
                embed.set_author(name=f"🏆 {character_class} 職業等級經驗排行榜 (前10名)")
            else:
                embed.set_author(name="🏆 角色等級經驗排行榜 (前10名)")
            embed.description = "簡易排行榜模式"
            
            # 使用與互動模式相同的格式
            formatted_characters = []
            for i, character in enumerate(top_10_data):
                actual_rank = i + 1
                
                level = character['character_level']
                exp_rate = character['character_exp_rate']
                character_class = character['character_class']
                character_name = character['character_name']
                world_name = character['world_name']
                
                # Fix bracket issues for specific classes
                character_class = character_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
                character_class = character_class.replace('大魔導士(火、毒)', '大魔導士（火、毒）')
                
                # Format experience as fixed-width string
                exp_text = f"{exp_rate:.1f}%" if exp_rate > 0 else "0.0%"
                exp_display = f"({exp_text:>5s})"
                
                # Limit class name to 9 characters and pad with full-width spaces
                short_class = character_class[:9] if len(character_class) > 9 else character_class
                padding_needed = 9 - len(short_class)
                padded_class = short_class + '　' * padding_needed
                
                # Limit character name to 10 characters
                short_name = character_name[:10] if len(character_name) > 10 else character_name
                
                # Get world abbreviation (first character)
                world_abbr = world_name[0] if world_name else "?"
                
                formatted_characters.append(f"{actual_rank:3d}. {world_abbr} Lv.{level:3d}{exp_display} {padded_class} {short_name}")
            
            embed.add_field(
                name="🏆 排行榜",
                value="```\n" + '\n'.join(formatted_characters) + "\n```",
                inline=False
            )
            
            # 添加說明欄位
            embed.add_field(
                name="📝 說明",
                value="1. 等級資料誤差一周\n2. 搜尋該角色可刷新\n3. 僅記錄本bot搜尋過之角色",
                inline=False
            )
            
            embed.timestamp = datetime.datetime.now()
            embed.set_footer(text="TMSBug API 資料查詢")
            
            return {
                "embed": embed,
                "view": None,
                "success": True
            }
            
    except Exception as e:
        print(f"創建排行榜 Embed 時發生錯誤: {e}")
        error_embed = discord.Embed(
            title="❌ 錯誤",
            description=f"創建排行榜時發生錯誤: {str(e)}",
            color=discord.Color.red()
        )
        return {
            "embed": error_embed,
            "view": None,
            "success": False
        }