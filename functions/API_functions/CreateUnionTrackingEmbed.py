import discord
import datetime
from functions.API_functions.API_Request_union import get_character_ocid, request_user_union
from Data.SmallData import unionicon, worldemoji

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

def calculate_union_level_growth(current_level, old_level):
    """Calculate union level growth between two points"""
    # Safely handle None values
    try:
        current_level = int(current_level) if current_level is not None else 0
        old_level = int(old_level) if old_level is not None else 0
    except (ValueError, TypeError):
        return 0
    
    growth = current_level - old_level
    return max(0, growth)

def calculate_union_artifact_exp_growth(current_exp, old_exp):
    """Calculate union artifact exp growth between two points"""
    # Safely handle None values
    try:
        current_exp = int(current_exp) if current_exp is not None else 0
        old_exp = int(old_exp) if old_exp is not None else 0
    except (ValueError, TypeError):
        return 0
    
    growth = current_exp - old_exp
    return max(0, growth)

def calculate_union_artifact_level_growth(current_level, old_level):
    """Calculate union artifact level growth between two points"""
    # Safely handle None values
    try:
        current_level = int(current_level) if current_level is not None else 0
        old_level = int(old_level) if old_level is not None else 0
    except (ValueError, TypeError):
        return 0
    
    growth = current_level - old_level
    return max(0, growth)

def format_union_level_display(level_growth):
    """Format union level growth for display"""
    if level_growth > 0:
        return f"Lv+{level_growth:,}"
    else:
        return "Lv+0"

def format_artifact_exp_display(exp_growth):
    """Format artifact exp growth for display"""
    if exp_growth > 0:
        return f"+{exp_growth:,} EXP"
    else:
        return "0 EXP"

def format_artifact_level_display(level_growth):
    """Format artifact level growth for display"""
    if level_growth > 0:
        return f"Lv+{level_growth:,}"
    else:
        return "Lv+0"

def format_union_grade_display(union_grade):
    """Convert numbers to Roman numerals in union grade"""
    if not union_grade:
        return union_grade
    
    # 數字轉羅馬數字的對應表
    number_to_roman = {
        '1': 'I',
        '2': 'II', 
        '3': 'III',
        '4': 'IV',
        '5': 'V'
    }
    
    # 將字串中的數字轉換為羅馬數字
    formatted_grade = union_grade
    for number, roman in number_to_roman.items():
        formatted_grade = formatted_grade.replace(f' {number}', f'{roman}')
    
    return formatted_grade

def get_union_icon_url(original_union_grade):
    """Get union icon URL based on original union grade (with numbers)"""
    if not original_union_grade or original_union_grade == '未知':
        return None
    
    # 直接從 unionicon 字典中查找對應的圖片URL
    return unionicon.get(original_union_grade, None)

def create_union_tracking_embed(character_name: str) -> dict:
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
        # Get current union data
        current_data = request_user_union(ocid)
        
        if not current_data:
            embed = discord.Embed(
                title="錯誤",
                description=f"無法獲取角色 '{character_name}' 的當前戰地聯盟資料",
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
                data = request_user_union(ocid, date=date_str)
                if data:
                    historical_data[days] = data
            except Exception as e:
                print(f"Failed to get union data for {days} days ago: {e}")
        
        # Get weekly data for the past 7 weeks
        weekly_data = {}
        for i in range(8):  # 0-7 weeks (including this week)
            try:
                if i == 0:
                    # This week's data (current)
                    weekly_data[i] = current_data
                else:
                    # 使用調整後的日期時間來計算每周資料
                    date_str = (adjusted_datetime - datetime.timedelta(weeks=i)).strftime('%Y-%m-%d')
                    data = request_user_union(ocid, date=date_str)
                    if data:
                        weekly_data[i] = data
            except Exception as e:
                print(f"Failed to get union data for {i} weeks ago: {e}")
            
    except Exception as e:
        embed = discord.Embed(
            title="錯誤",
            description=f"獲取戰地聯盟資料時發生錯誤: {str(e)}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    # Extract current data
    current_union_level = current_data.get('union_level')
    current_union_grade = format_union_grade_display(current_data.get('union_grade', '未知'))
    current_artifact_level = current_data.get('union_artifact_level')
    current_artifact_exp = current_data.get('union_artifact_exp')
    current_artifact_point = current_data.get('union_artifact_point')
    
    # Check if current data is valid
    if current_union_level is None:
        embed = discord.Embed(
            title="錯誤",
            description=f"角色 '{character_name}' 的戰地聯盟資料不完整",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    # Safely handle values
    try:
        current_union_level = int(current_union_level)
        current_artifact_level = int(current_artifact_level) if current_artifact_level is not None else 0
        current_artifact_exp = int(current_artifact_exp) if current_artifact_exp is not None else 0
        current_artifact_point = int(current_artifact_point) if current_artifact_point is not None else 0
    except (ValueError, TypeError):
        embed = discord.Embed(
            title="錯誤",
            description=f"角色 '{character_name}' 的戰地聯盟資料格式錯誤",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        return {
            "embed": embed,
            "success": False
        }
    
    # Calculate multi-period growth for union level, artifact level and artifact exp
    period_data = {}
    
    for days in [7, 30, 90]:
        if days in historical_data:
            old_data = historical_data[days]
            old_union_level = old_data.get('union_level')
            old_artifact_level = old_data.get('union_artifact_level')
            old_artifact_exp = old_data.get('union_artifact_exp')
            
            # Check if data is None
            if old_union_level is None:
                period_data[days] = {
                    "union_level": "無資料", 
                    "artifact_level": "無資料",
                    "artifact_exp": "無資料"
                }
            else:
                # Union level growth
                union_level_growth = calculate_union_level_growth(current_union_level, old_union_level)
                union_level_display = format_union_level_display(union_level_growth)
                
                # Artifact level growth
                if old_artifact_level is not None:
                    artifact_level_growth = calculate_union_artifact_level_growth(current_artifact_level, old_artifact_level)
                    artifact_level_display = format_artifact_level_display(artifact_level_growth)
                else:
                    artifact_level_display = "無資料"
                
                # Artifact exp growth
                if old_artifact_exp is not None:
                    artifact_exp_growth = calculate_union_artifact_exp_growth(current_artifact_exp, old_artifact_exp)
                    artifact_exp_display = format_artifact_exp_display(artifact_exp_growth)
                else:
                    artifact_exp_display = "無資料"
                
                period_data[days] = {
                    "union_level": union_level_display,
                    "artifact_level": artifact_level_display, 
                    "artifact_exp": artifact_exp_display
                }
        else:
            period_data[days] = {
                "union_level": "無資料",
                "artifact_level": "無資料", 
                "artifact_exp": "無資料"
            }
    
    # Calculate weekly union level breakdown
    weekly_breakdown = []
    week_labels = ["本周", "1周前", "2周前", "3周前", "4周前", "5周前", "6周前", "7周前"]
    
    for i in range(8):  # 0-7 weeks
        if i in weekly_data:
            data = weekly_data[i]
            union_level = data.get('union_level')
            union_grade = data.get('union_grade', '未知')
            artifact_level = data.get('union_artifact_level')
            artifact_exp = data.get('union_artifact_exp')
            
            # Check if data is None
            if union_level is None:
                weekly_breakdown.append(f"{week_labels[i]:4s}：無資料")
                continue
            
            # Safely handle values
            try:
                union_level = int(union_level)
                artifact_level = int(artifact_level) if artifact_level is not None else 0
                artifact_exp = int(artifact_exp) if artifact_exp is not None else 0
            except (ValueError, TypeError):
                weekly_breakdown.append(f"{week_labels[i]:4s}：無資料")
                continue
            
            # Calculate weekly growth (compared to next week)
            if i < 7 and (i + 1) in weekly_data:
                next_data = weekly_data[i + 1]
                next_union_level = next_data.get('union_level')
                
                # Check if next week data is valid
                if next_union_level is not None:
                    weekly_level_growth = calculate_union_level_growth(union_level, next_union_level)
                    
                    # Show growth without star emoji
                    if weekly_level_growth > 0:
                        weekly_breakdown.append(f"{week_labels[i]:4s}：Lv.{union_level:,}[+{weekly_level_growth}]")
                    else:
                        weekly_breakdown.append(f"{week_labels[i]:4s}：Lv.{union_level:,}")
                else:
                    weekly_breakdown.append(f"{week_labels[i]:4s}：Lv.{union_level:,}")
            else:
                weekly_breakdown.append(f"{week_labels[i]:4s}：Lv.{union_level:,}")
        else:
            weekly_breakdown.append(f"{week_labels[i]:4s}：無資料")
    
    # Create embed
    embed = discord.Embed(
        title=f"{character_name} 戰地聯盟追蹤",
        description=f"戰地聯盟等級追蹤",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )
    
    # Set union icon as thumbnail
    original_union_grade = current_data.get('union_grade', '未知')
    union_icon_url = get_union_icon_url(original_union_grade)
    if union_icon_url:
        embed.set_thumbnail(url=union_icon_url)
    
    # Add current union info
    embed.add_field(
        name="🏆 當前戰地/神器",
        value=f"```autohotkey\n{current_union_grade}\n戰地等級：{current_union_level:,}\n神器等級：{current_artifact_level}```",
        inline=False
    )
    
    # Add individual period growth fields (inline)
    embed.add_field(
        name="📈 7日成長",
        value=f"```autohotkey\n戰地：{period_data[7]['union_level']}\n神器：{period_data[7]['artifact_level']}```",
        inline=True
    )
    
    embed.add_field(
        name="📈 30日成長", 
        value=f"```autohotkey\n戰地：{period_data[30]['union_level']}\n神器：{period_data[30]['artifact_level']}```",
        inline=True
    )
    
    embed.add_field(
        name="📈 90日成長",
        value=f"```autohotkey\n戰地：{period_data[90]['union_level']}\n神器：{period_data[90]['artifact_level']}```",
        inline=True
    )
    
    # Add weekly breakdown
    embed.add_field(
        name="📅 近七周戰地聯盟等級",
        value=f"```autohotkey\n{chr(10).join(weekly_breakdown)}```",
        inline=False
    )
    
    # Set footer with data source info
    embed.set_footer(text="TMSBug API 戰地聯盟追蹤系統")
    
    return {
        "embed": embed,
        "success": True
    }
