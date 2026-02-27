import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from functions.database_manager import UserDataDB

# 初始化資料庫
user_db = UserDataDB()


class UserSetting(discord.ui.Modal):
    """輸入遊戲角色ID的 Modal"""
    def __init__(self):
        super().__init__(title="設定遊戲角色ID")

        self.character_input = discord.ui.TextInput(
            label="遊戲本尊角色ID",
            placeholder="請輸入ID(輸入視同同意BOT儲存您的角色ID)",
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )
        self.add_item(self.character_input)

    async def on_submit(self, interaction: discord.Interaction):
        character_name = self.character_input.value.strip()

        if not character_name:
            await interaction.response.send_message("❌ 角色ID不能為空白。", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        old_character = user_db.get_user_character(user_id)
        user_db.set_user_character(user_id, character_name)

        if old_character:
            await interaction.response.send_message(
                f"✅ 已更新您的遊戲角色ID！\n"
                f"舊角色ID：`{old_character}`\n"
                f"新角色ID：`{character_name}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"✅ 已設定您的遊戲角色ID為：`{character_name}`",
                ephemeral=True
            )


class SettingOverviewView(discord.ui.View):
    """設定總覽頁面的 View，包含刪除按鈕"""
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.target_user_id = user_id
        self._update_buttons()

    def _update_buttons(self):
        """根據目前設定狀態更新按鈕"""
        character_name = user_db.get_user_character(self.target_user_id)
        # 如果沒有任何已設定的項目，停用刪除按鈕
        self.delete_character_btn.disabled = character_name is None

    def _build_embed(self, interaction: discord.Interaction) -> discord.Embed:
        """建立設定總覽 Embed"""
        character_name = user_db.get_user_character(self.target_user_id)

        embed = discord.Embed(
            title="📋 個人設定總覽",
            description=f"使用者：{interaction.user.mention}",
            color=0x00bfff
        )
        embed.add_field(
            name="🎮 本尊 (遊戲角色ID)",
            value=f"`{character_name}`" if character_name else "尚未設定",
            inline=False
        )
        embed.set_footer(text="使用 /setting設定 type:本尊 來修改設定")
        return embed

    @discord.ui.button(label="刪除本尊設定", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_character_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 確保只有本人能操作
        if str(interaction.user.id) != self.target_user_id:
            await interaction.response.send_message("❌ 你無法操作他人的設定。", ephemeral=True)
            return

        character_name = user_db.get_user_character(self.target_user_id)
        if character_name is None:
            await interaction.response.send_message("⚠️ 目前沒有本尊設定可以刪除。", ephemeral=True)
            return

        user_db.remove_user(self.target_user_id)

        # 更新按鈕狀態與 Embed
        self._update_buttons()
        embed = self._build_embed(interaction)
        embed.add_field(
            name="",
            value=f"✅ 已刪除本尊設定 (`{character_name}`)",
            inline=False
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Slash_Setting(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="setting設定", description="TMS_Bug個人設定")
    @app_commands.describe(type="類型 (不輸入則顯示當前設定)")
    @app_commands.choices(type=[
        app_commands.Choice(name="本尊", value="MainCharacter"),
    ])
    async def setting(self, interaction: discord.Interaction, type: Optional[app_commands.Choice[str]] = None):
        # 未輸入類型 → 顯示當前已設定的項目（含刪除按鈕）
        if type is None:
            user_id = str(interaction.user.id)
            view = SettingOverviewView(user_id)
            embed = view._build_embed(interaction)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        # 選擇本尊 → 彈出 Modal 輸入角色ID
        if type.value == "MainCharacter":
            modal = UserSetting()
            await interaction.response.send_modal(modal)


async def setup(client: commands.Bot):
    await client.add_cog(Slash_Setting(client))