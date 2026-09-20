"""可熱重載的 cog 清單。

單獨一個模組，不放在 TMSBug_v2.py 裡 —— Bot 主檔是以 `__main__` 執行的，
從 cog 去 `from TMSBug_v2 import ...` 會把整個主檔**當成另一個模組再 import
一次**（類別定義、匯入全部重跑）。目前主檔的啟動被 `if __name__` 保護著，
所以不會開出第二個 Bot，但那是一條不該踩的線。

新增 cog 時要記得加進來，否則它只會在下次重啟時出現，後台也看不到它。
Loop_* 不放這裡：它們帶 tasks.loop，而 Loop_StatusReport 正是執行重載的
那一支，重載自己等於抽掉腳下的地板。
"""

RELOADABLE_COGS = [
    'Slash_BasicCommands', 'Slash_RequestUnionRank', 'Slash_CreateBossDataEmbed',
    'Slash_CreatePrizeEmbed', 'Slash_CreateSolErdaFragmentEmbed',
    'Slash_RequestMapleEvents', 'Slash_Formulas', 'Slash_CalculateScrolls',
    'Slash_Cubes', 'Slash_GuildFunction', 'Slash_StarForce', 'Slash_API',
    'Slash_Setting', 'Slash_Battle',
]
