"""
API_RequestLogger.py
=====================
記錄每一筆 Nexon Open API 請求，供統計：
  - 總次數
  - 每個 API(endpoint) 的次數
  - 每個 OCID 的次數

特性：
  - 每一季一個 SQLite 檔（API_Log_2026Q2.db），由使用者自行備份/刪除
  - 不記耗時
  - 記錄失敗絕不影響 API 本身（全程 try/except 吞例外）
  - endpoint 與 ocid 直接從請求 URL 解析，呼叫端不必額外傳參數
"""

import os
import sqlite3
import datetime
import requests
from urllib.parse import urlparse, parse_qs

# API 請求 log 存放位置（專屬子資料夾，會自動建立）
LOG_DIR = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\requestlog'


def _current_db_path() -> str:
    """依目前季度回傳對應的 DB 路徑，例如 .../API_Log_2026Q2.db"""
    now = datetime.datetime.now()
    quarter = (now.month - 1) // 3 + 1
    return os.path.join(LOG_DIR, f"API_Log_{now.year}Q{quarter}.db")


def _ensure_table(conn: sqlite3.Connection):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS api_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TIMESTAMP NOT NULL,
            endpoint TEXT,
            ocid TEXT,
            status INTEGER
        )
    ''')


def _parse_url(url: str):
    """從 URL 解析 endpoint（/v1/ 之後的路徑）與 ocid（無 ocid 則退而取其他識別碼）"""
    try:
        parts = urlparse(url)
        path = parts.path
        endpoint = path.split('/v1/', 1)[1] if '/v1/' in path else path
        query = parse_qs(parts.query)
        # 大多數端點帶 ocid；/v1/guild/basic 帶 oguild_id；/v1/id 與 /v1/guild/id 只有名稱
        ocid = (query.get('ocid')
                or query.get('oguild_id')
                or query.get('character_name')
                or query.get('guild_name')
                or [None])[0]
        return endpoint, ocid
    except Exception:
        return None, None


def log_request(url: str, status: int = None):
    """記錄一筆 API 請求；任何錯誤都被吞掉，不影響呼叫端"""
    try:
        endpoint, ocid = _parse_url(url)
        path = _current_db_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with sqlite3.connect(path) as conn:
            _ensure_table(conn)
            conn.execute(
                'INSERT INTO api_log (ts, endpoint, ocid, status) VALUES (?, ?, ?, ?)',
                (datetime.datetime.now(), endpoint, ocid, status)
            )
            conn.commit()
    except Exception:
        pass


def logged_get(url: str, headers=None, **kwargs):
    """requests.get 的包裝：先正常發送請求，再記錄 log，回傳原本的 response"""
    resp = requests.get(url, headers=headers, **kwargs)
    log_request(url, getattr(resp, 'status_code', None))
    return resp


# ---------------------------------------------------------------------------
# 查詢用 helper（可供之後做 /apistat 指令或手動統計）
# ---------------------------------------------------------------------------

def _connect_quarter(year: int = None, quarter: int = None) -> sqlite3.Connection:
    now = datetime.datetime.now()
    year = year or now.year
    quarter = quarter or ((now.month - 1) // 3 + 1)
    path = os.path.join(LOG_DIR, f"API_Log_{year}Q{quarter}.db")
    conn = sqlite3.connect(path)
    _ensure_table(conn)
    return conn


def get_total_count(year: int = None, quarter: int = None) -> int:
    """該季 API 請求總次數"""
    with _connect_quarter(year, quarter) as conn:
        return conn.execute('SELECT COUNT(*) FROM api_log').fetchone()[0]


def get_last_hour_count() -> int:
    """過去 1 小時的 API 請求次數（讀目前季度的 DB）"""
    try:
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=1)
        with sqlite3.connect(_current_db_path()) as conn:
            _ensure_table(conn)
            return conn.execute(
                'SELECT COUNT(*) FROM api_log WHERE ts >= ?', (cutoff,)
            ).fetchone()[0]
    except Exception:
        return 0


def get_daily_counts(days: int = 7) -> dict:
    """回傳近 N 天每天的 API 請求次數 {'YYYY-MM-DD': count}。
    日期以 UTC 計（date(ts,'utc')），與 command_usage 的 date('now') 基準一致，方便對齊顯示。"""
    try:
        with sqlite3.connect(_current_db_path()) as conn:
            _ensure_table(conn)
            rows = conn.execute(
                "SELECT date(ts,'utc') AS d, COUNT(*) FROM api_log "
                "WHERE ts >= datetime('now','localtime',?) GROUP BY d",
                (f'-{days} days',)
            ).fetchall()
            return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


def get_month_summary(year: int = None, month: int = None) -> dict:
    """指定月份的 API 統計（省略則為當月）。自動挑對應季度的 DB 檔。
    回傳 {'month': 'YYYY-MM', 'total': N, 'by_endpoint': [(endpoint, count), ...]}"""
    now = datetime.datetime.now()
    year = year or now.year
    month = month or now.month
    ym = f"{year:04d}-{month:02d}"
    quarter = (month - 1) // 3 + 1
    path = os.path.join(LOG_DIR, f"API_Log_{year}Q{quarter}.db")

    result = {'month': ym, 'total': 0, 'by_endpoint': []}
    try:
        with sqlite3.connect(path) as conn:
            _ensure_table(conn)
            result['total'] = conn.execute(
                "SELECT COUNT(*) FROM api_log WHERE strftime('%Y-%m', ts) = ?", (ym,)
            ).fetchone()[0]
            result['by_endpoint'] = conn.execute(
                "SELECT endpoint, COUNT(*) FROM api_log WHERE strftime('%Y-%m', ts) = ? "
                "GROUP BY endpoint ORDER BY 2 DESC", (ym,)
            ).fetchall()
    except Exception:
        pass
    return result


def get_count_by_endpoint(year: int = None, quarter: int = None) -> list:
    """各 API(endpoint) 的次數，由多到少"""
    with _connect_quarter(year, quarter) as conn:
        return conn.execute(
            'SELECT endpoint, COUNT(*) FROM api_log GROUP BY endpoint ORDER BY 2 DESC'
        ).fetchall()


def get_count_by_ocid(year: int = None, quarter: int = None, limit: int = 50) -> list:
    """各 OCID 的次數，由多到少"""
    with _connect_quarter(year, quarter) as conn:
        return conn.execute(
            'SELECT ocid, COUNT(*) FROM api_log WHERE ocid IS NOT NULL '
            'GROUP BY ocid ORDER BY 2 DESC LIMIT ?', (limit,)
        ).fetchall()
