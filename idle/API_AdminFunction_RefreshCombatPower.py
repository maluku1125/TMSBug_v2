"""
API_AdminFunction_RefreshCombatPower.py
=======================================
戰鬥力「全量首次掃描」admin 腳本（手動執行）。

每日輪替刷新（Loop_API_Data_Refresh）已經會在刷新角色時順帶抓戰力，
但那要 7 天才輪完一圈、5 週才填滿 30 日最高的週桶。
這支腳本讓所有角色一次就先拿到第一格週桶，戰力榜當天就能用。

只打 /character/stat 一個端點，成本遠低於 RefreshEquipStat（那支要打 5 個）：
  264,000 角色 ÷ 350 req/s ≈ 13 分鐘

用法：
  python API_AdminFunction_RefreshCombatPower.py                # 全部 260+ 角色
  python API_AdminFunction_RefreshCombatPower.py --skip-done    # 跳過本週已有紀錄者（續跑）
  python API_AdminFunction_RefreshCombatPower.py --limit 500    # 只測前 500 筆
  python API_AdminFunction_RefreshCombatPower.py --rate 200     # 降速

執行中可按 Ctrl+C 中斷，已取得的資料會寫入後才結束。
"""

import os
import sys
import time
import json
import asyncio
import sqlite3
import argparse
import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_IDLE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_IDLE_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import aiohttp
from functions.API_functions.API_Request_Character import request_character_stat_async
from functions.API_functions.API_EquipStat import (
    cp_fields, save_character_stat, flush_equip_stat,
    EQUIP_DB, EQUIP_STAT_MIN_LEVEL, _iso_week)


def get_targets(min_level: int, limit: int, skip_done: bool):
    """從 Equip_Stat 取出要掃描的角色。

    以 Equip_Stat 為來源而非 CharacterBasicInfo，因為戰力欄位就住在這張表，
    且該表已經過等級篩選與孤兒清理。
    """
    with sqlite3.connect(f'file:{EQUIP_DB}?mode=ro', uri=True) as conn:
        rows = conn.execute(
            'SELECT ocid, character_name, cp_slots FROM character_equip_stat '
            'WHERE character_level IS NOT NULL AND character_level >= ?',
            (min_level,)).fetchall()

    if skip_done:
        wk = _iso_week(datetime.datetime.now())
        before = len(rows)
        kept = []
        for ocid, name, slots in rows:
            try:
                if slots and wk in (json.loads(slots) or {}):
                    continue          # 本週已有紀錄，再抓也只會取到同一格的最大值
            except (ValueError, TypeError):
                pass
            kept.append((ocid, name, slots))
        rows = kept
        print(f'--skip-done：本週已完成 {before - len(rows):,} 筆，剩餘 {len(rows):,} 筆')

    if limit and limit > 0:
        rows = rows[:limit]
    return [(o, n) for o, n, _ in rows]


async def _one(session, sem, ocid, name, stats):
    stat = await request_character_stat_async(session, ocid, sem)
    if not stat:
        stats['failed'] += 1
        return
    f = cp_fields(ocid, stat)
    if not f:
        stats['no_cp'] += 1
        return
    save_character_stat(ocid, name, f)
    stats['success'] += 1
    stats['cp_sum'] += f['cp_current']
    stats['cp_max'] = max(stats['cp_max'], f['cp_current'])


async def run(min_level, limit, concurrent, skip_done):
    targets = get_targets(min_level, limit, skip_done)
    total = len(targets)
    print(f'找到 {total:,} 筆 LV{min_level}+ 角色，開始掃描戰鬥力（併發 {concurrent}）…')
    if not total:
        return

    stats = {'success': 0, 'failed': 0, 'no_cp': 0, 'cp_sum': 0, 'cp_max': 0}
    sem = asyncio.Semaphore(concurrent)
    start = time.time()
    done = 0

    try:
        async with aiohttp.ClientSession() as session:
            tasks = [_one(session, sem, o, n, stats) for o, n in targets]
            for fut in asyncio.as_completed(tasks):
                await fut
                done += 1
                if done % 2000 == 0:
                    el = time.time() - start
                    rate = done / el
                    print(f'  …{done:,}/{total:,} ({done / total * 100:.1f}%)  '
                          f'{rate:.0f}/秒  剩餘約 {(total - done) / rate / 60:.1f} 分')
    except KeyboardInterrupt:
        print('\n⚠ 已中斷，正在寫出已取得的資料…（下次可加 --skip-done 續跑）')
    finally:
        flushed = flush_equip_stat()
        if flushed:
            print(f'最後批次寫入 {flushed} 筆')
        dur = time.time() - start
        ok = stats['success']
        print('\n=== 戰鬥力掃描結果 ===')
        print(f'成功 {ok:,} / 失敗 {stats["failed"]:,} / 無戰力欄位 {stats["no_cp"]:,}')
        if ok:
            print(f'平均戰力 : {stats["cp_sum"] // ok:,}')
            print(f'最高戰力 : {stats["cp_max"]:,}')
        print(f'耗時     : {dur / 60:.1f} 分（{done / dur:.0f} req/s）')
        print('=' * 22)


def main():
    ap = argparse.ArgumentParser(description='戰鬥力全量掃描（只打 /character/stat）')
    ap.add_argument('--min-level', type=int, default=EQUIP_STAT_MIN_LEVEL)
    ap.add_argument('--limit', type=int, default=0, help='處理筆數上限，0=全部')
    ap.add_argument('--concurrent', type=int, default=20)
    ap.add_argument('--rate', type=float, default=350,
                    help='全域 API 速率上限 req/s，預設 350（官方上限 500）')
    ap.add_argument('--skip-done', action='store_true',
                    help='跳過本週已有戰力紀錄的角色（中斷後續跑用）')
    args = ap.parse_args()

    from functions.API_functions.API_RateLimiter import set_global_rate
    import functions.API_functions.API_Request_Character as _rc
    set_global_rate(args.rate)
    _rc.QUIET = True

    asyncio.run(run(args.min_level, args.limit, args.concurrent, args.skip_done))


if __name__ == '__main__':
    main()
