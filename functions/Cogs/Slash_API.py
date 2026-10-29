import aiohttp
import asyncio
import io
import discord
from discord import app_commands
from discord.ext import commands

# ⚠️ 這些 create_*_embed 是**同步**函式，內部會打數次到數十次 HTTP。
# 直接從 async 指令呼叫會整個凍住 event loop —— Discord 隨即噴
# "heartbeat blocked"，嚴重時 shard 斷線。實測 /exptracking 一次最多打 10 次
# character/basic，正常也要 1.2 秒，外部 API 稍慢就破 10 秒。
#
# 用 asyncio.to_thread 丟到執行緒。⚠️ 只有「不建立 discord.ui.View」的函式
# 能這樣包 —— View 的建構需要 running event loop，在工作執行緒裡會
# RuntimeError（discord.py 2.5.2 實測）。

import datetime
import time
import logging
from discord.errors import NotFound
from functions.API_functions.CreateCharacterEmbed import create_character_basic_embed
from functions.API_functions.CreateGuildEmbed import create_guild_basic_embed   
from functions.API_functions.CreateCharacterEquipmentEmbed import (
    create_character_equipment_embed, _equipment_fetch)
# 等級榜改讀 JSON（前 5,000 名，/rank 只顯示前 100）
from tmsapi.stats import get_all_characters_level_exp_ranking
from functions.API_functions.CreateRankingEmbed import create_ranking_embed
from functions.API_functions.CreateEXPTrackingEmbed import create_exp_tracking_embed
from functions.API_functions.CreateUnionTrackingEmbed import create_union_tracking_embed
from functions.API_functions.CreateAPIAnalyseEmbed import create_api_analyse_embed
from functions.API_functions.CreateCharacterGIF import build_character_gif
from functions.API_functions.CreateChampionEmbed import create_champion_embed
from functions.API_functions.CreateAccountTrackingEmbed import (
    collect_account, extract_cp, needs_old_rate, look_entries,
    build_embed as build_account_embed,
    page_count as account_page_count,
    page_rows as account_page_rows)
from functions.CombineCharacter import fetch_look_images, compose_roster
from tmsapi.request import request_character_stat_async, request_character_basic_async

from functions.SlashCommandManager import UseSlashCommand
from functions.database_manager import UserDataDB
from functions.CombineCharacter import combine_character_images

user_db = UserDataDB()
SLOT_NAMES = UserDataDB.SLOT_NAMES


def get_action_params(user_id: str):
    """取得使用者設定的角色動作（action/emotion/wmotion/animated），無設定則回 None"""
    if not user_id:
        return None
    action = user_db.get_user_action(user_id)
    if action and (action.get('action') or action.get('emotion')
                   or action.get('wmotion') or action.get('animated')):
        return action
    return None


async def make_character_gif_file(user_id: str, image_url: str):
    """若使用者開啟動畫且該動作可動畫，回傳 ('attachment://char.gif', discord.File)；否則 (None, None)"""
    ap = get_action_params(user_id)
    if not (ap and ap.get('animated') and image_url):
        return None, None
    try:
        gif = await build_character_gif(
            image_url,
            ap.get('action') or 'A00',
            ap.get('emotion') or 'E00',
            ap.get('wmotion'),
        )
        if gif:
            return 'attachment://char.gif', discord.File(gif, filename='char.gif')
    except Exception:
        pass
    return None, None


class CharacterView(discord.ui.View):
    def __init__(self, character_name: str, character_basic_data: dict = None, user_id: str = None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.character_name = character_name
        self.character_basic_data = character_basic_data
        self.user_id = user_id  # 用來查詢該使用者設定的角色動作
        self.current_mode = "character"  # character, preset_1, preset_2, preset_3
        self._update_button_styles()
    
    def _update_button_styles(self):
        """Update button colors based on current mode"""
        # Find all buttons
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "角色":
                    item.style = discord.ButtonStyle.primary if self.current_mode == "character" else discord.ButtonStyle.secondary
                elif item.label == "預設1":
                    item.style = discord.ButtonStyle.primary if self.current_mode == "preset_1" else discord.ButtonStyle.success
                elif item.label == "預設2":
                    item.style = discord.ButtonStyle.primary if self.current_mode == "preset_2" else discord.ButtonStyle.success
                elif item.label == "預設3":
                    item.style = discord.ButtonStyle.primary if self.current_mode == "preset_3" else discord.ButtonStyle.success
    
    def get_character_basic_embed(self):
        """Get character basic data embed"""
        try:
            # 查詢使用者設定的角色動作（action/emotion/wmotion），有設定才套用
            action_params = None
            if self.user_id:
                action = user_db.get_user_action(self.user_id)
                if action and (action.get('action') or action.get('emotion') or action.get('wmotion')):
                    action_params = action

            # ⚠️ 這裡**不能**用 to_thread —— get_character_basic_embed 是同步方法
            # （View 的 callback 會直接呼叫）。要改成非阻塞得先把整條路徑改 async。
            result = create_character_basic_embed(
                self.character_name, return_data=True, action_params=action_params)
            if isinstance(result, dict):
                self.character_basic_data = result["character_basic_data"]
                return result["embed"]
            else:
                return result
        except Exception:
            return None
    
    @discord.ui.button(label="角色", style=discord.ButtonStyle.primary)
    async def character_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.current_mode != "character":
                self.current_mode = "character"
                self._update_button_styles()
                await interaction.response.defer()
                embed = self.get_character_basic_embed()
                if embed:
                    # 回到角色頁時，若有開啟動畫則重新附上 GIF（否則清掉先前附件）
                    image_url = (self.character_basic_data or {}).get('character_image')
                    thumb_url, gif_file = await make_character_gif_file(self.user_id, image_url)
                    if gif_file:
                        embed.set_thumbnail(url=thumb_url)
                        await interaction.edit_original_response(embed=embed, view=self, attachments=[gif_file])
                    else:
                        await interaction.edit_original_response(embed=embed, view=self, attachments=[])
            else:
                await interaction.response.defer()
        except NotFound:
            logging.warning("character_button: Interaction expired (Unknown interaction)")
    
    @discord.ui.button(label="預設1", style=discord.ButtonStyle.success)
    async def preset_1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("preset_1_button: Interaction expired (Unknown interaction)")
            return
        
        if self.current_mode != "preset_1":
            self.current_mode = "preset_1"
            try:
                _pre = await asyncio.to_thread(_equipment_fetch, self.character_name)
                result = create_character_equipment_embed(self.character_name, self.character_basic_data, prefetched=_pre)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    view.current_preset = "preset_1"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.edit_original_response(embed=embed, view=view, attachments=[])
                else:
                    error_embed = discord.Embed(
                        title="錯誤",
                        description="無法獲取預設1的裝備資訊",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=error_embed, view=self)
            except NotFound:
                logging.warning("preset_1_button: Message edit failed (Unknown interaction)")
            except Exception as e:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"載入裝備資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                try:
                    await interaction.edit_original_response(embed=error_embed, view=self)
                except NotFound:
                    pass
    
    @discord.ui.button(label="預設2", style=discord.ButtonStyle.success)
    async def preset_2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("preset_2_button: Interaction expired (Unknown interaction)")
            return
        
        if self.current_mode != "preset_2":
            self.current_mode = "preset_2"
            try:
                _pre = await asyncio.to_thread(_equipment_fetch, self.character_name)
                result = create_character_equipment_embed(self.character_name, self.character_basic_data, prefetched=_pre)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    view.current_preset = "preset_2"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.edit_original_response(embed=embed, view=view, attachments=[])
                else:
                    error_embed = discord.Embed(
                        title="錯誤",
                        description="無法獲取預設2的裝備資訊",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=error_embed, view=self)
            except NotFound:
                logging.warning("preset_2_button: Message edit failed (Unknown interaction)")
            except Exception as e:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"載入裝備資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                try:
                    await interaction.edit_original_response(embed=error_embed, view=self)
                except NotFound:
                    pass
    
    @discord.ui.button(label="預設3", style=discord.ButtonStyle.success)
    async def preset_3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("preset_3_button: Interaction expired (Unknown interaction)")
            return
        
        if self.current_mode != "preset_3":
            self.current_mode = "preset_3"
            try:
                _pre = await asyncio.to_thread(_equipment_fetch, self.character_name)
                result = create_character_equipment_embed(self.character_name, self.character_basic_data, prefetched=_pre)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    view.current_preset = "preset_3"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.edit_original_response(embed=embed, view=view, attachments=[])
                else:
                    error_embed = discord.Embed(
                        title="錯誤",
                        description="無法獲取預設3的裝備資訊",
                        color=discord.Color.red()
                    )
                    await interaction.edit_original_response(embed=error_embed, view=self)
            except NotFound:
                logging.warning("preset_3_button: Message edit failed (Unknown interaction)")
            except Exception as e:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"載入裝備資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                try:
                    await interaction.edit_original_response(embed=error_embed, view=self)
                except NotFound:
                    pass
    
    async def on_timeout(self):
        # Disable all components after timeout
        for item in self.children:
            item.disabled = True


class CharacterSelectView(discord.ui.View):
    """多角色選擇畫面：顯示合成圖 + 下拉選單讓使用者選擇要查詢的角色"""
    def __init__(self, registered_characters: dict, interaction: discord.Interaction, start_time: float):
        super().__init__(timeout=120)
        self.registered_characters = registered_characters  # {slot: name}
        self.original_interaction = interaction
        self.start_time = start_time

        # 建立下拉選單
        options = []
        for slot, name in sorted(registered_characters.items()):
            options.append(discord.SelectOption(
                label=name,
                value=name
            ))

        select = discord.ui.Select(
            placeholder="選擇要查詢的角色...",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        selected_name = interaction.data['values'][0]
        try:
            await interaction.response.defer()
        except NotFound:
            return

        try:
            view = CharacterView(selected_name, user_id=str(interaction.user.id))
            embed = view.get_character_basic_embed()

            if embed:
                image_url = (view.character_basic_data or {}).get('character_image')
                thumb_url, gif_file = await make_character_gif_file(str(interaction.user.id), image_url)
                if gif_file:
                    embed.set_thumbnail(url=thumb_url)
                    await interaction.edit_original_response(embed=embed, view=view, attachments=[gif_file])
                else:
                    await interaction.edit_original_response(embed=embed, view=view, attachments=[])
                response_time = time.time() - self.start_time
                UseSlashCommand('api_character', self.original_interaction, response_time, True)
            else:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"無法獲取角色 '{selected_name}' 的資訊",
                    color=discord.Color.red()
                )
                await interaction.edit_original_response(embed=error_embed, view=None, attachments=[])
                response_time = time.time() - self.start_time
                UseSlashCommand('api_character', self.original_interaction, response_time, False)
        except Exception as e:
            error_embed = discord.Embed(
                title="錯誤",
                description=f"生成角色資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            try:
                await interaction.edit_original_response(embed=error_embed, view=None, attachments=[])
            except NotFound:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class ExpTrackingSelectView(discord.ui.View):
    """經驗追蹤多角色選擇畫面"""
    def __init__(self, registered_characters: dict, interaction: discord.Interaction, start_time: float):
        super().__init__(timeout=120)
        self.registered_characters = registered_characters
        self.original_interaction = interaction
        self.start_time = start_time

        options = []
        for slot, name in sorted(registered_characters.items()):
            options.append(discord.SelectOption(label=name, value=name))

        select = discord.ui.Select(
            placeholder="選擇要追蹤的角色...",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        selected_name = interaction.data['values'][0]
        try:
            await interaction.response.defer()
        except NotFound:
            return

        try:
            result = await asyncio.to_thread(
                create_exp_tracking_embed,
                selected_name, action_params=get_action_params(str(interaction.user.id)))
            if result["success"]:
                thumb_url, gif_file = await make_character_gif_file(str(interaction.user.id), result.get("image_url"))
                if gif_file:
                    result["embed"].set_thumbnail(url=thumb_url)
                    await interaction.edit_original_response(embed=result["embed"], view=None, attachments=[gif_file])
                else:
                    await interaction.edit_original_response(embed=result["embed"], view=None, attachments=[])
                response_time = time.time() - self.start_time
                UseSlashCommand('api_exptracking', self.original_interaction, response_time, True)
            else:
                await interaction.edit_original_response(embed=result["embed"], view=None, attachments=[])
                response_time = time.time() - self.start_time
                UseSlashCommand('api_exptracking', self.original_interaction, response_time, False)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成經驗追蹤資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            try:
                await interaction.edit_original_response(embed=error_embed, view=None, attachments=[])
            except NotFound:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class UnionTrackingSelectView(discord.ui.View):
    """戰地追蹤多角色選擇畫面"""
    def __init__(self, registered_characters: dict, interaction: discord.Interaction, start_time: float):
        super().__init__(timeout=120)
        self.registered_characters = registered_characters
        self.original_interaction = interaction
        self.start_time = start_time

        options = []
        for slot, name in sorted(registered_characters.items()):
            options.append(discord.SelectOption(label=name, value=name))

        select = discord.ui.Select(
            placeholder="選擇要追蹤的角色...",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        selected_name = interaction.data['values'][0]
        try:
            await interaction.response.defer()
        except NotFound:
            return

        try:
            result = await asyncio.to_thread(
                create_union_tracking_embed,
                selected_name)
            await interaction.edit_original_response(
                embed=result["embed"], view=None, attachments=[])
            response_time = time.time() - self.start_time
            UseSlashCommand('api_uniontracking', self.original_interaction,
                            response_time, result["success"])
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成戰地聯盟追蹤資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            try:
                await interaction.edit_original_response(
                    embed=error_embed, view=None, attachments=[])
            except NotFound:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


def _account_fail_embed(name):
    """只有「這個名字不在本機資料庫」會走到這裡。

    「查得到但只有自己一隻」不是失敗（實測佔 26.5%），那種情況照常列出，
    由 embed 的 description 說明為什麼只有一隻。
    """
    return discord.Embed(
        title="查無這個角色",
        description=(
            f"資料庫裡沒有「{name}」。\n\n"
            "帳號查詢全部讀本機資料，不會即時去問官方，所以還沒被收錄的角色"
            "（新角色、或長期沒上線被清掉的）查不到。確認一下名字有沒有打錯。"),
        color=0xff0000)


async def _fetch_page_data(rows):
    """現打這一頁要的兩種資料，回傳 ({ocid: 戰力}, {ocid: 七天前的經驗%})。

    **戰力**為什麼不讀本機快取：`Equip_Stat.db` 只收 LV260 以上
    （`EQUIP_STAT_MIN_LEVEL = 260`），實測帳號角色有一半在那之下、完全沒有列，
    而 260-279 那批又有四成超過 7 天沒更新。現打才能每一隻都有、而且是當下的值。

    **七天前的經驗%**只有七天內升過等的角色要（實測 5.7%）—— 沒升等的用本機
    lvl_hist 就能算得精確，不必多打。帶 date 的 basic 查詢不會寫進資料庫
    （request.py 裡的條件是 `not date and save_to_db`），不會污染管線的資料。

    兩種請求一起送。全域限流器預設 350 req/s（官方上限 500），一頁十幾個請求
    不會排擠到管線；ocid 已經從本機資料庫拿到了，不必再打一次 id 端點。
    """
    sem = asyncio.Semaphore(12)
    old_jobs = needs_old_rate(rows)
    async with aiohttp.ClientSession() as session:
        cp_res, old_res = await asyncio.gather(
            asyncio.gather(
                *[request_character_stat_async(session, r['ocid'], sem) for r in rows],
                return_exceptions=True),
            asyncio.gather(
                *[request_character_basic_async(session, ocid, sem, date=d,
                                                save_to_db=False)
                  for ocid, d in old_jobs],
                return_exceptions=True))

    cp = {}
    for r, res in zip(rows, cp_res):
        cp[r['ocid']] = None if isinstance(res, BaseException) else extract_cp(res)

    old = {}
    for (ocid, _date), res in zip(old_jobs, old_res):
        if isinstance(res, BaseException) or not res:
            continue
        try:
            old[ocid] = float(res.get('character_exp_rate'))
        except (TypeError, ValueError):
            pass
    return cp, old


async def _compose_page_look(rows):
    """下載並合成這一頁的造型圖，回傳 PNG bytes（失敗回 None）。

    造型 URL 本機 100% 都有（`character_image`），所以不必打 API。下載走磁碟
    快取 —— URL 最後一段是造型本身的雜湊，換裝才會變，可以永久有效。
    實測 12 張冷啟動約 1.4 秒、命中快取 0 秒。

    PIL 合成是 CPU 工作，丟 to_thread：直接在事件迴圈裡跑會卡 heartbeat。
    """
    entries = look_entries(rows)
    try:
        blobs = await fetch_look_images([u for _n, u in entries])
        # 6 欄不是美感問題：圖太高會把整個 embed 的寬度縮掉，
        # 上面的 inline 欄位跟著被擠扁。詳見 compose_roster 的說明。
        buf = await asyncio.to_thread(compose_roster, entries, blobs, 6, 2)
    except Exception as e:
        logging.warning(f"accounttracking 合成造型失敗: {e}")
        return None
    return buf.getvalue() if buf else None


class AccountTrackingView(discord.ui.View):
    """帳號角色清單翻頁，外加一顆切換造型圖的按鈕。

    翻到哪一頁才打哪一頁的 API，抓過的存進 self.cp，翻回去不重打 ——
    否則一個 5 頁的帳號來回翻幾次就是上百次請求。

    **造型圖預設顯示，但可以按鈕關掉。** 只要 embed 裡有圖，Discord 就會把整個
    embed 的寬度壓成圖的顯示寬度，inline 欄位跟著被擠扁 —— 按鈕留著是為了能
    一鍵比對有圖與無圖的寬度差，順便給不想看造型的人一個關掉的方法
    （關著的時候完全不下載，連外部 CDN 都不碰）。
    """

    def __init__(self, character_name, data, interaction, start_time):
        super().__init__(timeout=180)
        self.character_name = character_name
        self.data = data
        self.original_interaction = interaction
        self.start_time = start_time
        self.page = 0
        self.npage = account_page_count(data['rows'])
        self.cp = {}
        self.old_rates = {}
        self.img = {}           # {頁碼: 合成好的 PNG bytes}
        self.show_look = True   # 預設顯示；按鈕留著是為了能一鍵比對有圖/無圖的寬度

        self.prev_btn = discord.ui.Button(
            label="◀ 上一頁", style=discord.ButtonStyle.secondary)
        self.next_btn = discord.ui.Button(
            label="下一頁 ▶", style=discord.ButtonStyle.secondary)
        self.look_btn = discord.ui.Button(
            label="🧍 顯示外觀", style=discord.ButtonStyle.secondary)
        self.prev_btn.callback = self._prev
        self.next_btn.callback = self._next
        self.look_btn.callback = self._toggle_look
        if self.npage > 1:
            self.add_item(self.prev_btn)
            self.add_item(self.next_btn)
        self.add_item(self.look_btn)
        self._sync_buttons()

    def _sync_buttons(self):
        self.prev_btn.disabled = self.page <= 0
        self.next_btn.disabled = self.page >= self.npage - 1
        self.look_btn.label = "🧍 隱藏外觀" if self.show_look else "🧍 顯示外觀"

    async def load_page(self, page):
        """切到第 page 頁：補齊戰力與歷史、合成造型圖。回傳 (embed, file)。

        合成結果以 bytes 存在 self.img，翻回來不必重做。discord.File 送出後
        內部的串流就讀完了、不能重用，所以每次都要拿 bytes 現包一個新的。
        """
        self.page = max(0, min(page, self.npage - 1))
        rows = account_page_rows(self.data['rows'], self.page)
        todo = [r for r in rows if r['ocid'] not in self.cp]
        if todo:
            cp, old = await _fetch_page_data(todo)
            self.cp.update(cp)
            self.old_rates.update(old)

        # 沒按「顯示外觀」就完全不合成，也不下載 —— 預設狀態一次外部請求都不發
        png = None
        if self.show_look:
            if self.page not in self.img:
                self.img[self.page] = await _compose_page_look(rows)
            png = self.img[self.page]

        self._sync_buttons()
        # 檔名帶頁碼：同名附件在翻頁時有機會被客戶端拿舊的快取圖頂替
        fname = 'roster_p%d.png' % (self.page + 1) if png else None
        embed = build_account_embed(self.character_name, self.data, self.page,
                                    self.cp, self.old_rates, fname)
        file = discord.File(io.BytesIO(png), filename=fname) if png else None
        return embed, file

    async def _turn(self, interaction, delta):
        try:
            await interaction.response.defer()
        except NotFound:
            return
        try:
            embed, file = await self.load_page(self.page + delta)
            await interaction.edit_original_response(
                embed=embed, view=self, attachments=[file] if file else [])
        except NotFound:
            pass
        except Exception as e:
            logging.warning(f"accounttracking 翻頁失敗: {e}")

    async def _prev(self, interaction):
        await self._turn(interaction, -1)

    async def _next(self, interaction):
        await self._turn(interaction, +1)

    async def _toggle_look(self, interaction):
        """切換造型圖。關掉時要傳 attachments=[] 才會真的把圖拿掉。"""
        try:
            await interaction.response.defer()
        except NotFound:
            return
        self.show_look = not self.show_look
        try:
            embed, file = await self.load_page(self.page)
            await interaction.edit_original_response(
                embed=embed, view=self, attachments=[file] if file else [])
        except NotFound:
            pass
        except Exception as e:
            logging.warning(f"accounttracking 切換外觀失敗: {e}")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


async def send_account_tracking(interaction, character_name, start_time, edit=False):
    """查帳號 → 抓第一頁戰力 → 送出。select 選單與指令本體共用這一段。

    `collect_account` 是同步的 SQLite 查詢，丟 to_thread；View 必須留在
    事件迴圈裡建（在工作執行緒建 View 會 RuntimeError，見檔頭說明）。
    """
    data = await asyncio.to_thread(collect_account, character_name)

    async def _out(embed, view=None, file=None):
        if edit:
            # 編輯時 view 一定要明確傳，不然選單那排按鈕不會被收掉
            await interaction.edit_original_response(
                embed=embed, view=view, attachments=[file] if file else [])
            return
        kw = {'embed': embed}
        if view is not None:
            kw['view'] = view
        if file is not None:
            kw['file'] = file
        await interaction.followup.send(**kw)

    if not data.get("success"):
        await _out(_account_fail_embed(character_name))
        return False

    # 就算只有一頁也要掛 view —— 翻頁鈕可以不要，但「顯示外觀」永遠都在
    view = AccountTrackingView(character_name, data, interaction, start_time)
    embed, file = await view.load_page(0)
    await _out(embed, view, file)
    return True


class AccountTrackingSelectView(discord.ui.View):
    """帳號追蹤多角色選擇畫面"""
    def __init__(self, registered_characters: dict, interaction: discord.Interaction, start_time: float):
        super().__init__(timeout=120)
        self.registered_characters = registered_characters
        self.original_interaction = interaction
        self.start_time = start_time

        options = []
        for slot, name in sorted(registered_characters.items()):
            options.append(discord.SelectOption(label=name, value=name))

        select = discord.ui.Select(
            placeholder="選擇要查詢的角色...",
            options=options,
            min_values=1,
            max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        selected_name = interaction.data['values'][0]
        try:
            await interaction.response.defer()
        except NotFound:
            return

        try:
            ok = await send_account_tracking(
                interaction, selected_name, self.start_time, edit=True)
            UseSlashCommand('api_accounttracking', self.original_interaction,
                            time.time() - self.start_time, ok)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成帳號追蹤資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            try:
                await interaction.edit_original_response(
                    embed=error_embed, view=None, attachments=[])
            except NotFound:
                pass

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Slash_API(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="character角色查詢", description="API角色查詢")
    @app_commands.describe(playername="角色名稱 (不輸入則使用已登錄的角色)")
    async def api_character_basic(self, interaction: discord.Interaction, playername: str = None):
        
        start_time = time.time()
        
        if playername is None:
            user_id = str(interaction.user.id)
            all_chars = user_db.get_all_user_characters(user_id)
            registered = {slot: name for slot, name in all_chars.items() if name}

            # 情況 3：無登錄任何角色 → 要求輸入
            if len(registered) == 0:
                try:
                    await interaction.response.send_message(
                        "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                        ephemeral=True
                    )
                except NotFound:
                    logging.warning("Interaction expired before first response")
                return

            # 情況 1：只有 1 個角色 → 直接查詢
            if len(registered) == 1:
                playername = list(registered.values())[0]
            else:
                # 情況 2：多個角色 → 顯示合成圖 + 下拉選單
                try:
                    await interaction.response.defer()
                except NotFound:
                    logging.warning("api_character_basic: Interaction expired before defer")
                    return

                select_view = CharacterSelectView(registered, interaction, start_time)

                # 合成角色圖片
                combined_image = await combine_character_images(all_chars)

                embed = discord.Embed(
                    title="🎮 請選擇要查詢的角色",
                    color=0x00bfff
                )

                if combined_image:
                    file = discord.File(combined_image, filename="characters.png")
                    embed.set_image(url="attachment://characters.png")
                    await interaction.followup.send(embed=embed, view=select_view, file=file)
                else:
                    await interaction.followup.send(embed=embed, view=select_view)
                return
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_character_basic: Interaction expired before defer")
            return

        try:
            # Create character data View
            view = CharacterView(playername, user_id=str(interaction.user.id))
            embed = view.get_character_basic_embed()
            
            if embed:
                image_url = (view.character_basic_data or {}).get('character_image')
                thumb_url, gif_file = await make_character_gif_file(str(interaction.user.id), image_url)
                if gif_file:
                    embed.set_thumbnail(url=thumb_url)
                    await interaction.followup.send(embed=embed, view=view, file=gif_file)
                else:
                    await interaction.followup.send(embed=embed, view=view)
                response_time = time.time() - start_time
                UseSlashCommand('api_character', interaction, response_time, True)
            else:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"無法獲取角色 '{playername}' 的資訊",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=error_embed)
                response_time = time.time() - start_time
                UseSlashCommand('api_character', interaction, response_time, False)
        except Exception as e:
            error_embed = discord.Embed(
                title="錯誤",
                description=f"生成角色資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_character', interaction, response_time, False)


    @app_commands.command(name="rank排行", description="顯示角色等級經驗排行榜")
    @app_commands.describe(character_class="職業")
    async def api_character_ranking(self, interaction: discord.Interaction, character_class: str = None):
        
        start_time = time.time()
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_character_ranking: Interaction expired before defer")
            return
        
        try:
            # 獲取排行榜資料 (全部資料，由 CreateRankingEmbed 來處理篩選)
            ranking_data = get_all_characters_level_exp_ranking(sort_by='level', ascending=False)
            
            if not ranking_data:
                error_embed = discord.Embed(
                    title="❌ 錯誤",
                    description="目前沒有任何角色資料可顯示",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=error_embed)
                response_time = time.time() - start_time
                UseSlashCommand('api_ranking', interaction, response_time, False)
                return
            
            # 如果指定了職業，則篩選特定職業的角色
            if character_class:
                ranking_data = [char for char in ranking_data if char['character_class'] == character_class]
                if not ranking_data:
                    error_embed = discord.Embed(
                        title="❌ 錯誤",
                        description=f"目前沒有找到職業為 '{character_class}' 的角色資料",
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=error_embed)
                    response_time = time.time() - start_time
                    UseSlashCommand('api_ranking', interaction, response_time, False)
                    return
            
            # 使用 create_ranking_embed 函數 (全伺服器TOP100，各世界TOP50)
            result = create_ranking_embed(ranking_data, include_view=True, character_class=character_class)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"], view=result["view"])
                response_time = time.time() - start_time
                UseSlashCommand('api_ranking', interaction, response_time, True)
            else:
                await interaction.followup.send(embed=result["embed"])
                response_time = time.time() - start_time
                UseSlashCommand('api_ranking', interaction, response_time, False)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"獲取排行榜資料時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_ranking', interaction, response_time, False)


    @app_commands.command(name="exptracking經驗追蹤", description="顯示角色近7日經驗成長分析")
    @app_commands.describe(character_name="角色名稱 (不輸入則使用已登錄的角色)")
    async def api_exp_tracking(self, interaction: discord.Interaction, character_name: str = None):
        
        start_time = time.time()
        
        if character_name is None:
            user_id = str(interaction.user.id)
            all_chars = user_db.get_all_user_characters(user_id)
            registered = {slot: name for slot, name in all_chars.items() if name}

            # 無登錄角色
            if len(registered) == 0:
                try:
                    await interaction.response.send_message(
                        "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                        ephemeral=True
                    )
                except NotFound:
                    logging.warning("Interaction expired before first response")
                return

            # 只有 1 個角色 → 直接查詢
            if len(registered) == 1:
                character_name = list(registered.values())[0]
            else:
                # 多個角色 → 顯示合成圖 + 下拉選單
                try:
                    await interaction.response.defer()
                except NotFound:
                    logging.warning("api_exp_tracking: Interaction expired before defer")
                    return

                select_view = ExpTrackingSelectView(registered, interaction, start_time)

                combined_image = await combine_character_images(all_chars)

                embed = discord.Embed(
                    title="📊 請選擇要追蹤的角色",
                    color=0x00bfff
                )

                if combined_image:
                    file = discord.File(combined_image, filename="characters.png")
                    embed.set_image(url="attachment://characters.png")
                    await interaction.followup.send(embed=embed, view=select_view, file=file)
                else:
                    await interaction.followup.send(embed=embed, view=select_view)
                return
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_exp_tracking: Interaction expired before defer")
            return
        
        try:
            # Create experience tracking embed
            result = await asyncio.to_thread(
                create_exp_tracking_embed,
                character_name, action_params=get_action_params(str(interaction.user.id)))

            if result["success"]:
                thumb_url, gif_file = await make_character_gif_file(str(interaction.user.id), result.get("image_url"))
                if gif_file:
                    result["embed"].set_thumbnail(url=thumb_url)
                    await interaction.followup.send(embed=result["embed"], file=gif_file)
                else:
                    await interaction.followup.send(embed=result["embed"])
                response_time = time.time() - start_time
                UseSlashCommand('api_exptracking', interaction, response_time, True)
            else:
                await interaction.followup.send(embed=result["embed"])
                response_time = time.time() - start_time
                UseSlashCommand('api_exptracking', interaction, response_time, False)
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成經驗追蹤資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_exptracking', interaction, response_time, False)


    @app_commands.command(name="champion聯盟冠軍", description="查詢聯盟冠軍角色（等級/經驗、六轉進度與戰鬥力）")
    @app_commands.describe(playername="角色名稱 (不輸入則使用已登錄的角色)")
    async def api_champion(self, interaction: discord.Interaction, playername: str = None):

        start_time = time.time()

        if playername is None:
            user_id = str(interaction.user.id)
            all_chars = user_db.get_all_user_characters(user_id)
            registered = {slot: name for slot, name in all_chars.items() if name}

            if len(registered) == 0:
                try:
                    await interaction.response.send_message(
                        "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                        ephemeral=True
                    )
                except NotFound:
                    logging.warning("Interaction expired before first response")
                return

            # 聯盟冠軍為帳號同世界共用，使用主要登錄角色即可
            playername = list(registered.values())[0]

        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_champion: Interaction expired before defer")
            return

        try:
            result = await asyncio.to_thread(
                create_champion_embed,
                playername)
            await interaction.followup.send(embed=result["embed"])
            response_time = time.time() - start_time
            UseSlashCommand('api_champion', interaction, response_time, result["success"])

        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"查詢聯盟冠軍時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_champion', interaction, response_time, False)


    @app_commands.command(name="uniontracking戰地追蹤", description="顯示角色近7日戰地聯盟成長分析")
    @app_commands.describe(character_name="角色名稱 (不輸入則使用已登錄的角色)")
    async def api_union_tracking(self, interaction: discord.Interaction, character_name: str = None):

        start_time = time.time()

        if character_name is None:
            user_id = str(interaction.user.id)
            all_chars = user_db.get_all_user_characters(user_id)
            registered = {slot: name for slot, name in all_chars.items() if name}

            # 無登錄角色
            if len(registered) == 0:
                try:
                    await interaction.response.send_message(
                        "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                        ephemeral=True
                    )
                except NotFound:
                    logging.warning("Interaction expired before first response")
                return

            # 只有 1 個角色 → 直接查詢
            if len(registered) == 1:
                character_name = list(registered.values())[0]
            else:
                # 多個角色 → 顯示合成圖 + 下拉選單
                try:
                    await interaction.response.defer()
                except NotFound:
                    logging.warning("api_union_tracking: Interaction expired before defer")
                    return

                select_view = UnionTrackingSelectView(registered, interaction, start_time)

                combined_image = await combine_character_images(all_chars)

                embed = discord.Embed(
                    title="📊 請選擇要追蹤的角色",
                    color=0x00bfff
                )

                if combined_image:
                    file = discord.File(combined_image, filename="characters.png")
                    embed.set_image(url="attachment://characters.png")
                    await interaction.followup.send(embed=embed, view=select_view, file=file)
                else:
                    await interaction.followup.send(embed=embed, view=select_view)
                return
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_union_tracking: Interaction expired before defer")
            return
        
        try:
            # Create union tracking embed
            result = await asyncio.to_thread(
                create_union_tracking_embed,
                character_name)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"])
                response_time = time.time() - start_time
                UseSlashCommand('api_uniontracking', interaction, response_time, True)
            else:
                await interaction.followup.send(embed=result["embed"])
                response_time = time.time() - start_time
                UseSlashCommand('api_uniontracking', interaction, response_time, False)
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成戰地聯盟追蹤資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_uniontracking', interaction, response_time, False)


    @app_commands.command(name="accounttracking帳號追蹤", description="列出同帳號所有角色的等級、經驗、戰力與近7日成長")
    @app_commands.describe(character_name="角色名稱 (不輸入則使用已登錄的角色)")
    async def api_account_tracking(self, interaction: discord.Interaction, character_name: str = None):

        start_time = time.time()

        if character_name is None:
            user_id = str(interaction.user.id)
            all_chars = user_db.get_all_user_characters(user_id)
            registered = {slot: name for slot, name in all_chars.items() if name}

            # 無登錄角色
            if len(registered) == 0:
                try:
                    await interaction.response.send_message(
                        "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                        ephemeral=True
                    )
                except NotFound:
                    logging.warning("Interaction expired before first response")
                return

            # 只有 1 個角色 → 直接查詢
            if len(registered) == 1:
                character_name = list(registered.values())[0]
            else:
                # 多個角色 → 顯示合成圖 + 下拉選單
                try:
                    await interaction.response.defer()
                except NotFound:
                    logging.warning("api_account_tracking: Interaction expired before defer")
                    return

                select_view = AccountTrackingSelectView(registered, interaction, start_time)

                combined_image = await combine_character_images(all_chars)

                embed = discord.Embed(
                    title="📒 請選擇要查詢的角色",
                    color=0x00bfff
                )

                if combined_image:
                    file = discord.File(combined_image, filename="characters.png")
                    embed.set_image(url="attachment://characters.png")
                    await interaction.followup.send(embed=embed, view=select_view, file=file)
                else:
                    await interaction.followup.send(embed=embed, view=select_view)
                return

        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_account_tracking: Interaction expired before defer")
            return

        try:
            ok = await send_account_tracking(interaction, character_name, start_time)
            UseSlashCommand('api_accounttracking', interaction,
                            time.time() - start_time, ok)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成帳號追蹤資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            UseSlashCommand('api_accounttracking', interaction,
                            time.time() - start_time, False)


    @app_commands.command(name="apianalyse楓谷分析", description="楓谷資料分析：職業、世界、等級、寶玉、裝備、CD帽、冠軍")
    @app_commands.describe(analysis_type="分析類型")
    @app_commands.choices(analysis_type=[
        app_commands.Choice(name="職業分析", value="class"),
        app_commands.Choice(name="世界分析", value="world"),
        app_commands.Choice(name="等級分析", value="level"),
        app_commands.Choice(name="寶玉排行", value="gem"),
        app_commands.Choice(name="裝備分析", value="equip"),
        app_commands.Choice(name="CD帽分析", value="hatcd"),
        app_commands.Choice(name="冠軍分析", value="champion")
    ])
    async def api_analyse(self, interaction: discord.Interaction, analysis_type: str = "class"):
        
        start_time = time.time()
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_analyse: Interaction expired before defer")
            return
        
        try:
            # 創建分析嵌入
            result = create_api_analyse_embed(analysis_type, include_view=True)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"], view=result["view"])
                response_time = time.time() - start_time
                UseSlashCommand('api_analyse', interaction, response_time, True)
            else:
                await interaction.followup.send(embed=result["embed"])
                response_time = time.time() - start_time
                UseSlashCommand('api_analyse', interaction, response_time, False)
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"生成資料分析時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_analyse', interaction, response_time, False)


    @app_commands.command(name="guild公會查詢", description="API公會查詢")
    @app_commands.describe(
        guild_name="公會名稱",
        world_name="伺服器名稱"
    )
    @app_commands.choices(world_name=[
        app_commands.Choice(name="艾麗亞", value="艾麗亞"),
        app_commands.Choice(name="普力特", value="普力特"),
        app_commands.Choice(name="琉德", value="琉德"),
        app_commands.Choice(name="優依娜", value="優依娜"),
        app_commands.Choice(name="愛麗西亞", value="愛麗西亞"),
        app_commands.Choice(name="挑戰者", value="挑戰者"),
        app_commands.Choice(name="殺人鯨", value="殺人鯨")
    ])
    async def api_guild_basic(self, interaction: discord.Interaction, guild_name: str, world_name: str):
        
        start_time = time.time()
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_guild_basic: Interaction expired before defer")
            return
        
        try:
            result = await asyncio.to_thread(
                create_guild_basic_embed, guild_name, world_name, include_view=True, build_view=False)
            if result.get("view_factory"):
                result["view"] = result["view_factory"]()   # View 必須在 event loop 上建
            embed = result["embed"]
            view = result["view"]
            
            await interaction.followup.send(embed=embed, view=view)
            response_time = time.time() - start_time
            UseSlashCommand('api_guild', interaction, response_time, True)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"查詢公會資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)
            response_time = time.time() - start_time
            UseSlashCommand('api_guild', interaction, response_time, False)

# 讓這支可以被 load_extension／reload_extension 熱抽換（2026-09-20）。
# setup_hook 改用 load_extension 之後，後台就能單獨重載這一個 cog，
# 不必為了改一行文案重啟整台 Bot（5 個 shard、近 5,000 個伺服器要重連）。
async def setup(client: commands.Bot):
    await client.add_cog(Slash_API(client))
