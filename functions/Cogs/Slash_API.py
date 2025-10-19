import discord
from discord import app_commands
from discord.ext import commands

import datetime
from functions.API_functions.CreateCharacterEmbed import create_character_basic_embed
from functions.API_functions.CreateGuildEmbed import create_guild_basic_embed   
from functions.API_functions.CreateCharacterEquipmentEmbed import create_character_equipment_embed
from functions.API_functions.API_Ranking import get_all_characters_level_exp_ranking
from functions.API_functions.CreateRankingEmbed import create_ranking_embed

from functions.SlashCommandManager import UseSlashCommand


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
        if self.current_mode != "character":
            self.current_mode = "character"
            self._update_button_styles()
            embed = self.get_character_basic_embed()
            if embed:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                await interaction.response.defer()
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="預設1", style=discord.ButtonStyle.success)
    async def preset_1_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_mode != "preset_1":
            self.current_mode = "preset_1"
            # Create complete equipment View
            try:
                result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    # Set to preset 1
                    view.current_preset = "preset_1"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.response.edit_message(embed=embed, view=view)
                else:
                    error_embed = discord.Embed(
                        title="錯誤",
                        description="無法獲取預設1的裝備資訊",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=error_embed, view=self)
            except Exception as e:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"載入裝備資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=error_embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="預設2", style=discord.ButtonStyle.success)
    async def preset_2_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_mode != "preset_2":
            self.current_mode = "preset_2"
            # Create complete equipment View
            try:
                result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    # Set to preset 2
                    view.current_preset = "preset_2"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.response.edit_message(embed=embed, view=view)
                else:
                    error_embed = discord.Embed(
                        title="錯誤",
                        description="無法獲取預設2的裝備資訊",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=error_embed, view=self)
            except Exception as e:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"載入裝備資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=error_embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="預設3", style=discord.ButtonStyle.success)
    async def preset_3_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_mode != "preset_3":
            self.current_mode = "preset_3"
            # Create complete equipment View
            try:
                result = create_character_equipment_embed(self.character_name, self.character_basic_data)
                embed = result["embed"]
                view = result["view"]
                
                if view and embed:
                    # Set to preset 3
                    view.current_preset = "preset_3"
                    view._process_equipment_data()
                    view._update_preset_button_styles()
                    embed = view.create_embed("weapon")
                    await interaction.response.edit_message(embed=embed, view=view)
                else:
                    error_embed = discord.Embed(
                        title="錯誤",
                        description="無法獲取預設3的裝備資訊",
                        color=discord.Color.red()
                    )
                    await interaction.response.edit_message(embed=error_embed, view=self)
            except Exception as e:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"載入裝備資訊時發生錯誤: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=error_embed, view=self)
        else:
            await interaction.response.defer()
    
    async def on_timeout(self):
        # Disable all components after timeout
        for item in self.children:
            item.disabled = True


class Slash_API(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="character角色查詢", description="API角色查詢")
    async def api_character_basic(self, interaction: discord.Interaction, playername: str):
        
        await interaction.response.defer()

        UseSlashCommand('api_character', interaction)
        
        try:
            # Create character data View
            view = CharacterView(playername)
            embed = view.get_character_basic_embed()
            
            if embed:
                await interaction.followup.send(embed=embed, view=view)
            else:
                error_embed = discord.Embed(
                    title="錯誤",
                    description=f"無法獲取角色 '{playername}' 的資訊",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=error_embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="錯誤",
                description=f"生成角色資訊時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)


    @app_commands.command(name="rank排行", description="顯示角色等級經驗排行榜")
    @app_commands.describe(character_class="職業")
    async def api_character_ranking(self, interaction: discord.Interaction, character_class: str = None):
        
        await interaction.response.defer()
        UseSlashCommand('api_ranking', interaction)
        
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
                    return
            
            # 使用 create_ranking_embed 函數 (全伺服器TOP100，各世界TOP50)
            result = create_ranking_embed(ranking_data, include_view=True, character_class=character_class)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"], view=result["view"])
            else:
                await interaction.followup.send(embed=result["embed"])
            
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ 錯誤",
                description=f"獲取排行榜資料時發生錯誤: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed)


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
        
        await interaction.response.defer()
        UseSlashCommand('api_guild', interaction)

        result = create_guild_basic_embed(guild_name, world_name, include_view=True)
        embed = result["embed"]
        view = result["view"]
        
        await interaction.followup.send(embed=embed, view=view)