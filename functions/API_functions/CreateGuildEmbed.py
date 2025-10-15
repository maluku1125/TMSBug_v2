import discord
from discord import app_commands
from discord.ext import commands

from functions.API_functions.API_Request_Guild import get_guildid, request_guild_basic
import datetime

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

    # info
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



