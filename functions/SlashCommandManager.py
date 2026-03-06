import discord
import datetime
import sqlite3
import json
import asyncio
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CommandUsage:
    """命令使用記錄"""
    timestamp: datetime.datetime
    guild_id: Optional[int]
    guild_name: str
    user_id: int
    user_name: str
    command_type: str
    response_time: Optional[float] = None
    success: bool = True

class SlashCommandManager:
    """斜線命令管理器 v2.0"""
    
    def __init__(self, db_path: str = None, config_path: str = None):
        self.db_path = db_path or 'C:\\Users\\User\\Desktop\\DiscordBotlog\\SlashLog\\slash_commands.db'
        self.config_path = config_path or 'C:\\Users\\User\\Desktop\\DiscordBotlog\\SlashLog\\config.json'
        
        # 確保目錄存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 載入配置
        self.config = self._load_config()
        
        # 初始化資料庫
        self._init_database()
        
        # 記憶體快取
        self._command_cache = {}
        self._guild_cache = {}
        self._user_cache = {}
        self._last_cache_update = datetime.datetime.now()
        self._bot_start_time = time.time()
        
        # 統計計數器
        self._session_commands = 0
        self._session_errors = 0
        
    def _load_config(self) -> Dict:
        """載入配置文件"""
        default_config = {
            "cache_duration": 300,  # 5分鐘
            "max_top_items": 10,
            "db_cleanup_days": 30,
            "enable_performance_tracking": True,
            "log_level": "INFO",
            "backup_enabled": True,
            "dashboard_refresh_interval": 60,
            "statistics_retention_days": 90
        }
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return {**default_config, **config}
        except Exception as e:
            logger.warning(f"無法載入配置文件: {e}")
            
        # 保存默認配置
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict = None):
        """儲存配置文件"""
        try:
            config_to_save = config or self.config
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"無法儲存配置文件: {e}")
    
    def _init_database(self):
        """初始化資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 創建命令使用記錄表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS command_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        guild_id INTEGER,
                        guild_name TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        user_name TEXT NOT NULL,
                        command_type TEXT NOT NULL,
                        response_time REAL,
                        success BOOLEAN DEFAULT 1,
                        created_date DATE DEFAULT (date('now'))
                    )
                ''')
                
                # 創建系統統計表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        cpu_usage REAL,
                        memory_usage REAL,
                        memory_usage_mb REAL,
                        guild_count INTEGER,
                        user_count INTEGER,
                        commands_per_minute REAL
                    )
                ''')
                
                # 創建索引提升查詢效能
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_command_type ON command_usage(command_type)",
                    "CREATE INDEX IF NOT EXISTS idx_guild_id ON command_usage(guild_id)",
                    "CREATE INDEX IF NOT EXISTS idx_created_date ON command_usage(created_date)",
                    "CREATE INDEX IF NOT EXISTS idx_user_id ON command_usage(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_timestamp ON command_usage(timestamp)",
                    "CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_stats(timestamp)"
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                
                conn.commit()
                logger.info("資料庫初始化完成")
                
        except Exception as e:
            logger.error(f"資料庫初始化失敗: {e}")
            raise
    
    @contextmanager
    def _get_db_connection(self):
        """安全的資料庫連接管理"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"資料庫操作錯誤: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def log_command_usage_sync(self, command_type: str, interaction: discord.Interaction, response_time: float = None, success: bool = True):
        """記錄命令使用 - 同步版本"""
        try:
            usage = CommandUsage(
                timestamp=datetime.datetime.now(),
                guild_id=interaction.guild.id if interaction.guild else None,
                guild_name=interaction.guild.name if interaction.guild else "Private Message",
                user_id=interaction.user.id,
                user_name=str(interaction.user),
                command_type=command_type,
                response_time=response_time,
                success=success
            )
            
            # 儲存到資料庫
            self._save_usage_to_db(usage)
            
            # 更新快取和計數器
            self._update_cache(usage)
            self._session_commands += 1
            if not success:
                self._session_errors += 1
            
            # 輸出日誌
            self._log_usage(usage)
            
        except Exception as e:
            logger.error(f"記錄命令使用失敗: {e}")
    
    def _save_usage_to_db(self, usage: CommandUsage):
        """儲存使用記錄到資料庫"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO command_usage 
                    (timestamp, guild_id, guild_name, user_id, user_name, command_type, response_time, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    usage.timestamp,
                    usage.guild_id,
                    usage.guild_name,
                    usage.user_id,
                    usage.user_name,
                    usage.command_type,
                    usage.response_time,
                    usage.success
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"資料庫寫入失敗: {e}")
            # 寫入備用文件
            self._write_to_backup_file(usage)
    
    def _write_to_backup_file(self, usage: CommandUsage):
        """寫入備用文件（當資料庫失敗時）"""
        try:
            backup_path = Path(self.db_path).parent / 'backup_log.txt'
            with open(backup_path, 'a', encoding='utf-8') as f:
                f.write(f"{usage.timestamp}|{usage.guild_name}|{usage.user_name}|{usage.command_type}|{usage.success}\n")
        except Exception as e:
            logger.error(f"備用文件寫入失敗: {e}")
    
    def _update_cache(self, usage: CommandUsage):
        """更新記憶體快取"""
        # 更新命令計數快取
        if usage.command_type in self._command_cache:
            self._command_cache[usage.command_type] += 1
        else:
            self._command_cache[usage.command_type] = 1
            
        # 更新公會計數快取
        if usage.guild_name in self._guild_cache:
            self._guild_cache[usage.guild_name] += 1
        else:
            self._guild_cache[usage.guild_name] = 1
            
        # 更新用戶計數快取
        if usage.user_id in self._user_cache:
            self._user_cache[usage.user_id] += 1
        else:
            self._user_cache[usage.user_id] = 1
    
    def _log_usage(self, usage: CommandUsage):
        """輸出使用日誌"""
        current_time = usage.timestamp.strftime('%H:%M:%S')
        status_icon = "✅" if usage.success else "❌"
        response_info = f", 響應時間: {usage.response_time:.2f}s" if usage.response_time else ""
        
        print(f'{current_time} {status_icon}, 公會: {usage.guild_name}, 用戶: {usage.user_name}, '
              f'命令: {usage.command_type}{response_info}')
        print('-' * 50)
    
    def get_system_stats(self) -> Dict:
        """獲取系統統計信息"""
        try:
            # 獲取當前系統信息
            process = psutil.Process()
            cpu_usage = process.cpu_percent() / psutil.cpu_count()
            memory_info = process.memory_info()
            memory_usage_mb = memory_info.rss / 1024 / 1024
            total_memory_mb = psutil.virtual_memory().total / 1024 / 1024
            memory_usage_percent = memory_usage_mb / total_memory_mb * 100
            
            # 計算運行時間
            runtime_seconds = time.time() - self._bot_start_time
            runtime_minutes, runtime_seconds = divmod(runtime_seconds, 60)
            runtime_hours, runtime_minutes = divmod(runtime_minutes, 60)
            runtime_days, runtime_hours = divmod(runtime_hours, 24)
            
            if runtime_days > 0:
                runtime_str = f"{int(runtime_days)}天{int(runtime_hours)}時{int(runtime_minutes)}分"
            else:
                runtime_str = f"{int(runtime_hours)}小時{int(runtime_minutes)}分"
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage_percent': memory_usage_percent,
                'memory_usage_mb': memory_usage_mb,
                'total_memory_mb': total_memory_mb,
                'runtime_str': runtime_str,
                'runtime_seconds': time.time() - self._bot_start_time,
                'session_commands': self._session_commands,
                'session_errors': self._session_errors,
                'error_rate': (self._session_errors / max(self._session_commands, 1)) * 100
            }
            
        except Exception as e:
            logger.error(f"獲取系統統計失敗: {e}")
            return {}
    
    def save_system_stats(self, guild_count: int = 0, user_count: int = 0):
        """保存系統統計到資料庫"""
        try:
            stats = self.get_system_stats()
            
            # 計算每分鐘命令數
            commands_per_minute = self._session_commands / max(stats.get('runtime_seconds', 1) / 60, 1)
            
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_stats 
                    (cpu_usage, memory_usage, memory_usage_mb, guild_count, user_count, commands_per_minute)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    stats.get('cpu_usage', 0),
                    stats.get('memory_usage_percent', 0),
                    stats.get('memory_usage_mb', 0),
                    guild_count,
                    user_count,
                    commands_per_minute
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存系統統計失敗: {e}")
    
    def get_command_statistics(self, days: int = 30) -> Dict:
        """獲取命令統計"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 獲取命令統計
                cursor.execute('''
                    SELECT command_type, COUNT(*) as count,
                           AVG(response_time) as avg_response_time,
                           SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
                    FROM command_usage 
                    WHERE created_date >= date('now', '-{} days')
                    GROUP BY command_type
                    ORDER BY count DESC
                '''.format(days))
                
                command_stats = []
                for row in cursor.fetchall():
                    command_stats.append({
                        'command': row['command_type'],
                        'count': row['count'],
                        'avg_response_time': row['avg_response_time'] or 0,
                        'error_count': row['error_count'],
                        'success_rate': ((row['count'] - row['error_count']) / row['count']) * 100 if row['count'] > 0 else 0
                    })
                
                # 獲取公會統計
                cursor.execute('''
                    SELECT guild_name, COUNT(*) as count
                    FROM command_usage 
                    WHERE created_date >= date('now', '-{} days')
                    GROUP BY guild_name
                    ORDER BY count DESC
                '''.format(days))
                
                guild_stats = [{'guild': row['guild_name'], 'count': row['count']} 
                              for row in cursor.fetchall()]
                
                # 獲取用戶統計
                cursor.execute('''
                    SELECT user_name, COUNT(*) as count
                    FROM command_usage 
                    WHERE created_date >= date('now', '-{} days')
                    GROUP BY user_id, user_name
                    ORDER BY count DESC
                    LIMIT 10
                '''.format(days))
                
                user_stats = [{'user': row['user_name'], 'count': row['count']} 
                             for row in cursor.fetchall()]
                
                # 獲取每日統計
                cursor.execute('''
                    SELECT created_date, COUNT(*) as count
                    FROM command_usage 
                    WHERE created_date >= date('now', '-{} days')
                    GROUP BY created_date
                    ORDER BY created_date
                '''.format(days))
                
                daily_stats = [{'date': row['created_date'], 'count': row['count']} 
                              for row in cursor.fetchall()]
                
                return {
                    'command_stats': command_stats,
                    'guild_stats': guild_stats,
                    'user_stats': user_stats,
                    'daily_stats': daily_stats,
                    'system_stats': self.get_system_stats()
                }
                
        except Exception as e:
            logger.error(f"獲取統計失敗: {e}")
            return {
                'command_stats': [], 
                'guild_stats': [], 
                'user_stats': [], 
                'daily_stats': [],
                'system_stats': {}
            }
    
    def create_dashboard_embed(self, days: int = 30, bot_client=None) -> discord.Embed:
        """創建詳細的儀表板嵌入"""
        try:
            stats = self.get_command_statistics(days)
            system_stats = stats['system_stats']
            
            embed = discord.Embed(
                title="TMSBug 運營儀表板",
                description=f"過去 {days} 天的詳細統計資料",
                color=0x32EBA7,
                timestamp=datetime.datetime.now()
            )
            
            # 系統狀態
            embed.add_field(
                name="系統狀態",
                value=(
                    f"```yaml\n"
                    f"CPU 使用率: {system_stats.get('cpu_usage', 0):.2f}%\n"
                    f"記憶體使用率: {system_stats.get('memory_usage_percent', 0):.2f}%\n"
                    f"記憶體使用量: {system_stats.get('memory_usage_mb', 0):.2f} MB\n"
                    f"運行時間: {system_stats.get('runtime_str', 'N/A')}\n"
                    f"本次會話命令數: {system_stats.get('session_commands', 0):,}\n"
                    f"錯誤率: {system_stats.get('error_rate', 0):.2f}%\n"
                    f"```"
                ),
                inline=False
            )
            
            # Bot 資訊
            if bot_client:
                guild_count = len(bot_client.guilds)
                user_count = sum([_.member_count or 0 for _ in bot_client.guilds if not _.unavailable])
                command_count = len(bot_client.tree.get_commands())
                
                embed.add_field(
                    name="Bot 資訊",
                    value=(
                        f"```yaml\n"
                        f"指令數量: {command_count}\n"
                        f"伺服器數量: {guild_count:,}\n"
                        f"服務用戶: {user_count:,}\n"
                        f"平均用戶/伺服器: {user_count/max(guild_count,1):.1f}\n"
                        f"```"
                    ),
                    inline=False
                )
            
            # 最熱門命令 (Top 8)
            if stats['command_stats']:
                top_commands = stats['command_stats'][:8]
                command_text = ""
                for cmd in top_commands:
                    success_icon = "🟢" if cmd['success_rate'] > 95 else "🟡" if cmd['success_rate'] > 90 else "🔴"
                    response_time = f"{cmd['avg_response_time']:.2f}s" if cmd['avg_response_time'] > 0 else "N/A"
                    command_text += f"{success_icon} {cmd['command']:17s}| {cmd['count']:>6,} 次 | {response_time:>6s}\n"
                
                embed.add_field(
                    name="最熱門命令 (成功率|使用次數|平均響應)",
                    value=f"```{command_text}```",
                    inline=False
                )
            
            # 最活躍伺服器 (Top 6)
            if stats['guild_stats']:
                top_guilds = stats['guild_stats'][:6]
                guild_text = '\n'.join([
                    f"{i+1}.  {guild['count']:>6,} 次 |  {guild['guild']}"
                    for i, guild in enumerate(top_guilds)
                ])
                
                embed.add_field(
                    name="最活躍伺服器",
                    value=f"```{guild_text}```",
                    inline=False
                )
            
            # 最活躍用戶 (Top 6)
            if stats['user_stats']:
                top_users = stats['user_stats'][:6]
                user_text = '\n'.join([
                    f"{i+1}.  {user['count']:>6,} 次 |  {user['user']}"
                    for i, user in enumerate(top_users)
                ])
                
                embed.add_field(
                    name="最活躍用戶",
                    value=f"```{user_text}```",
                    inline=False
                )
            
            # 每日趨勢 (最近7天)
            if stats['daily_stats']:
                recent_days = stats['daily_stats'][-7:]  # 最近7天
                trend_text = '\n'.join([
                    f"{day['date']:10s} | {day['count']:>6,} 次"
                    for day in recent_days
                ])
                
                embed.add_field(
                    name="每日使用趨勢 (最近7天)",
                    value=f"```{trend_text}```",
                    inline=False
                )
            
            embed.set_footer(text="TMSBug 統計系統 v2.0")
            embed.set_thumbnail(url='https://cdn.discordapp.com/emojis/957283103364235284.webp?size=96&quality=lossless')
            
            return embed
            
        except Exception as e:
            logger.error(f"創建儀表板失敗: {e}")
            return discord.Embed(
                title="❌ 錯誤",
                description="無法載入統計資料",
                color=discord.Color.red()
            )
    
    def get_last_hour_command_count(self) -> int:
        """獲取過去1小時的指令觸發次數"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM command_usage 
                    WHERE timestamp >= datetime('now', '-1 hour')
                ''')
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            logger.error(f"獲取過去1小時指令次數失敗: {e}")
            return 0

    def get_top_commands_simple(self, days: int = 30, limit: int = 5) -> list:
        """獲取最熱門指令（簡化版，只返回名稱和次數）"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT command_type, COUNT(*) as count
                    FROM command_usage 
                    WHERE created_date >= date('now', ?)
                    GROUP BY command_type
                    ORDER BY count DESC
                    LIMIT ?
                ''', (f'-{days} days', limit))
                return [{'command': row['command_type'], 'count': row['count']}
                        for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"獲取最熱門指令失敗: {e}")
            return []

    def get_daily_trend(self, days: int = 7) -> list:
        """獲取每日使用趨勢"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT created_date, COUNT(*) as count
                    FROM command_usage 
                    WHERE created_date >= date('now', ?)
                    GROUP BY created_date
                    ORDER BY created_date
                ''', (f'-{days} days',))
                return [{'date': row['created_date'], 'count': row['count']} 
                        for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"獲取每日趨勢失敗: {e}")
            return []

    def cleanup_old_data(self, days: int = None):
        """清理舊資料"""
        cleanup_days = days or self.config.get('db_cleanup_days', 30)
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 清理命令記錄
                cursor.execute('''
                    DELETE FROM command_usage 
                    WHERE created_date < date('now', '-{} days')
                '''.format(cleanup_days))
                
                deleted_commands = cursor.rowcount
                
                # 清理系統統計
                cursor.execute('''
                    DELETE FROM system_stats 
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(cleanup_days))
                
                deleted_stats = cursor.rowcount
                conn.commit()
                
                logger.info(f"清理了 {deleted_commands} 條命令記錄和 {deleted_stats} 條系統統計")
                
        except Exception as e:
            logger.error(f"清理資料失敗: {e}")

# 全域實例
command_manager = SlashCommandManager()

# 向後相容的函數
def UseSlashCommand(command_type: str, interaction: discord.Interaction, response_time: float = None, success: bool = True):
    """記錄斜線命令使用"""
    command_manager.log_command_usage_sync(command_type, interaction, response_time, success)

def GetSlashCommandUsage(days: int = 30, bot_client=None) -> discord.Embed:
    """獲取命令使用統計"""
    return command_manager.create_dashboard_embed(days, bot_client)

def GetSystemStats() -> Dict:
    """獲取系統統計"""
    return command_manager.get_system_stats()

def SaveSystemStats(guild_count: int = 0, user_count: int = 0):
    """保存系統統計"""
    command_manager.save_system_stats(guild_count, user_count)

def GetLastHourCommandCount() -> int:
    """獲取過去1小時指令次數"""
    return command_manager.get_last_hour_command_count()

def GetTopCommandsSimple(days: int = 30, limit: int = 5) -> list:
    """獲取最熱門指令"""
    return command_manager.get_top_commands_simple(days, limit)

def GetDailyTrend(days: int = 7) -> list:
    """獲取每日使用趨勢"""
    return command_manager.get_daily_trend(days)