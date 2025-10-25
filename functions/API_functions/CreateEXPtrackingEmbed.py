import discord
import datetime
from functions.API_functions.API_Request_Character import get_character_ocid, request_character_basic
from Data.SmallData import worldlogo, worldemoji

def get_adjusted_datetime():
    """
    取得調整後的日期時間
    由於 API 兩點才會提供前一日的資料，所以 0:00~2:05 間會出現問題
    在 2:05 之前使用前一天的日期
    """
    now = datetime.datetime.now()
    
    # 如果當前時間在凌晨 0:00 到 2:05 之間，使用前一天的日期
    if now.hour < 2 or (now.hour == 2 and now.minute <= 5):
        adjusted_datetime = now - datetime.timedelta(days=1)
    else:
        adjusted_datetime = now
    
    return adjusted_datetime

def calculate_exp_growth(current_level, current_exp_rate, old_level, old_exp_rate):
    """Calculate experience growth between two points"""
    # Safely handle None values
    try:
        current_level = int(current_level) if current_level is not None else 0
        old_level = int(old_level) if old_level is not None else 0
        current_exp_rate = float(current_exp_rate) if current_exp_rate is not None else 0.0
        old_exp_rate = float(old_exp_rate) if old_exp_rate is not None else 0.0
    except (ValueError, TypeError):
        return 0.0
    
    if current_level == old_level:
        # Same level, only calculate experience difference
        growth_exp = current_exp_rate - old_exp_rate
    else:
        # Different level, calculate complete experience growth
        remaining_old_exp = 100.0 - old_exp_rate
        level_difference = current_level - old_level - 1
        growth_exp = remaining_old_exp + (level_difference * 100.0) + current_exp_rate
    
    return max(0, growth_exp)

def format_growth_display(growth_exp):
    """Format growth experience for display"""
    return f"{growth_exp:7.2f}%"

def create_exp_tracking_embed(character_name: str) -> dict:
    try:
        # Get character OCID
        ocid = get_character_ocid(character_name)
        
        if not ocid:
            embed = discord.Embed(
                title="錯誤",
                description=f"無法找到角色 '{character_name}' 的資訊",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            return {
                "embed": embed,
                "success": False
            }
            
    except Exception as e:
        embed = discord.Embed(
            title="錯誤",
            description=f"查詢角色時發生錯誤: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    try:
        # Get current character data
        current_data = request_character_basic(ocid, use_cache=False)
        
        if not current_data:
            embed = discord.Embed(
                title="錯誤",
                description=f"無法獲取角色 '{character_name}' 的當前資料",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            return {
                "embed": embed,
                "success": False
            }
        
        # Get historical data for different periods
        historical_data = {}
        periods = [7, 30, 90]  # Days to track
        
        # 使用調整後的日期時間來計算歷史資料
        adjusted_datetime = get_adjusted_datetime()
        
        for days in periods:
            try:
                date_str = (adjusted_datetime - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
                data = request_character_basic(ocid, use_cache=False, date=date_str)
                if data:
                    historical_data[days] = data
            except Exception as e:
                print(f"Failed to get data for {days} days ago: {e}")
        
        # Get daily data for the past 7 days
        daily_data = {}
        for i in range(8):  # 0-7 days (including today)
            try:
                if i == 0:
                    # Today's data
                    daily_data[i] = current_data
                else:
                    # 使用調整後的日期時間來計算每日資料
                    date_str = (adjusted_datetime - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                    data = request_character_basic(ocid, use_cache=False, date=date_str)
                    if data:
                        daily_data[i] = data
            except Exception as e:
                print(f"Failed to get data for {i} days ago: {e}")
            
    except Exception as e:
        embed = discord.Embed(
            title="錯誤",
            description=f"獲取角色資料時發生錯誤: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    # Extract current data
    current_level = current_data.get('character_level')
    current_exp_rate = current_data.get('character_exp_rate')
    character_class = current_data.get('character_class', '未知')
    world_name = current_data.get('world_name', '未知')
    guild_name = current_data.get('character_guild_name', '-')
    character_image = current_data.get('character_image', '')
    
    # Fix character class display
    if character_class:
        character_class = character_class.replace('大魔導士(冰、雷)', '大魔導士（冰、雷）')
        character_class = character_class.replace('大魔導士(火、毒)', '大魔導士（火、毒）')
    else:
        character_class = '未知'
    
    # Check if current data is valid
    if current_level is None or current_exp_rate is None:
        embed = discord.Embed(
            title="錯誤",
            description=f"角色 '{character_name}' 的當前資料不完整",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    # Safely handle level and exp_rate
    try:
        current_level = int(current_level)
        current_exp_rate = float(current_exp_rate)
    except (ValueError, TypeError):
        embed = discord.Embed(
            title="錯誤",
            description=f"角色 '{character_name}' 的資料格式錯誤",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    # Calculate multi-period growth for individual fields
    period_data = {}
    
    for days in [7, 30, 90]:
        if days in historical_data:
            old_data = historical_data[days]
            old_level = old_data.get('character_level')
            old_exp_rate = old_data.get('character_exp_rate')
            
            # Check if data is None
            if old_level is None or old_exp_rate is None:
                period_data[days] = "無資料"
            else:
                growth_exp = calculate_exp_growth(current_level, current_exp_rate, old_level, old_exp_rate)
                growth_display = format_growth_display(growth_exp)
                period_data[days] = growth_display
        else:
            period_data[days] = "無資料"
    
    # Calculate daily experience breakdown
    daily_breakdown = []
    day_labels = ["今日", "1日前", "2日前", "3日前", "4日前", "5日前", "6日前", "7日前"]
    
    for i in range(8):  # 0-7 days
        if i in daily_data:
            data = daily_data[i]
            level = data.get('character_level')
            exp_rate = data.get('character_exp_rate')
            
            # Check if data is None
            if level is None or exp_rate is None:
                daily_breakdown.append(f"{day_labels[i]:3s}：無資料")
                continue
            
            # Safely handle level and exp_rate
            try:
                level = int(level)
                exp_rate = float(exp_rate)
            except (ValueError, TypeError):
                daily_breakdown.append(f"{day_labels[i]:3s}：無資料")
                continue
            
            # Calculate daily growth (compared to next day)
            if i < 7 and (i + 1) in daily_data:
                next_data = daily_data[i + 1]
                next_level = next_data.get('character_level')
                next_exp_rate = next_data.get('character_exp_rate')
                
                # Check if next day data is valid
                if next_level is not None and next_exp_rate is not None:
                    daily_growth = calculate_exp_growth(level, exp_rate, next_level, next_exp_rate)
                    daily_growth_display = format_growth_display(daily_growth)
                    # Add star emoji if there's level up (level changed)
                    level_diff = level - int(next_level)
                    if level_diff > 0:
                        if level_diff == 1:
                            star_emoji = "🌟"
                        else:
                            star_emoji = f"🌟x{level_diff}"
                    else:
                        star_emoji = ""
                    daily_breakdown.append(f"{day_labels[i]:3s}：Lv.{level}({exp_rate:4.1f}%)[+{daily_growth_display}]{star_emoji}")
                else:
                    daily_breakdown.append(f"{day_labels[i]:3s}：Lv.{level}({exp_rate:4.1f}%)")
            else:
                daily_breakdown.append(f"{day_labels[i]:3s}：Lv.{level}({exp_rate:4.1f}%)")
        else:
            daily_breakdown.append(f"{day_labels[i]:3s}：無資料")
    
    # Create embed
    embed = discord.Embed(
        title=f"{character_name} 經驗追蹤",
        description=f"{world_name} • {character_class}",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    
    # Set character image as thumbnail
    if character_image:
        embed.set_thumbnail(url=character_image)
    
    # Add current level info
    embed.add_field(
        name="✨ 當前等級",
        value=f"```autohotkey\nLv.{current_level} ({current_exp_rate:.1f}%)```",
        inline=False
    )
    
    # Add individual period growth fields (inline)
    embed.add_field(
        name="📈 7日成長",
        value=f"```autohotkey\n{period_data[7]}```",
        inline=True
    )
    
    embed.add_field(
        name="📈 30日成長", 
        value=f"```autohotkey\n{period_data[30]}```",
        inline=True
    )
    
    embed.add_field(
        name="📈 90日成長",
        value=f"```autohotkey\n{period_data[90]}```",
        inline=True
    )
    
    # Add daily breakdown (Second field)
    embed.add_field(
        name="📅 近七日",
        value=f"```autohotkey\n{chr(10).join(daily_breakdown)}```",
        inline=False
    )
    
    # Set footer with data source info
    embed.set_footer(text="TMSBug API 經驗追蹤系統")
    
    return {
        "embed": embed,
        "success": True
    }
