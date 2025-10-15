import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Guild import get_guildid, request_guild_basic
import datetime
import math

worldlogo = {
    "艾麗亞" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/ai_li_ya.png",
    "普力特" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/pu_li_te.png",
    "琉德" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/liu_de.png",
    "優依娜" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/you_yi_na.png",
    "愛麗西亞" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/ai_li_xi_ya.png",
    "殺人鯨" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/sha_ren_jing.png",
    "賽蓮" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/silien.png",
    "米特拉" : "https://tw.hicdn.beanfun.com/beanfun/event/MapleStory/UnionWebRank/assets/img/reboot.png",
}

def create_guild_basic_embed(guild_name: str, world_name: str, include_view: bool = False):
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
        return create_guild_basic_embed_with_view(guild_name, world_name)
    else:
        return create_guild_basic_embed_without_view(guild_name, world_name)


class GuildView(discord.ui.View):
    def __init__(self, guild_name: str, world_name: str, guild_basic_data: dict):
        super().__init__(timeout=300)
        self.guild_name = guild_name
        self.world_name = world_name
        self.guild_basic_data = guild_basic_data
        self.showing_members = False
    
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
        
        # Sort guild members by name
        guild_members = sorted(guild_members)
        
        # Group members for display, maximum 20 members per field
        members_per_field = 20
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
        "殺BOSS機器": "Ｂ傷",
        "防禦不過是數字": "無視", 
        "以公會之名": "總傷",
        "猛烈一擊": "爆傷"
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


def create_guild_basic_embed_with_view(guild_name: str, world_name: str) -> dict:
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
    view = GuildView(guild_name, world_name, guild_basic_data)
    
    return {"embed": embed, "view": view}



