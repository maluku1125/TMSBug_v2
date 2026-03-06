import discord
from discord import app_commands
from discord.ext import commands

import datetime
import time
import logging
from discord.errors import NotFound
from functions.API_functions.CreateCharacterEmbed import create_character_basic_embed
from functions.API_functions.CreateGuildEmbed import create_guild_basic_embed   
from functions.API_functions.CreateCharacterEquipmentEmbed import create_character_equipment_embed
from functions.API_functions.API_Ranking import get_all_characters_level_exp_ranking
from functions.API_functions.CreateRankingEmbed import create_ranking_embed
from functions.API_functions.CreateEXPTrackingEmbed import create_exp_tracking_embed
from functions.API_functions.CreateUnionTrackingEmbed import create_union_tracking_embed
from functions.API_functions.CreateAPIAnalyseEmbed import create_api_analyse_embed

from functions.SlashCommandManager import UseSlashCommand
from functions.database_manager import UserDataDB
from functions.CombineCharacter import combine_character_images

user_db = UserDataDB()
SLOT_NAMES = UserDataDB.SLOT_NAMES


class CharacterView(discord.ui.View):
    def __init__(self, character_name: str, character_basic_data: dict = None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.character_name = character_name
        self.character_basic_data = character_basic_data
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
            result = create_character_basic_embed(self.character_name, return_data=True)
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
                    await interaction.edit_original_response(embed=embed, view=self)
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
                result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    view.current_preset = "preset_1"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.edit_original_response(embed=embed, view=view)
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
                result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    view.current_preset = "preset_2"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.edit_original_response(embed=embed, view=view)
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
                result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    view.current_preset = "preset_3"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.edit_original_response(embed=embed, view=view)
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
            view = CharacterView(selected_name)
            embed = view.get_character_basic_embed()

            if embed:
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
            result = create_exp_tracking_embed(selected_name)
            if result["success"]:
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
                await interaction.response.send_message(
                    "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                    ephemeral=True
                )
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
            view = CharacterView(playername)
            embed = view.get_character_basic_embed()
            
            if embed:
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
                await interaction.response.send_message(
                    "❌ 請輸入角色名稱，或先使用 `/setting設定 type:1本` 設定您的遊戲角色ID。",
                    ephemeral=True
                )
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
            result = create_exp_tracking_embed(character_name)
            
            if result["success"]:
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


    @app_commands.command(name="uniontracking戰地追蹤", description="顯示角色近7日戰地聯盟成長分析")
    @app_commands.describe(character_name="角色名稱")
    async def api_union_tracking(self, interaction: discord.Interaction, character_name: str):
        
        start_time = time.time()
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_union_tracking: Interaction expired before defer")
            return
        
        try:
            # Create union tracking embed
            result = create_union_tracking_embed(character_name)
            
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


    @app_commands.command(name="apianalyse楓谷分析", description="API資料分析")
    @app_commands.describe(analysis_type="分析類型")
    @app_commands.choices(analysis_type=[
        app_commands.Choice(name="職業分析", value="class"),
        app_commands.Choice(name="世界分析", value="world"),
        app_commands.Choice(name="等級分析", value="level")
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
        app_commands.Choice(name="米特拉", value="米特拉"),
        app_commands.Choice(name="挑戰者", value="挑戰者"),
        app_commands.Choice(name="殺人鯨", value="殺人鯨"),
        app_commands.Choice(name="賽蓮", value="賽蓮")
    ])
    async def api_guild_basic(self, interaction: discord.Interaction, guild_name: str, world_name: str):
        
        start_time = time.time()
        
        try:
            await interaction.response.defer()
        except NotFound:
            logging.warning("api_guild_basic: Interaction expired before defer")
            return
        
        try:
            result = create_guild_basic_embed(guild_name, world_name, include_view=True)
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