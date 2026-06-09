"""
API_BattleRecord.py
===================
/battle 對戰戰績儲存。以「角色暱稱」為 key（非 Discord 使用者）。
資料庫：C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\battle\\battle_record.db
打贏 +1W、打輸 +1L。
"""

import os
import sqlite3
import datetime

BATTLE_DIR = 'C:\\Users\\User\\Desktop\\DiscordBotlog\\API\\battle'
DB_PATH = os.path.join(BATTLE_DIR, 'battle_record.db')


def _conn():
    os.makedirs(BATTLE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS battle_record (
            character_name TEXT PRIMARY KEY,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            updated_at TIMESTAMP
        )
    ''')
    # 勝敗感言：以 Discord user_id 為 key
    conn.execute('''
        CREATE TABLE IF NOT EXISTS battle_quotes (
            user_id TEXT PRIMARY KEY,
            win_quote TEXT,
            bigwin_quote TEXT,
            lose_quote TEXT,
            biglose_quote TEXT,
            updated_at TIMESTAMP
        )
    ''')
    return conn


def get_record(character_name: str):
    """回傳 (wins, losses)，查不到回 (0, 0)"""
    try:
        with _conn() as conn:
            row = conn.execute(
                'SELECT wins, losses FROM battle_record WHERE character_name = ?',
                (character_name,)
            ).fetchone()
            return (row[0], row[1]) if row else (0, 0)
    except Exception:
        return (0, 0)


def add_result(character_name: str, won: bool):
    """記錄一場結果：won=True +1W，否則 +1L。失敗不拋例外。"""
    try:
        with _conn() as conn:
            conn.execute(
                '''
                INSERT INTO battle_record (character_name, wins, losses, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(character_name) DO UPDATE SET
                    wins = wins + excluded.wins,
                    losses = losses + excluded.losses,
                    updated_at = excluded.updated_at
                ''',
                (character_name, 1 if won else 0, 0 if won else 1, datetime.datetime.now())
            )
            conn.commit()
    except Exception:
        pass


def get_quotes(user_id: str) -> dict:
    """取得使用者的勝敗感言 {win, big_win, lose, big_lose}（未設定為 None）"""
    try:
        with _conn() as conn:
            row = conn.execute(
                'SELECT win_quote, bigwin_quote, lose_quote, biglose_quote '
                'FROM battle_quotes WHERE user_id = ?',
                (user_id,)
            ).fetchone()
            if not row:
                return {'win': None, 'big_win': None, 'lose': None, 'big_lose': None}
            return {'win': row[0], 'big_win': row[1], 'lose': row[2], 'big_lose': row[3]}
    except Exception:
        return {'win': None, 'big_win': None, 'lose': None, 'big_lose': None}


def set_quotes(user_id: str, win=None, big_win=None, lose=None, big_lose=None):
    """設定使用者的勝敗感言（空字串視為 None）。失敗不拋例外。"""
    def _clean(v):
        v = (v or '').strip()
        return v or None
    try:
        with _conn() as conn:
            conn.execute(
                '''
                INSERT INTO battle_quotes (user_id, win_quote, bigwin_quote, lose_quote, biglose_quote, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    win_quote = excluded.win_quote,
                    bigwin_quote = excluded.bigwin_quote,
                    lose_quote = excluded.lose_quote,
                    biglose_quote = excluded.biglose_quote,
                    updated_at = excluded.updated_at
                ''',
                (user_id, _clean(win), _clean(big_win), _clean(lose), _clean(big_lose),
                 datetime.datetime.now())
            )
            conn.commit()
    except Exception:
        pass
