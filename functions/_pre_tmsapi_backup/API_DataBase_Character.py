"""
API_DataBase_Character.py —— 轉發層（階段 1）

實作已搬到 tmsapi.store.character，本檔只把自己**替換**成那個模組。

⚠️ 為什麼是 `sys.modules[__name__] = _impl` 而不是 `from ... import *`：

    Loop_API_Data_Refresh 會做 `_rc.QUIET = True` 去改模組層級變數。
    如果用 `import *`，那個賦值會落在這個轉發模組上，真正的實作看不到，
    批次刷新時的 print 就不會被關掉 —— 而那正是當初 discord heartbeat
    blocked 的成因。替換 sys.modules 之後，任何 import 這個路徑的地方
    拿到的都是實作模組本身，屬性賦值會正確生效。

回退方式：把本檔換回 git 中的原始內容（備份在 functions/_pre_tmsapi_backup/API_DataBase_Character.py）。
"""

import sys as _sys

from tmsapi.store.character import *          # noqa: F401,F403  —— 讓靜態檢查看得到名稱
import tmsapi.store.character as _impl

_sys.modules[__name__] = _impl
