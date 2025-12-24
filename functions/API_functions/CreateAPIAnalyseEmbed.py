import discord
import datetime
from Data.SmallData import worldlogo, worldemoji
from functions.API_functions.API_Analyse import (
    get_class_distribution_analysis, 
    get_world_distribution_analysis, 
    get_level_distribution_analysis
)

class LevelFilterModal(discord.ui.Modal):
    def __init__(self, view_instance):
        super().__init__(title="等級篩選")
        self.view_instance = view_instance
        
        self.add_item(discord.ui.TextInput(
            label="最低等級 (1-300)",
            placeholder="例如：200 (留空表示不篩選)",
            style=discord.TextStyle.short,
            max_length=3,
            required=False
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            min_level_input = self.children[0].value.strip()
            
            if min_level_input == "":
                # 清除等級篩選
                self.view_instance.min_level_filter = None
                # 直接更新嵌入，不發送訊息
                embed = self.view_instance.create_analysis_embed()
                await interaction.response.edit_message(embed=embed, view=self.view_instance)
            else:
                min_level = int(min_level_input)
                if min_level < 1 or min_level > 300:
                    await interaction.response.send_message(
                        "❌ 等級必須介於 1-300 之間", 
                        ephemeral=True
                    )
                    return
                
                self.view_instance.min_level_filter = min_level
                # 直接更新嵌入，不發送成功訊息
                embed = self.view_instance.create_analysis_embed()
                await interaction.response.edit_message(embed=embed, view=self.view_instance)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ 請輸入有效的數字 (1-300)", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ 發生錯誤：{str(e)}", 
                ephemeral=True
            )

class APIAnalyseView(discord.ui.View):
    def __init__(self, analysis_type: str = "class"):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.current_analysis_type = analysis_type  # "class", "world", "level"
        self.current_world = "全部"  # Currently selected world
        self.min_level_filter = None  # Minimum level filter
        self._update_button_styles()
    
    def _update_button_styles(self):
        """Update button colors based on current analysis type"""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "📊 職業分析":
                    item.style = discord.ButtonStyle.primary if self.current_analysis_type == "class" else discord.ButtonStyle.secondary
                elif item.label == "🌍 世界分析":
                    item.style = discord.ButtonStyle.primary if self.current_analysis_type == "world" else discord.ButtonStyle.secondary
                elif item.label == "📈 等級分析":
                    item.style = discord.ButtonStyle.primary if self.current_analysis_type == "level" else discord.ButtonStyle.secondary
    
    def create_analysis_embed(self):
        """Create analysis embed based on current type"""
        if self.current_analysis_type == "class":
            return self._create_class_analysis_embed()
        elif self.current_analysis_type == "world":
            return self._create_world_analysis_embed()
        elif self.current_analysis_type == "level":
            return self._create_level_analysis_embed()
        else:
            return self._create_error_embed("未知的分析類型")
    
    def _create_class_analysis_embed(self):
        """Create class analysis embed"""
        # Get class analysis data
        world_filter = None if self.current_world == "全部" else self.current_world
        analysis_result = get_class_distribution_analysis(world_filter, self.min_level_filter)
        
        embed = discord.Embed(
            title='',
            color=discord.Color.blue()
        )
        
        if not analysis_result['success']:
            embed.set_author(name="❌ 職業分析錯誤")
            embed.description = analysis_result['message']
            embed.color = discord.Color.red()
            return embed
        
        # Set title
        level_filter_text = f" (≥{self.min_level_filter}級)" if self.min_level_filter else ""
        if self.current_world == "全部":
            embed_title = f"📊 全伺服器職業分析{level_filter_text}"
            embed.set_author(name=embed_title)
        else:
            embed_title = f"📊 {self.current_world} 職業分析{level_filter_text}"
            if self.current_world in worldlogo:
                embed.set_author(name=embed_title, icon_url=worldlogo[self.current_world])
            else:
                embed.set_author(name=embed_title)
        
        class_stats = analysis_result['data']
        total_characters = analysis_result['total_characters']
        
        embed.description = "職業分析"
        
        if not class_stats:
            embed.add_field(
                name="📭 暫無資料",
                value="目前沒有符合條件的職業資料",
                inline=False
            )
            return embed
        
        # Limit to top 60 classes
        display_stats = class_stats[:60]
        
        # Format class statistics
        formatted_stats = []
        for i, stat in enumerate(display_stats):
            class_name = stat['class_name']
            count = stat['count']
            percentage = stat['percentage']

            # Process class name, max 9 characters
            short_class = class_name[:9] if len(class_name) > 9 else class_name
            
            # Use full-width spaces for Chinese class name alignment
            # Calculate needed full-width spaces (target width 10 character positions)
            padding_needed = 9 - len(short_class)
            padded_class = short_class + '　' * padding_needed  # Use full-width space (U+3000)
            
            # Format display
            formatted_stats.append(f"{i+1:2d}. {padded_class} {percentage:5.2f}%")
        
        # Display in two columns, 30 classes per column
        if len(formatted_stats) > 30:
            # First column (1-30)
            first_half = formatted_stats[:30]
            embed.add_field(
                name="🏆 職業排名 (1-30名)",
                value="```\n" + '\n'.join(first_half) + "\n```",
                inline=True
            )
            
            # Second column (31-60)  
            second_half = formatted_stats[30:60]
            embed.add_field(
                name="🏆 職業排名 (31-60名)",
                value="```\n" + '\n'.join(second_half) + "\n```",
                inline=True
            )
        else:
            # Single column when less than 30 classes
            embed.add_field(
                name=f"🏆 職業排名 (共{len(formatted_stats)}個職業)",
                value="```\n" + '\n'.join(formatted_stats) + "\n```",
                inline=False
            )
        
        # Add description
        embed.add_field(
            name="📝 說明",
            value="1. 統計基於已搜尋過的角色資料\n2. 僅統計轉職為 4/5/6 轉的職業\n3. 百分比計算基於當前選定的伺服器範圍\n4. 點擊其他按鈕切換分析類型",
            inline=False
        )
        
        # Set timestamp
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"分析自 {format(total_characters, ',')} 位玩家的職業分布 | TMSBug API 資料查詢")
        
        return embed
    
    def _create_world_analysis_embed(self):
        """Create world analysis embed"""
        # Get world analysis data
        analysis_result = get_world_distribution_analysis(self.min_level_filter)
        
        embed = discord.Embed(
            title='',
            color=discord.Color.green()
        )
        
        if not analysis_result['success']:
            embed.set_author(name="❌ 世界分析錯誤")
            embed.description = analysis_result['message']
            embed.color = discord.Color.red()
            return embed
        
        level_filter_text = f" (≥{self.min_level_filter}級)" if self.min_level_filter else ""
        embed.set_author(name=f"🌍 全伺服器世界分布分析{level_filter_text}")
        
        world_stats = analysis_result['data']
        total_characters = analysis_result['total_characters']
        
        embed.description = "世界分析"
        
        if not world_stats:
            embed.add_field(
                name="📭 暫無資料",
                value="目前沒有世界資料",
                inline=False
            )
            return embed
        
        # Format world statistics
        formatted_stats = []
        for i, stat in enumerate(world_stats):
            world_name = stat['world_name']
            count = stat['count']
            percentage = stat['percentage']
            
            
            # Limit world name length and align
            short_world = world_name[:5] if len(world_name) > 5 else world_name
            padding_needed = 5 - len(short_world)
            padded_world = short_world + '　' * padding_needed
            
            formatted_stats.append(f"{i+1:2d}. {padded_world} {percentage:5.2f}% ({count:,}人)")
        
        # Display world statistics
        embed.add_field(
            name="🏆 世界排名",
            value="```\n" + '\n'.join(formatted_stats) + "\n```",
            inline=False
        )
        
        # Add description
        embed.add_field(
            name="📝 說明",
            value="1. 統計基於已搜尋過的角色資料\n2. 百分比顯示各世界玩家分布\n3. 點擊其他按鈕切換分析類型",
            inline=False
        )
        
        # Set timestamp
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"分析自 {format(total_characters, ',')} 位玩家的世界分布 | TMSBug API 資料查詢")
        
        return embed
    
    def _create_level_analysis_embed(self):
        """Create level analysis embed"""
        # Get level analysis data
        world_filter = None if self.current_world == "全部" else self.current_world
        analysis_result = get_level_distribution_analysis(world_filter)
        
        embed = discord.Embed(
            title='',
            color=discord.Color.orange()
        )
        
        if not analysis_result['success']:
            embed.set_author(name="❌ 等級分析錯誤")
            embed.description = analysis_result['message']
            embed.color = discord.Color.red()
            return embed
        
        # Set title
        if self.current_world == "全部":
            embed_title = f"📈 全伺服器等級分析"
            embed.set_author(name=embed_title)
        else:
            embed_title = f"📈 {self.current_world} 等級分析"
            if self.current_world in worldlogo:
                embed.set_author(name=embed_title, icon_url=worldlogo[self.current_world])
            else:
                embed.set_author(name=embed_title)
        
        level_stats = analysis_result['data']
        total_characters = analysis_result['total_characters']
        
        embed.description = "等級分析"
        
        if not level_stats:
            embed.add_field(
                name="📭 暫無資料",
                value="目前沒有符合條件的等級資料",
                inline=False
            )
            return embed
        
        # Format level statistics
        formatted_stats = []
        for i, stat in enumerate(level_stats):
            range_name = stat['range_name']
            count = stat['count']
            percentage = stat['percentage']
            
            # Simplified alignment logic: use fixed padding amounts
            # Use same target width regardless of emoji presence
            if '🏆' in range_name:
                padded_range = range_name + '　' * 3  # 300🏆 + 3 full-width spaces
            elif '⬆️' in range_name or '⬇️' in range_name:
                padded_range = range_name + '　' * 3  # 295⬆️ + 3 full-width spaces  
            else:
                # Pure text level ranges
                padded_range = range_name + '　' * (8 - len(range_name))
            
            formatted_stats.append(f"{i+1:2d}. {padded_range} {percentage:5.2f}% ({count:,}人)")
        
        # Display level statistics
        embed.add_field(
            name="📊 等級分布",
            value="```\n" + '\n'.join(formatted_stats) + "\n```",
            inline=False
        )
        
        # Add description
        embed.add_field(
            name="📝 說明",
            value="1. 統計基於已搜尋過的角色資料\n2. 僅統計轉職為 4/5/6 轉的職業\n3. 等級區間依照常見分類劃分\n4. 點擊其他按鈕切換分析類型",
            inline=False
        )
        
        # Set timestamp
        embed.timestamp = datetime.datetime.now()
        embed.set_footer(text=f"分析自 {format(total_characters, ',')} 位玩家的等級分布 | TMSBug API 資料查詢")
        
        return embed
    
    def _create_error_embed(self, error_message: str):
        """Create error embed"""
        embed = discord.Embed(
            title="❌ 錯誤",
            description=error_message,
            color=discord.Color.red()
        )
        embed.timestamp = datetime.datetime.now()
        return embed
    
    @discord.ui.button(label="📊 職業分析", style=discord.ButtonStyle.primary)
    async def class_analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_analysis_type != "class":
            self.current_analysis_type = "class"
            self._update_button_styles()
            embed = self.create_analysis_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="🌍 世界分析", style=discord.ButtonStyle.secondary)
    async def world_analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_analysis_type != "world":
            self.current_analysis_type = "world"
            # 世界分析不需要世界篩選，強制設為全部
            self.current_world = "全部"
            self._update_button_styles()
            embed = self.create_analysis_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="📈 等級分析", style=discord.ButtonStyle.secondary)
    async def level_analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_analysis_type != "level":
            self.current_analysis_type = "level"
            self._update_button_styles()
            embed = self.create_analysis_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="🔢 等級篩選", style=discord.ButtonStyle.secondary, row=1)
    async def level_filter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 只有職業分析和世界分析支援等級篩選
        if self.current_analysis_type in ["class", "world"]:
            modal = LevelFilterModal(self)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(
                "等級篩選僅支援職業分析和世界分析", 
                ephemeral=True
            )
    
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
            discord.SelectOption(label="挑戰者", value="挑戰者", emoji=worldemoji.get("挑戰者", "⚔️")),
        ]
    )
    async def world_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_world = select.values[0]
        
        # World analysis doesn't allow world filtering
        if self.current_analysis_type == "world":
            await interaction.response.defer()
            return
        
        self.current_world = selected_world
        embed = self.create_analysis_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        # Disable all components after timeout
        for item in self.children:
            item.disabled = True


def create_api_analyse_embed(analysis_type: str = "class", include_view: bool = True) -> dict:
    """
    創建 API 分析嵌入
    
    Args:
        analysis_type (str): 分析類型 ("class", "world", "level")
        include_view (bool): 是否包含互動式 View
        
    Returns:
        dict: 包含 embed, view, success 的字典
    """
    try:
        if include_view:
            view = APIAnalyseView(analysis_type)
            embed = view.create_analysis_embed()
            return {
                "embed": embed,
                "view": view,
                "success": True
            }
        else:
            # Simple mode (no interactive features)
            if analysis_type == "class":
                analysis_result = get_class_distribution_analysis()
            elif analysis_type == "world":
                analysis_result = get_world_distribution_analysis()
            elif analysis_type == "level":
                analysis_result = get_level_distribution_analysis()
            else:
                raise ValueError(f"不支援的分析類型: {analysis_type}")
            
            if not analysis_result['success']:
                embed = discord.Embed(
                    title="❌ 錯誤",
                    description=analysis_result['message'],
                    color=discord.Color.red()
                )
                return {
                    "embed": embed,
                    "view": None,
                    "success": False
                }
            
            # Create simple embed
            embed = discord.Embed(
                title=f"{'職業' if analysis_type == 'class' else '世界' if analysis_type == 'world' else '等級'}分析 (簡易模式)",
                color=discord.Color.blue()
            )
            
            data = analysis_result['data'][:10]  # Show only top 10
            total_characters = analysis_result['total_characters']
            
            embed.description = f"分析自 {format(total_characters, ',')} 位玩家"
            
            formatted_stats = []
            for i, stat in enumerate(data):
                if analysis_type == "class":
                    name = stat['class_name']
                elif analysis_type == "world":
                    name = stat['world_name']
                else:  # level
                    name = stat['range_name']
                
                count = stat['count']
                percentage = stat['percentage']
                
                # Use same format as full mode
                if analysis_type == "class":
                    short_name = name[:10] if len(name) > 10 else name
                    # Use full-width spaces for class name alignment
                    padding_needed = 10 - len(short_name)
                    padded_name = short_name + '　' * padding_needed
                    formatted_stats.append(f"{i+1:2d}. {padded_name} {percentage:5.2f}%")
                else:
                    formatted_stats.append(f"{i+1:2d}. {name} {percentage:5.2f}% ({count:,}人)")
            
            embed.add_field(
                name="前10名統計",
                value="```\n" + '\n'.join(formatted_stats) + "\n```",
                inline=False
            )
            
            embed.timestamp = datetime.datetime.now()
            embed.set_footer(text="TMSBug API 資料查詢 (簡易模式)")
            
            return {
                "embed": embed,
                "view": None,
                "success": True
            }
            
    except Exception as e:
        error_embed = discord.Embed(
            title="❌ 錯誤",
            description=f"創建分析嵌入時發生錯誤: {str(e)}",
            color=discord.Color.red()
        )
        return {
            "embed": error_embed,
            "view": None,
            "success": False
        }