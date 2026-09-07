import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Guild import get_guildid, request_guild_basic
from tmsapi.request import get_character_ocid, request_character_basic
from tmsapi.store.character import get_character_basic_info_db
import datetime
import math
import asyncio

from Data.SmallData import worldlogo
from Data.BotEmojiList import EmojiList




# 一批要抓幾個成員。每抓完一批才回到 event loop 更新進度。
MEMBER_BATCH = 20


def _blank_member(name):
    return {'name': name, 'level': 0, 'exp_rate': 0.0, 'class': '-', 'sort_key': -1}


def _fetch_member(member_name):
    """抓單一成員的等級／職業。**同步、會打 HTTP**，只能在執行緒裡呼叫。"""
    try:
        ocid = get_character_ocid(member_name)
        if not ocid:
            return _blank_member(member_name)
        # 優先用 7 天內的 DB 資料；輪替週期就是 7 天，所以幾乎都會命中
        character_data = get_character_basic_info_db(ocid, cache_days=7)
        if not character_data:
            character_data = request_character_basic(ocid)
        if not character_data:
            return _blank_member(member_name)

        level = character_data.get('character_level', 0)
        exp_rate = character_data.get('character_exp_rate', 0)
        character_class = character_data.get('character_class', '未知') or '未知'
        character_class = character_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
        character_class = character_class.replace('大魔導士(火、毒)', '大魔導士（火、毒）')
        return {'name': member_name, 'level': int(level),
                'exp_rate': float(exp_rate), 'class': character_class,
                'sort_key': int(level) * 100 + float(exp_rate)}
    except Exception:                                       # noqa: BLE001
        return _blank_member(member_name)


def _fetch_members(names):
    return [_fetch_member(n) for n in names]


def create_guild_basic_embed(guild_name: str, world_name: str,
                             include_view: bool = False,
                             build_view: bool = True):
    """
    Create basic guild embed
    
    Args:
        guild_name: Guild name
        world_name: Server name  
        include_view: Whether to include interactive buttons, returns dict{"embed": embed, "view": view} when True, only embed when False
    
    Returns:
        If include_view=True: dict{"embed": embed, "view": view}
        If include_view=False: embed
    """
    if include_view:
        return create_guild_basic_embed_with_view(guild_name, world_name,
                                                  build_view=build_view)
    else:
        return create_guild_basic_embed_without_view(guild_name, world_name)


class GuildView(discord.ui.View):
    def __init__(self, guild_name: str, world_name: str, guild_basic_data: dict):
        super().__init__(timeout=600)  # Increased timeout to 10 minutes
        self.guild_name = guild_name
        self.world_name = world_name
        self.guild_basic_data = guild_basic_data
        self.showing_members = False
        self.showing_detailed_members = False
    
    @discord.ui.button(label="顯示公會成員", style=discord.ButtonStyle.primary, emoji="👥")
    async def show_members_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.showing_members:
            # Show members
            embed = self.create_guild_members_embed()
            button.label = "隱藏公會成員"
            button.emoji = "👤"
            self.showing_members = True
        else:
            # Hide members, return to basic info
            embed = create_guild_basic_embed_without_view(self.guild_name, self.world_name)
            button.label = "顯示公會成員"
            button.emoji = "👥" 
            self.showing_members = False
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="詳細成員資訊", style=discord.ButtonStyle.secondary, emoji="📊")
    async def show_detailed_members_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.showing_detailed_members:
            # Disable all buttons to prevent multiple clicks
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    item.disabled = True
            
            # Update the message immediately to show disabled buttons
            await interaction.response.edit_message(view=self)
            
            try:
                # Show detailed members info (this will take time)
                embed = await self.create_guild_detailed_members_embed(interaction)
                button.label = "隱藏詳細資訊"
                button.emoji = "📈"
                self.showing_detailed_members = True
                
                # Re-enable all buttons
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = False
                        
                await interaction.edit_original_response(embed=embed, view=self)
            except Exception as e:
                # Re-enable buttons even if there's an error
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = False
                        
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"獲取詳細成員資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=error_embed, view=self)
        else:
            # Hide detailed members, return to basic info
            embed = create_guild_basic_embed_without_view(self.guild_name, self.world_name)
            button.label = "詳細成員資訊"
            button.emoji = "📊"
            self.showing_detailed_members = False
            await interaction.response.edit_message(embed=embed, view=self)
    
    def create_guild_members_embed(self) -> discord.Embed:
        """Create embed displaying guild members"""
        # Get world icon URL from worldlogo dictionary
        world_icon_url = worldlogo.get(self.world_name)
        
        embed = discord.Embed(
            title='',
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Set author to world icon if available
        if world_icon_url:
            embed.set_author(name=f"{self.guild_name}", icon_url=world_icon_url)
        
        # Add basic guild information
        guild_info = []
        guild_info.append(f"**等級　**： {self.guild_basic_data.get('guild_level', '未知')}")
        guild_info.append(f"**成員數**： {self.guild_basic_data.get('guild_member_count', 0)}/200")
        guild_info.append(f"**公會長**： {self.guild_basic_data.get('guild_master_name', '未知')}")
        
        embed.add_field(
            name="公會資訊",
            value='\n'.join(guild_info),
            inline=False
        )
        
        # Get guild member list
        guild_members = self.guild_basic_data.get('guild_member', [])
        
        if not guild_members:
            embed.add_field(
                name="公會成員",
                value="無法獲取成員資訊",
                inline=False
            )
            return embed
        
        # Custom sorting function: numbers → uppercase → lowercase → Chinese (Big5)
        def custom_sort_key(name):
            """
            Create sort key for custom ordering:
            1. Numbers (0-9)
            2. English uppercase (A-Z)
            3. English lowercase (a-z)
            4. Chinese characters (Big5 encoding)
            """
            sort_key = []
            for char in name:
                if char.isdigit():
                    # Numbers: priority 0, then the digit value
                    sort_key.append((0, ord(char)))
                elif char.isupper() and char.isascii():
                    # Uppercase English: priority 1, then ASCII value
                    sort_key.append((1, ord(char)))
                elif char.islower() and char.isascii():
                    # Lowercase English: priority 2, then ASCII value
                    sort_key.append((2, ord(char)))
                else:
                    # Chinese and other characters: priority 3, then try Big5 encoding
                    try:
                        # Try to encode in Big5 and use the encoded bytes for sorting
                        big5_bytes = char.encode('big5')
                        sort_key.append((3, int.from_bytes(big5_bytes, byteorder='big')))
                    except UnicodeEncodeError:
                        # If can't encode in Big5, use Unicode code point
                        sort_key.append((3, ord(char)))
            return sort_key
        
        # Sort guild members by custom key
        guild_members = sorted(guild_members, key=custom_sort_key)

        # Group members for display, maximum 17 members per field
        members_per_field = 17
        total_members = len(guild_members)
        total_fields = math.ceil(total_members / members_per_field)
        
        for i in range(total_fields):
            start_idx = i * members_per_field
            end_idx = min(start_idx + members_per_field, total_members)
            
            members_chunk = guild_members[start_idx:end_idx]
            
            # Add numbering for members
            numbered_members = []
            for j, member in enumerate(members_chunk, start=start_idx + 1):
                numbered_members.append(f"{j:3d}. {member}")
            
            field_name = f"公會成員 ({start_idx + 1}-{end_idx})"
            if total_fields == 1:
                field_name = f"公會成員 (共 {total_members} 人)"
            
            embed.add_field(
                name=field_name,
                value="```\n" + '\n'.join(numbered_members) + "\n```",
                inline=True
            )
        
        return embed
    
    async def create_guild_detailed_members_embed(self, interaction: discord.Interaction = None) -> discord.Embed:
        """Create embed displaying detailed guild members information with level and class"""
        # Get world icon URL from worldlogo dictionary
        world_icon_url = worldlogo.get(self.world_name)
        
        embed = discord.Embed(
            title='',
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        # Set author to world icon if available
        if world_icon_url:
            embed.set_author(name=f"{self.guild_name} - 詳細成員資訊", icon_url=world_icon_url)
        
        # Add basic guild information
        guild_info = []
        guild_info.append(f"**等級　**： {self.guild_basic_data.get('guild_level', '未知')}")
        guild_info.append(f"**成員數**： {self.guild_basic_data.get('guild_member_count', 0)}/200")
        guild_info.append(f"**公會長**： {self.guild_basic_data.get('guild_master_name', '未知')}")
        
        embed.add_field(
            name="公會資訊",
            value='\n'.join(guild_info),
            inline=False
        )
        
        # Get guild member list
        guild_members = self.guild_basic_data.get('guild_member', [])
        
        if not guild_members:
            embed.add_field(
                name="公會成員",
                value="無法獲取成員資訊",
                inline=False
            )
            return embed
        
        # Show initial loading message
        loading_embed = discord.Embed(
            title='',
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )
        
        if world_icon_url:
            loading_embed.set_author(name=f"{self.guild_name} - 載入中...", icon_url=world_icon_url)
        
        loading_embed.add_field(
            name="公會資訊",
            value='\n'.join(guild_info),
            inline=False
        )
        
        loading_embed.add_field(
            name="🔄 載入中...",
            value=f"正在從資料庫獲取 {len(guild_members)} 位成員的詳細資訊...\n只顯示排行前20名",
            inline=False
        )
        
        # Update message with loading status
        if interaction:
            await interaction.edit_original_response(embed=loading_embed, view=self)
        
        # ⚠️ 這裡原本是逐筆同步 HTTP（最多 200 個成員 × 2 次請求），
        # 每筆阻塞約 120ms，中間只靠 `await asyncio.sleep(0.05)` 讓出 ——
        # event loop 有七成時間是凍住的，Discord 會噴 "heartbeat blocked"。
        #
        # 改成每 MEMBER_BATCH 個丟一次執行緒，抓完才回 loop 更新進度。
        # 順便拿掉每筆 0.05 秒的人工延遲（200 人就是 10 秒）。
        detailed_members = []
        total_members = len(guild_members)

        for i in range(0, total_members, MEMBER_BATCH):
            batch = guild_members[i:i + MEMBER_BATCH]

            if interaction:
                progress = (i / total_members) * 100 if total_members else 100
                loading_embed.set_field_at(1,
                    name="🔄 載入中...",
                    value=f"正在處理第 {i+1}/{total_members} 位成員..."
                          f" ({progress:.1f}%)\n當前處理: {batch[0]}",
                    inline=False
                )
                try:
                    await interaction.edit_original_response(embed=loading_embed, view=self)
                except Exception:                           # noqa: BLE001
                    pass

            detailed_members.extend(await asyncio.to_thread(_fetch_members, batch))

        # Sort members by level and exp_rate (descending)
        detailed_members.sort(key=lambda x: x['sort_key'], reverse=True)
        
        # 只取前20名
        top_20_members = detailed_members[:20]
        
        # Create final embed
        final_embed = discord.Embed(
            title='',
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        if world_icon_url:
            final_embed.set_author(name=f"{self.guild_name} - 成員排行榜 TOP 20", icon_url=world_icon_url)
        
        final_embed.add_field(
            name="公會資訊",
            value='\n'.join(guild_info),
            inline=False
        )
        
        # 顯示前20名成員，每個field顯示10個
        total_members = len(top_20_members)
        members_per_field = 10
        total_fields = math.ceil(total_members / members_per_field)
        
        for i in range(total_fields):
            start_idx = i * members_per_field
            end_idx = min(start_idx + members_per_field, total_members)
            
            members_chunk = top_20_members[start_idx:end_idx]
            
            # Format member information
            formatted_members = []
            for j, member in enumerate(members_chunk, start=start_idx + 1):
                level = member['level']
                exp_rate = member['exp_rate']
                character_class = member['class']
                name = member['name']
                
                # Format the display string
                if level > 0:
                    # Format experience as fixed-width string (right-aligned to 5 characters including %)
                    exp_text = f"{exp_rate:.1f}%" if exp_rate > 0 else "0.0%"
                    exp_display = f"({exp_text:>5s})"
                    # Limit class name to 9 characters and pad with full-width spaces
                    short_class = character_class[:9] if len(character_class) > 9 else character_class
                    # Calculate how many full-width spaces needed to pad to 9 characters
                    padding_needed = 9 - len(short_class)
                    padded_class = short_class + '　' * padding_needed  # Using full-width space (U+3000)
                    short_name = name[:10] if len(name) > 10 else name
                    formatted_members.append(f"{j:2d}. Lv.{level:3d}{exp_display} {padded_class} {short_name}")
                else:
                    # For members with no data, show with - and sort at end
                    short_name = name[:16] if len(name) > 16 else name
                    formatted_members.append(f"{j:2d}. {character_class:>3s} {short_name}")
            
            field_name = f"TOP 排行榜 ({start_idx + 1}-{end_idx})"
            if total_fields == 1:
                field_name = f"TOP 排行榜 (前 {total_members} 名)"
            
            field_value = "```\n" + '\n'.join(formatted_members) + "\n```"
            
            # Check field value length and truncate if necessary
            if len(field_value) > 1024:
                # Truncate and add warning
                truncated_members = formatted_members[:15]  # Take first 15 members
                field_value = "```\n" + '\n'.join(truncated_members) + "\n[內容過長，已截斷...]\n```"
            
            final_embed.add_field(
                name=field_name,
                value=field_value,
                inline=False
            )

        # Calculate level statistics for all members (not just top 20)
        level_stats = {}
        
        # Count members in each level range
        for member in detailed_members:  # Use all members, not just top_20_members
            level = member['level']
            if level >= 300:
                level_stats['300🏆'] = level_stats.get('300🏆', 0) + 1
            elif level >= 295:
                level_stats['295⬆️'] = level_stats.get('295⬆️', 0) + 1
            elif level >= 290:
                level_stats['290⬆️'] = level_stats.get('290⬆️', 0) + 1
            elif level >= 285:
                level_stats['285⬆️'] = level_stats.get('285⬆️', 0) + 1
            elif level >= 280:
                level_stats['280⬆️'] = level_stats.get('280⬆️', 0) + 1
            elif level >= 275:
                level_stats['275⬆️'] = level_stats.get('275⬆️', 0) + 1
            elif level >= 270:
                level_stats['270⬆️'] = level_stats.get('270⬆️', 0) + 1
            elif level >= 265:
                level_stats['265⬆️'] = level_stats.get('265⬆️', 0) + 1
            elif level >= 260:
                level_stats['260⬆️'] = level_stats.get('260⬆️', 0) + 1
            elif level > 0:  # Members with valid level data but < 260
                level_stats['260⬇️'] = level_stats.get('260⬇️', 0) + 1
            else:  # Members with no data (level = 0)
                level_stats['無資料'] = level_stats.get('無資料', 0) + 1
        
        # Create statistics display
        stats_lines = []
        
        # Order the stats from highest to lowest, including 無資料 at the end
        stat_order = ['300🏆', '295⬆️', '290⬆️', '285⬆️', '280⬆️', '275⬆️', '270⬆️', '265⬆️', '260⬆️', '260⬇️', '無資料']
        
        for level_range in stat_order:
            if level_range in level_stats:
                count = level_stats[level_range]
                stats_lines.append(f"{level_range}： {count}")
        
        # Add statistics field if there are any stats
        if stats_lines:
            final_embed.add_field(
                name="📊 統計",
                value="```\n" + '\n'.join(stats_lines) + "\n```",
                inline=False
            )

        return final_embed


def create_guild_basic_embed_without_view(guild_name: str, world_name: str) -> discord.Embed:
    """Create basic guild embed without view (internal use)"""
    guild_id = get_guildid(guild_name, world_name)
    
    if not guild_id:
        
        embed = discord.Embed(
            title="錯誤",
            description=f"無法找到公會 '{guild_name}' 的資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return embed
    
    guild_basic_data = request_guild_basic(guild_id)

    if not guild_basic_data:
        # If unable to get guild information, return error embed
        embed = discord.Embed(
            title="錯誤",
            description=f"無法獲取公會 '{guild_name}({world_name})' 的詳細資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return embed
    
    # Create embed
    world_name = guild_basic_data.get('world_name', '未知伺服器')
    guild_name = guild_basic_data.get('guild_name', '未知公會')
    
    # Get world icon URL from worldlogo dictionary
    world_icon_url = worldlogo.get(world_name)
    
    embed = discord.Embed(
        title='',
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    # Set author to world icon if available
    if world_icon_url:
        embed.set_author(name=f"{guild_name}", icon_url=world_icon_url)
    
    guild_id_info = []

    # Basic info
    guild_id_info.append(f"**等級　**： {guild_basic_data.get('guild_level', '未知')}")
    guild_id_info.append(f"**成員數**： {guild_basic_data.get('guild_member_count', 0)}/200")
    guild_id_info.append(f"**會長　**： {guild_basic_data.get('guild_master_name', '未知')}")
      
    embed.add_field(
        name="公會資訊",
        value='\n'.join(guild_id_info),
        inline=False
    )

    guild_id_noblesse_skill_info = []

    # Add Noblesse skills
    skill_name_mapping = {
        f"殺BOSS機器": f"{EmojiList.get('Skill_Boss_Slayers', '')}Ｂ傷",
        f"防禦不過是數字": f"{EmojiList.get('Skill_Undeterred', '')}無視", 
        f"以公會之名": f"{EmojiList.get('Skill_For_the_Guild', '')}總傷",
        f"猛烈一擊": f"{EmojiList.get('Skill_Hard_Hitter', '')}爆傷"
    }
    
    for skill in guild_basic_data.get('guild_noblesse_skill', []):
        skill_name = skill.get('skill_name', '未知')
        skill_level = skill.get('skill_level', 0)
        # Use mapping if available, otherwise keep original name
        display_name = skill_name_mapping.get(skill_name, skill_name)
        guild_id_noblesse_skill_info.append(f"**{display_name}**： {skill_level}")

    # Add noblesse skills field to embed if there are any skills
    if guild_id_noblesse_skill_info:
        embed.add_field(
            name="貴族技能",
            value='\n'.join(guild_id_noblesse_skill_info),
            inline=False
        )
    
    return embed


# ⚠️ build_view 的用途
#
# 本函式是同步的、會打數次 HTTP，直接從 async 指令呼叫會凍住 event loop
# （Discord 噴 "heartbeat blocked"）。要用 asyncio.to_thread 丟到執行緒，
# 但 `discord.ui.View` 的建構需要 running event loop，在工作執行緒裡會
# RuntimeError（discord.py 2.5.2 實測）。
#
# 所以 build_view=False 時不建 View，改回傳一個零參數的 view_factory，
# 由呼叫端在 event loop 上呼叫它。呼叫端範例：
#
#     result = await asyncio.to_thread(create_xxx_embed, ..., build_view=False)
#     if result.get("view_factory"):
#         result["view"] = result["view_factory"]()
def create_guild_basic_embed_with_view(guild_name: str, world_name: str,
                                      build_view: bool = True) -> dict:
    """Create guild embed with view"""
    
    guild_id = get_guildid(guild_name, world_name)
    
    if not guild_id:
        
        embed = discord.Embed(
            title="錯誤",
            description=f"無法找到公會 '{guild_name}' 的資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    guild_basic_data = request_guild_basic(guild_id)

    if not guild_basic_data:
        # If unable to get guild information, return error embed
        embed = discord.Embed(
            title="錯誤",
            description=f"無法獲取公會 '{guild_name}({world_name})' 的詳細資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {"embed": embed, "view": None}
    
    # Create basic embed
    embed = create_guild_basic_embed_without_view(guild_name, world_name)
    
    # Create view
    def _make_view():
        return GuildView(guild_name, world_name, guild_basic_data)

    view = _make_view() if build_view else None
    
    return {"embed": embed, "view": view,
            "view_factory": None if build_view else _make_view}



