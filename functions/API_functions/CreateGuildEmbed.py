import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Guild import get_guildid, request_guild_basic
import datetime


def create_guild_basic_embed(guild_name: str, world_name: str) -> discord.Embed:

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
        # 如果無法獲取公會資訊，返回錯誤 embed
        embed = discord.Embed(
            title="錯誤",
            description=f"無法獲取公會 '{guild_name}({world_name})' 的詳細資訊",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return embed
    
    # Create embed
    embed = discord.Embed(
        title=f"{guild_basic_data.get('world_name', '未知伺服器')}  {guild_basic_data.get('guild_name', '未知公會')}",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    guild_id_info = []

    # info
    guild_id_info.append(f"**等級　**: {guild_basic_data.get('guild_level', '未知')}")
    guild_id_info.append(f"**成員數**: {guild_basic_data.get('guild_member_count', 0)}/200")
    guild_id_info.append(f"**會長　**: {guild_basic_data.get('guild_master_name', '未知')}")
      
    embed.add_field(
        name="公會資訊",
        value='\n'.join(guild_id_info),
        inline=False
    )
    guild_id_noblesse_skill_info = []

    # Add Noblesse skills
    for skill in guild_basic_data.get('guild_noblesse_skill', []):
        skill_name = skill.get('skill_name', '未知')
        skill_level = skill.get('skill_level', 0)
        guild_id_noblesse_skill_info.append(f"**{skill_name}**: {skill_level}")

    
    return embed



