import discord
import datetime
import unicodedata
from Data.SmallData import worldlogo, worldemoji
# 改讀 build.py 產出的 JSON（ARCHITECTURE.md §14 階段 3）——
# 這九項分析原本 Bot 與網站各有一份實作，答案已經開始分歧。
from tmsapi.stats import (
    get_class_distribution_analysis,
    get_world_distribution_analysis,
    get_level_distribution_analysis
)
from tmsapi.stats import (
    get_gem_ranking_normalized, get_equipment_ownership,
    get_glove_crit_distribution, get_familiar_distribution, get_hat_cd_distribution,
    get_classes_with_stats, get_soul_weapon_distribution, get_champion_grade_distribution)

# 寶玉屬性標籤；需顯示「等效主屬」的職業類型
_GEM_STAT_LABEL = {'str': 'STR', 'dex': 'DEX', 'int': 'INT', 'luk': 'LUK',
                   'str+dex+luk': 'S+D+L', 'max_hp': 'HP'}
_GEM_NORMALIZED = {'str+dex+luk', 'max_hp'}

# 過長職業名縮短（避免職業分析兩欄排版折行）
_CLASS_SHORT_NAME = {
    '大魔導士(火、毒)': '火毒大魔導', '大魔導士（火、毒）': '火毒大魔導',
    '大魔導士(冰、雷)': '冰雷大魔導', '大魔導士（冰、雷）': '冰雷大魔導',
}

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
            # 過長職業名先縮短（火毒/冰雷大魔導），避免兩欄排版折行
            class_name = _CLASS_SHORT_NAME.get(stat['class_name'], stat['class_name'])
            count = stat['count']
            percentage = stat['percentage']

            # 補齊到 5 格全形（縮短後最長職業名約 5 字），百分比 1 位小數，縮減行寬避免折行
            short_class = class_name[:5] if len(class_name) > 5 else class_name
            padding_needed = 5 - len(short_class)
            padded_class = short_class + '　' * padding_needed  # Use full-width space (U+3000)

            # Format display
            formatted_stats.append(f"{i+1:2d}.{padded_class}{percentage:.1f}%")
        
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

        # 虛線足標（撐寬 embed，兩欄較不易折行）
        embed.set_footer(text=f"{'-' * 22}共 {total_characters:,} 名角色{'-' * 22}")

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

    @discord.ui.button(label="💎 寶玉排行", style=discord.ButtonStyle.secondary, row=1)
    async def gem_ranking_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = get_gem_ranking_normalized(100)
        view = GemRankingView(data)
        await interaction.response.edit_message(embed=view.create_embed(), view=view)

    @discord.ui.button(label="💠 裝備分析", style=discord.ButtonStyle.secondary, row=1)
    async def equip_analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = EquipAnalyseView()
        await interaction.response.edit_message(embed=view.create_embed(), view=view)

    @discord.ui.button(label="🧢 CD帽分析", style=discord.ButtonStyle.secondary, row=2)
    async def hatcd_analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HatCDAnalyseView()
        await interaction.response.edit_message(embed=view.create_embed(), view=view)

    @discord.ui.button(label="👑 冠軍分析", style=discord.ButtonStyle.secondary, row=2)
    async def champion_analysis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChampionAnalyseView()
        await interaction.response.edit_message(embed=view.create_embed(), view=view)

    @discord.ui.select(
        placeholder="選擇世界篩選...",
        options=[
            discord.SelectOption(label="全部", value="全部", emoji="🌍"),
            discord.SelectOption(label="艾麗亞", value="艾麗亞", emoji=worldemoji.get("艾麗亞", "⚔️")),
            discord.SelectOption(label="普力特", value="普力特", emoji=worldemoji.get("普力特", "⚔️")),
            discord.SelectOption(label="琉德", value="琉德", emoji=worldemoji.get("琉德", "⚔️")),
            discord.SelectOption(label="優依娜", value="優依娜", emoji=worldemoji.get("優依娜", "⚔️")),
            discord.SelectOption(label="愛麗西亞", value="愛麗西亞", emoji=worldemoji.get("愛麗西亞", "⚔️")),
            discord.SelectOption(label="殺人鯨", value="殺人鯨", emoji=worldemoji.get("殺人鯨", "⚔️")),
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


def _dw(text: str) -> int:
    """字串的顯示寬度（全形字算 2 欄）"""
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in text)


def _padw(text: str, width: int) -> str:
    """補半形空白到指定顯示寬度，讓全形/半形混排也能對齊"""
    return text + ' ' * max(0, width - _dw(text))


def _pct(n: int, total: int) -> str:
    return f"{n:,} ({n / total * 100:.1f}%)" if total else f"{n:,} (—)"


class EquipAnalyseView(discord.ui.View):
    """裝備／萌獸統計分析（下拉切換分析類型；帽子分析可分頁）"""

    HAT_MIN_LEVEL = 290

    def __init__(self):
        super().__init__(timeout=300)
        self.mode = 'ownership'

    # ---------- Embed ----------
    def create_embed(self) -> discord.Embed:
        if self.mode == 'soul':
            return self._embed_soul()
        if self.mode == 'glove':
            return self._embed_glove()
        if self.mode == 'familiar':
            return self._embed_familiar()
        return self._embed_ownership()

    def _base(self, title: str) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.blurple())
        embed.set_author(name=title)
        embed.timestamp = datetime.datetime.now()
        return embed

    def _embed_ownership(self) -> discord.Embed:
        d = get_equipment_ownership()
        embed = self._base("💠 全服特殊裝備持有率")
        total = d['total']
        if not total:
            embed.description = "尚無統計資料（需先執行裝備統計刷新）"
            return embed
        embed.description = f"統計母數：**{total:,}** 位角色（已完成裝備統計）"
        width = max(len(n) for n, _ in d['items'])
        lines = "\n".join(f"{n.ljust(width, '　')} : {_pct(c, total)}"
                          for n, c in sorted(d['items'], key=lambda x: -x[1]))
        embed.add_field(name="持有人數 / 佔比",
                        value=f"```autohotkey\n{lines}\n```", inline=False)
        return embed

    def _embed_glove(self) -> discord.Embed:
        embed = self._base("🧤 手套爆擊傷害排數分布")
        embed.description = "依主潛能中「爆擊傷害」排數統計"
        data = get_glove_crit_distribution()
        any_data = False
        for lv, d in data.items():
            total = d['total']
            if not total:
                continue
            any_data = True
            lines = "\n".join(f"{i}排 : {_pct(d[i], total)}" for i in (0, 1, 2, 3))
            embed.add_field(name=f"LV{lv}+ （{total:,} 人）",
                            value=f"```autohotkey\n{lines}\n```", inline=False)
        if not any_data:
            embed.description = "尚無統計資料（需先執行裝備統計刷新）"
        return embed

    def _embed_familiar(self) -> discord.Embed:
        d = get_familiar_distribution()
        embed = self._base("🐾 萌獸與羈絆槽統計")
        total = d['total']
        if not total:
            embed.description = "尚無統計資料（需先執行裝備統計刷新）"
            return embed
        embed.description = f"統計母數：**{total:,}** 位角色"
        o = d['options']
        embed.add_field(
            name="召喚中萌獸的三排組合",
            value=("```autohotkey\n"
                   f"三排終傷　　 : {_pct(o.get('3final', 0), total)}\n"
                   f"雙終傷+物/魔 : {_pct(o.get('2final_atk', 0), total)}\n"
                   f"雙終傷+其他　: {_pct(o.get('2final_other', 0), total)}\n"
                   f"其他/未召喚　: {_pct(o.get('none', 0), total)}\n"
                   f"特殊萌獸　　 : {_pct(d['special'], total)}\n"
                   "```"),
            inline=False)
        lk = d['links']
        embed.add_field(
            name="羈絆槽啟用",
            value=("```autohotkey\n"
                   f"連結1　: {_pct(lk['1'], total)}\n"
                   f"連結2　: {_pct(lk['2'], total)}\n"
                   f"連結3　: {_pct(lk['3'], total)}\n"
                   f"VIP　　: {_pct(lk['VIP'], total)}\n"
                   "```"),
            inline=False)
        return embed

    def _embed_soul(self) -> discord.Embed:
        d = get_soul_weapon_distribution()
        embed = self._base("🗡️ 魂武等級分布")
        total = d['total']
        if not total:
            embed.description = "尚無統計資料（需先執行裝備統計刷新）"
            return embed
        embed.description = f"統計母數：**{total:,}** 位角色"
        has_soul = d['has_soul']
        width = max(_dw(lbl) for lbl, _ in d['buckets'])
        rows = [f"{_padw(lbl, width)} : {_pct(n, total)}"
                for lbl, n in d['buckets']]
        embed.add_field(name="等級區間 / 人數 / 佔比",
                        value=f"```autohotkey\n" + chr(10).join(rows) + f"\n```",
                        inline=False)
        embed.add_field(name="摘要",
                        value=(f"```autohotkey\n"
                               f"有魂武 : {_pct(has_soul, total)}\n"
                               f"無魂武 : {_pct(total - has_soul, total)}\n"
                               f"```"),
                        inline=False)
        return embed

    # ---------- 元件 ----------
    @discord.ui.select(
        placeholder="選擇分析項目...",
        options=[
            discord.SelectOption(label="特殊裝備持有率", value="ownership", emoji="💠",
                                 description="輪迴碑石 / 全面控制核心 / 創世胸章"),
            discord.SelectOption(label="手套爆傷排數", value="glove", emoji="🧤",
                                 description="LV285 / 290 / 295 以上各 0~3 排"),
            discord.SelectOption(label="萌獸與羈絆槽", value="familiar", emoji="🐾",
                                 description="召喚中萌獸組合、連結1/2/3/VIP"),
            discord.SelectOption(label="魂武等級", value="soul", emoji="🗡️",
                                 description="魂武等級分布與持有率"),
        ])
    async def mode_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.mode = select.values[0]
        self.page = 0
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="🔙 返回分析", style=discord.ButtonStyle.primary, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = APIAnalyseView()
        await interaction.response.edit_message(embed=view.create_analysis_embed(), view=view)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class HatCDAnalyseView(discord.ui.View):
    """CD帽分析：進入為全職業總覽，可用下拉選單切換單一職業"""

    LEVELS = (295, 290)     # 同時顯示的等級門檻（高→低）
    MIN_LEVEL = 290         # 職業清單母體門檻
    CLASSES_PER_PAGE = 24   # 下拉選單上限 25（保留 1 個給「全職業總覽」）

    def __init__(self):
        super().__init__(timeout=300)
        self.character_class = None      # None = 全職業總覽
        self.class_page = 0
        self._classes = get_classes_with_stats(self.MIN_LEVEL)
        self._refresh_options()

    # ---------- 下拉選單內容 ----------
    def _refresh_options(self):
        total_pages = max(1, (len(self._classes) + self.CLASSES_PER_PAGE - 1) // self.CLASSES_PER_PAGE)
        self.class_page = max(0, min(self.class_page, total_pages - 1))
        start = self.class_page * self.CLASSES_PER_PAGE
        page_classes = self._classes[start:start + self.CLASSES_PER_PAGE]

        options = [discord.SelectOption(
            label="全職業總覽", value="__all__", emoji="🌐",
            default=self.character_class is None)]
        for cls, n in page_classes:
            options.append(discord.SelectOption(
                label=cls[:100], value=cls[:100], description=f"{n:,} 人",
                default=(cls == self.character_class)))

        select = self.children[0]
        select.options = options
        select.placeholder = (f"選擇職業…（第 {self.class_page + 1}/{total_pages} 頁）"
                              if total_pages > 1 else "選擇職業…")

    # ---------- Embed ----------
    def create_embed(self) -> discord.Embed:
        scope = self.character_class or "全職業"
        embed = discord.Embed(color=discord.Color.teal())
        embed.set_author(name=f"🧢 CD帽分析 — {scope}")
        embed.timestamp = datetime.datetime.now()

        data = {lv: get_hat_cd_distribution(lv, self.character_class) for lv in self.LEVELS}
        if not any(d['total'] for d in data.values()):
            embed.description = ("尚無統計資料（需先執行裝備統計刷新）"
                                 if self.character_class is None
                                 else f"「{scope}」尚無統計資料")
            return embed

        embed.description = ("CD秒數 = 帽子潛能＋附加潛能的「技能冷卻時間」總和\n"
                             + "　".join(f"**LV{lv}+**：{data[lv]['total']:,} 人" for lv in self.LEVELS))

        # 兩個等級門檻並列比較（同一表格，便於看出高等玩家的差異）
        all_cds = sorted({cd for d in data.values() for cd in d['counts']}, reverse=True)
        header = "CD  " + "".join(f"│ LV{lv}+ 人數   佔比 " for lv in self.LEVELS)
        lines = [header, "─" * len(header)]
        for cd in all_cds:
            row = f"-{cd}  "
            for lv in self.LEVELS:
                d = data[lv]
                n = d['counts'].get(cd, 0)
                p = (n / d['total'] * 100) if d['total'] else 0
                row += f"│{n:>8,} {p:>6.1f}% "
            lines.append(row)
        embed.add_field(name="冷卻秒數分布",
                        value="```autohotkey\n" + "\n".join(lines) + "\n```", inline=False)

        # 有/無 CD帽摘要
        summary = []
        for lv in self.LEVELS:
            d = data[lv]
            t = d['total']
            with_cd = sum(n for cd, n in d['counts'].items() if cd > 0)
            summary.append(f"LV{lv}+　有CD帽 : {_pct(with_cd, t)}　無CD帽 : {_pct(d['counts'].get(0, 0), t)}")
        embed.add_field(name="摘要", value="```autohotkey\n" + "\n".join(summary) + "\n```",
                        inline=False)
        return embed

    # ---------- 元件 ----------
    @discord.ui.select(placeholder="選擇職業…", options=[
        discord.SelectOption(label="全職業總覽", value="__all__", emoji="🌐")])
    async def class_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = select.values[0]
        self.character_class = None if value == "__all__" else value
        self._refresh_options()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="⬅️ 職業選單上頁", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.class_page > 0:
            self.class_page -= 1
            self._refresh_options()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="➡️ 職業選單下頁", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = max(1, (len(self._classes) + self.CLASSES_PER_PAGE - 1) // self.CLASSES_PER_PAGE)
        if self.class_page < total_pages - 1:
            self.class_page += 1
            self._refresh_options()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="🔙 返回分析", style=discord.ButtonStyle.primary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = APIAnalyseView()
        await interaction.response.edit_message(embed=view.create_analysis_embed(), view=view)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class ChampionAnalyseView(discord.ui.View):
    """聯盟冠軍等級分析：全職業總覽，可用下拉選單切換單一職業"""

    MIN_LEVEL = 0
    CLASSES_PER_PAGE = 24

    def __init__(self):
        super().__init__(timeout=300)
        self.character_class = None
        self.class_page = 0
        self._classes = get_classes_with_stats(self.MIN_LEVEL)
        self._refresh_options()

    def _refresh_options(self):
        total_pages = max(1, (len(self._classes) + self.CLASSES_PER_PAGE - 1) // self.CLASSES_PER_PAGE)
        self.class_page = max(0, min(self.class_page, total_pages - 1))
        start = self.class_page * self.CLASSES_PER_PAGE
        page_classes = self._classes[start:start + self.CLASSES_PER_PAGE]
        options = [discord.SelectOption(
            label="全職業總覽", value="__all__", emoji="🌐",
            default=self.character_class is None)]
        for cls, n in page_classes:
            options.append(discord.SelectOption(
                label=cls[:100], value=cls[:100], description=f"{n:,} 人",
                default=(cls == self.character_class)))
        select = self.children[0]
        select.options = options
        select.placeholder = (f"選擇職業…（第 {self.class_page + 1}/{total_pages} 頁）"
                              if total_pages > 1 else "選擇職業…")

    def create_embed(self) -> discord.Embed:
        d = get_champion_grade_distribution(self.MIN_LEVEL, self.character_class)
        scope = self.character_class or "全職業"
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=f"👑 聯盟冠軍等級分析 — {scope}")
        embed.timestamp = datetime.datetime.now()

        total = d['total']
        if not total:
            embed.description = ("尚無統計資料（需先執行裝備統計刷新）"
                                 if self.character_class is None
                                 else f"「{scope}」尚無統計資料")
            return embed

        embed.description = f"統計母數：**{total:,}** 位角色"
        grades = d['grades']
        champ = d['is_champion']
        # 只列實際冠軍等級（不含非冠軍），佔比以「冠軍總數」為分母
        rows = []
        for g, n in grades:
            if g == "none":
                continue
            pct = (n / champ * 100) if champ else 0
            rows.append(f"{_padw(g, 4)} : {n:>6,} ({pct:5.1f}%)")
        embed.add_field(name="冠軍等級 / 人數 / 佔比（佔冠軍總數）",
                        value=f"```autohotkey\n" + chr(10).join(rows) + f"\n```",
                        inline=False)
        embed.add_field(name="摘要",
                        value=(f"```autohotkey\n"
                               f"是聯盟冠軍 : {_pct(champ, total)}\n"
                               f"非冠軍　　 : {_pct(total - champ, total)}\n"
                               f"```"),
                        inline=False)
        return embed

    @discord.ui.select(placeholder="選擇職業…", options=[
        discord.SelectOption(label="全職業總覽", value="__all__", emoji="🌐")])
    async def class_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = select.values[0]
        self.character_class = None if value == "__all__" else value
        self._refresh_options()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="⬅️ 職業選單上頁", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.class_page > 0:
            self.class_page -= 1
            self._refresh_options()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="➡️ 職業選單下頁", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_pages = max(1, (len(self._classes) + self.CLASSES_PER_PAGE - 1) // self.CLASSES_PER_PAGE)
        if self.class_page < total_pages - 1:
            self.class_page += 1
            self._refresh_options()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="🔙 返回分析", style=discord.ButtonStyle.primary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = APIAnalyseView()
        await interaction.response.edit_message(embed=view.create_analysis_embed(), view=view)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class GemRankingView(discord.ui.View):
    """伊妮絲的寶玉排行（分頁，每頁 20 筆，依等效主屬排序）"""
    def __init__(self, data: list):
        super().__init__(timeout=300)
        self.data = data  # [(name, gem_stat, raw_value, equiv), ...]
        self.items_per_page = 20
        self.current_page = 0
        self.total_pages = max(1, (len(data) + self.items_per_page - 1) // self.items_per_page)

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(color=discord.Color.purple())
        embed.set_author(name="💎 伊妮絲的寶玉排行 TOP 100")
        embed.description = f"第 {self.current_page + 1} 頁 / 共 {self.total_pages} 頁"
        embed.timestamp = datetime.datetime.now()

        start = self.current_page * self.items_per_page
        page = self.data[start:start + self.items_per_page]
        if not page:
            embed.add_field(name="📭 暫無資料", value="目前沒有寶玉資料（需先刷新裝備統計）", inline=False)
            return embed

        # 格式：<排序> <等效屬性> <暱稱>。暱稱放最後、不補寬度，避免長名字造成 embed 跑版
        equiv_w = max(len(f"{e:,}") for _, _, _, e in page)
        lines = []
        for i, (name, stat, raw, equiv) in enumerate(page):
            rank = start + i + 1
            lines.append(f"{rank:>3d}. {equiv:>{equiv_w},} {name}")
        embed.add_field(name="​", value="```\n" + "\n".join(lines) + "\n```", inline=False)
        embed.set_footer(text=f"{'-' * 19}寶玉排行 共 {len(self.data)} 人{'-' * 19}")
        return embed

    @discord.ui.button(label="⬅️ 上一頁", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="➡️ 下一頁", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="🔙 返回分析", style=discord.ButtonStyle.primary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = APIAnalyseView("class")
        await interaction.response.edit_message(embed=view.create_analysis_embed(), view=view)

    async def on_timeout(self):
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
            # 寶玉排行用專屬分頁 View
            if analysis_type == "gem":
                view = GemRankingView(get_gem_ranking_normalized(100))
                return {"embed": view.create_embed(), "view": view, "success": True}
            if analysis_type == "equip":
                view = EquipAnalyseView()
                return {"embed": view.create_embed(), "view": view, "success": True}
            if analysis_type == "hatcd":
                view = HatCDAnalyseView()
                return {"embed": view.create_embed(), "view": view, "success": True}
            if analysis_type == "champion":
                view = ChampionAnalyseView()
                return {"embed": view.create_embed(), "view": view, "success": True}
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