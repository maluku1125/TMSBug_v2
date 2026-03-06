import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from functions.database_manager import UserDataDB
from functions.SlashCommandManager import UseSlashCommand
from functions.CombineCharacter import combine_character_images

# 初始化資料庫
user_db = UserDataDB()

# slot 對應名稱
SLOT_NAMES = UserDataDB.SLOT_NAMES  # {1: '1本', 2: '2本', ...}


class UserSetting(discord.ui.Modal):
    """輸入遊戲角色ID的 Modal（支援多 slot）"""
    def __init__(self, slot: int = 1):
        self.slot = slot
        slot_label = SLOT_NAMES.get(slot, '1本')
        super().__init__(title=f"設定遊戲角色ID（{slot_label}）")

        self.character_input = discord.ui.TextInput(
            label=f"遊戲{slot_label}角色ID",
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
        slot_label = SLOT_NAMES.get(self.slot, '1本')

        # 檢查是否與其他 slot 的暱稱重複
        all_chars = user_db.get_all_user_characters(user_id)
        for other_slot, other_name in all_chars.items():
            if other_slot != self.slot and other_name and other_name == character_name:
                other_label = SLOT_NAMES.get(other_slot, f'{other_slot}本')
                await interaction.response.send_message(
                    f"❌ 角色ID `{character_name}` 已登錄在{other_label}，不可重複登記。",
                    ephemeral=True
                )
                return

        old_character = user_db.get_user_character_slot(user_id, self.slot)
        user_db.set_user_character_slot(user_id, self.slot, character_name)

        if old_character:
            await interaction.response.send_message(
                f"✅ 已更新您的{slot_label}角色ID！\n"
                f"舊角色ID：`{old_character}`\n"
                f"新角色ID：`{character_name}`",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"✅ 已設定您的{slot_label}角色ID為：`{character_name}`",
                ephemeral=True
            )


class SettingOverviewView(discord.ui.View):
    """設定總覽頁面的 View，包含 6 個 slot 的刪除按鈕"""
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.target_user_id = user_id
        self._create_buttons()

    def _create_buttons(self):
        """動態建立 6 個 slot 的刪除按鈕"""
        characters = user_db.get_all_user_characters(self.target_user_id)
        for slot in range(1, 7):
            slot_label = SLOT_NAMES[slot]
            button = discord.ui.Button(
                label=f"刪除{slot_label}",
                style=discord.ButtonStyle.danger,
                emoji="🗑️",
                custom_id=f"delete_slot_{slot}",
                disabled=characters[slot] is None,
                row=0 if slot <= 3 else 1,  # 上排 3 個、下排 3 個
            )
            button.callback = self._make_delete_callback(slot)
            self.add_item(button)

    def _make_delete_callback(self, slot: int):
        """為指定 slot 建立刪除回呼"""
        async def callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.target_user_id:
                await interaction.response.send_message("❌ 你無法操作他人的設定。", ephemeral=True)
                return

            slot_label = SLOT_NAMES[slot]
            character_name = user_db.get_user_character_slot(self.target_user_id, slot)
            if character_name is None:
                await interaction.response.send_message(
                    f"⚠️ 目前沒有{slot_label}設定可以刪除。", ephemeral=True
                )
                return

            user_db.remove_user_slot(self.target_user_id, slot)

            # 重建按鈕狀態與 Embed
            self.clear_items()
            self._create_buttons()
            embed = self._build_embed(interaction)
            embed.add_field(
                name="",
                value=f"✅ 已刪除{slot_label}設定 (`{character_name}`)",
                inline=False
            )

            # 重新合成角色圖片
            characters = user_db.get_all_user_characters(self.target_user_id)
            combined_image = await combine_character_images(characters)

            if combined_image:
                file = discord.File(combined_image, filename="characters.png")
                embed.set_image(url="attachment://characters.png")
                await interaction.response.edit_message(embed=embed, view=self, attachments=[file])
            else:
                embed.set_image(url=None)
                await interaction.response.edit_message(embed=embed, view=self, attachments=[])

        return callback

    def _build_embed(self, interaction: discord.Interaction) -> discord.Embed:
        """建立設定總覽 Embed"""
        characters = user_db.get_all_user_characters(self.target_user_id)

        lines = []
        for slot in range(1, 7):
            slot_label = SLOT_NAMES[slot]
            name = characters[slot]
            lines.append(f"{slot_label}：`{name}`" if name else f"{slot_label}：尚未設定")

        embed = discord.Embed(
            title="📋 個人設定總覽",
            description=f"使用者：{interaction.user.mention}",
            color=0x00bfff
        )
        embed.add_field(
            name="🎮 已登錄的角色",
            value="\n".join(lines),
            inline=False
        )
        embed.set_footer(text="使用 /setting設定 type:1本~6本 來修改設定")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Slash_Setting(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.command(name="setting設定", description="TMS_Bug個人設定")
    @app_commands.describe(type="類型 (不輸入則顯示當前設定)")
    @app_commands.choices(type=[
        app_commands.Choice(name="1本", value="slot_1"),
        app_commands.Choice(name="2本", value="slot_2"),
        app_commands.Choice(name="3本", value="slot_3"),
        app_commands.Choice(name="4本", value="slot_4"),
        app_commands.Choice(name="5本", value="slot_5"),
        app_commands.Choice(name="6本", value="slot_6"),
    ])

    async def setting(self, interaction: discord.Interaction, type: Optional[app_commands.Choice[str]] = None):
        # 未輸入類型 → 顯示當前已設定的項目（含刪除按鈕 + 合成角色圖片）
        if type is None:
            user_id = str(interaction.user.id)
            view = SettingOverviewView(user_id)
            embed = view._build_embed(interaction)
            UseSlashCommand('setting', interaction)

            # 合成角色圖片
            characters = user_db.get_all_user_characters(user_id)
            combined_image = await combine_character_images(characters)

            if combined_image:
                file = discord.File(combined_image, filename="characters.png")
                embed.set_image(url="attachment://characters.png")
                await interaction.response.send_message(embed=embed, view=view, file=file, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        # 解析 slot 編號（slot_1 ~ slot_6）
        slot = int(type.value.split('_')[1])
        UseSlashCommand('setting', interaction)
        modal = UserSetting(slot=slot)
        await interaction.response.send_modal(modal)


async def setup(client: commands.Bot):
    await client.add_cog(Slash_Setting(client))