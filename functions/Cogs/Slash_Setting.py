import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import re

from functions.database_manager import UserDataDB
from functions.SlashCommandManager import UseSlashCommand
from functions.CombineCharacter import combine_character_images

# 初始化資料庫
user_db = UserDataDB()

# slot 對應名稱
SLOT_NAMES = UserDataDB.SLOT_NAMES  # {1: '1本', 2: '2本', ...}
NAME_TO_SLOT = {v: k for k, v in SLOT_NAMES.items()}  # {'1本': 1, ...}


# ----------------------------------------------------------------------------
# 角色動作（action / emotion / wmotion）對應表，供引導 embed 顯示
# 參數說明來源：Nexon Open API 角色外型圖片文件
# ----------------------------------------------------------------------------
ACTION_MAP = {
    'A00': 'stand1(預設)', 'A01': 'stand2', 'A02': 'walk1', 'A03': 'walk2',
    'A04': 'prone', 'A05': 'fly', 'A06': 'jump', 'A07': 'sit', 'A08': 'ladder',
    'A09': 'rope', 'A10': 'heal', 'A11': 'alert', 'A12': 'proneStab',
    'A13': 'swingO1', 'A14': 'swingO2', 'A15': 'swingO3', 'A16': 'swingOF',
    'A17': 'swingP1', 'A18': 'swingP2', 'A19': 'swingPF', 'A20': 'swingT1',
    'A21': 'swingT2', 'A22': 'swingT3', 'A23': 'swingTF', 'A24': 'stabO1',
    'A25': 'stabO2', 'A26': 'stabOF', 'A27': 'stabT1', 'A28': 'stabT2',
    'A29': 'stabTF', 'A30': 'shoot1', 'A31': 'shoot2', 'A32': 'shootF',
    'A33': 'dead', 'A34': 'ghostwalk', 'A35': 'ghoststand', 'A36': 'ghostjump',
    'A37': 'ghostproneStab', 'A38': 'ghostladder', 'A39': 'ghostrope',
    'A40': 'ghostfly', 'A41': 'ghostsit',
}
EMOTION_MAP = {
    'E00': 'default(預設)', 'E01': 'wink', 'E02': 'smile', 'E03': 'cry',
    'E04': 'angry', 'E05': 'bewildered', 'E06': 'blink', 'E07': 'blaze',
    'E08': 'bowing', 'E09': 'cheers', 'E10': 'chu', 'E11': 'dam',
    'E12': 'despair', 'E13': 'glitter', 'E14': 'hit', 'E15': 'hot',
    'E16': 'hum', 'E17': 'love', 'E18': 'oops', 'E19': 'pain',
    'E20': 'troubled', 'E21': 'qBlue', 'E22': 'shine', 'E23': 'stunned',
    'E24': 'vomit',
}
WMOTION_MAP = {
    'W00': '預設(依武器類型)', 'W01': '單手武器', 'W02': '雙手武器',
    'W03': '槍械', 'W04': '無武器',
}

# 驗證用 regex（允許 action/emotion 後面接 .影格，如 A02.3）
_ACTION_RE = re.compile(r'^A(\d{2})(?:\.\d+)?$')
_EMOTION_RE = re.compile(r'^E(\d{2})(?:\.\d+)?$')
_WMOTION_RE = re.compile(r'^W0[0-4]$')


def _validate_action(value: str) -> bool:
    m = _ACTION_RE.match(value)
    return bool(m) and 0 <= int(m.group(1)) <= 41


def _validate_emotion(value: str) -> bool:
    m = _EMOTION_RE.match(value)
    return bool(m) and 0 <= int(m.group(1)) <= 24


def _validate_wmotion(value: str) -> bool:
    return bool(_WMOTION_RE.match(value))


def _format_map(mapping: dict) -> str:
    """把對應表格式化為每行一筆 `code` name 的字串（換行排版，較易閱讀）"""
    return '\n'.join(f"`{code}` {name}" for code, name in mapping.items())


def _format_columns(mapping: dict, n_cols: int = 3) -> list:
    """把對應表切成 n_cols 欄（連續代碼沿欄往下排），回傳各欄的字串清單"""
    import math
    items = [f"`{code}` {name}" for code, name in mapping.items()]
    per = math.ceil(len(items) / n_cols)
    cols = [items[i * per:(i + 1) * per] for i in range(n_cols)]
    return ['\n'.join(c) for c in cols if c]


def _add_columned_field(embed: discord.Embed, title: str, mapping: dict, n_cols: int = 3):
    """以多個 inline 欄位把對應表並排顯示，標題放在第一欄上方"""
    cols = _format_columns(mapping, n_cols)
    for idx, col in enumerate(cols):
        embed.add_field(name=title if idx == 0 else "​", value=col, inline=True)


def build_action_reference_embed(current: dict) -> discord.Embed:
    """建立角色動作設定的引導 Embed（顯示目前設定 + 所有可用代碼）"""
    embed = discord.Embed(
        title="🎭 角色動作設定",
        description=(
            "設定 `/character` 角色圖片要顯示的**動作 / 表情 / 武器動作**。\n"
            "點下方 **✏️ 設定動作** 按鈕輸入代碼即可。\n"
            "💡 動作與表情可在後面加上 `.影格` 逐格檢視，例如 `A02.3`、`E06.1`。"
        ),
        color=0x00bfff,
    )

    # 目前設定
    cur_action = current.get('action') or 'A00(預設)'
    cur_emotion = current.get('emotion') or 'E00(預設)'
    cur_wmotion = current.get('wmotion') or 'W00(預設)'
    cur_animated = '🎬 開啟' if current.get('animated') else '關閉'
    embed.add_field(
        name="🔧 目前設定",
        value=(f"動作：`{cur_action}`\n表情：`{cur_emotion}`\n"
               f"武器動作：`{cur_wmotion}`\n動畫：{cur_animated}"),
        inline=False,
    )

    _add_columned_field(embed, "🏃 動作 action (A00~A41)", ACTION_MAP, n_cols=3)
    _add_columned_field(embed, "😀 表情 emotion (E00~E24)", EMOTION_MAP, n_cols=3)
    embed.add_field(name="⚔️ 武器動作 wmotion (W00~W04)", value=_format_map(WMOTION_MAP), inline=False)
    embed.set_footer(text="留空的欄位代表恢復預設值")
    return embed


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


class ActionSettingModal(discord.ui.Modal):
    """輸入角色動作（action / emotion / wmotion）的 Modal"""
    def __init__(self, current: dict):
        super().__init__(title="設定角色動作")

        self.action_input = discord.ui.TextInput(
            label="動作 action (A00~A41)",
            placeholder="例：A00 或 A02.3（可加影格），留空＝預設",
            default=current.get('action') or "",
            required=False,
            max_length=10,
        )
        self.emotion_input = discord.ui.TextInput(
            label="表情 emotion (E00~E24)",
            placeholder="例：E00 或 E06.1，留空＝預設",
            default=current.get('emotion') or "",
            required=False,
            max_length=10,
        )
        self.wmotion_input = discord.ui.TextInput(
            label="武器動作 wmotion (W00~W04)",
            placeholder="例：W00，留空＝預設",
            default=current.get('wmotion') or "",
            required=False,
            max_length=10,
        )
        self.add_item(self.action_input)
        self.add_item(self.emotion_input)
        self.add_item(self.wmotion_input)

    async def on_submit(self, interaction: discord.Interaction):
        action = (self.action_input.value or "").strip().upper() or None
        emotion = (self.emotion_input.value or "").strip().upper() or None
        wmotion = (self.wmotion_input.value or "").strip().upper() or None

        # 驗證格式
        errors = []
        if action and not _validate_action(action):
            errors.append(f"動作 `{action}` 格式錯誤（應為 A00~A41，可加 .影格）")
        if emotion and not _validate_emotion(emotion):
            errors.append(f"表情 `{emotion}` 格式錯誤（應為 E00~E24，可加 .影格）")
        if wmotion and not _validate_wmotion(wmotion):
            errors.append(f"武器動作 `{wmotion}` 格式錯誤（應為 W00~W04）")

        if errors:
            await interaction.response.send_message("❌ " + "\n".join(errors), ephemeral=True)
            return

        user_id = str(interaction.user.id)
        user_db.set_user_action(user_id, action, emotion, wmotion)

        # 先 defer，避免後續預覽的 API 請求超過互動回應時限
        await interaction.response.defer(ephemeral=True)

        confirm_embed = discord.Embed(
            title="✅ 已更新角色動作",
            description=(
                f"動作：`{action or 'A00(預設)'}`\n"
                f"表情：`{emotion or 'E00(預設)'}`\n"
                f"武器動作：`{wmotion or 'W00(預設)'}`\n\n"
                "之後使用 `/character` 時角色圖片就會套用此姿勢。"
            ),
            color=discord.Color.green(),
        )

        # 嘗試用使用者的 1本角色做預覽縮圖（best-effort，失敗不影響設定）
        try:
            preview_name = user_db.get_user_character_slot(user_id, 1)
            if preview_name:
                from functions.API_functions.API_Request_Character import get_character_ocid, request_character_basic
                from functions.API_functions.CreateCharacterEmbed import apply_look_params
                ocid = get_character_ocid(preview_name)
                if ocid:
                    basic = request_character_basic(ocid)
                    image_url = basic.get('character_image') if basic else None
                    if image_url:
                        preview_url = apply_look_params(image_url, action, emotion, wmotion)
                        confirm_embed.set_thumbnail(url=preview_url)
                        confirm_embed.set_footer(text=f"預覽：{preview_name}")
        except Exception:
            pass

        await interaction.followup.send(embed=confirm_embed, ephemeral=True)


class ActionSettingView(discord.ui.View):
    """角色動作引導頁的 View：開啟設定 Modal / 重設為預設"""
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.target_user_id = user_id

    @discord.ui.button(label="設定動作", style=discord.ButtonStyle.primary, emoji="✏️")
    async def set_action_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_user_id:
            await interaction.response.send_message("❌ 你無法操作他人的設定。", ephemeral=True)
            return
        current = user_db.get_user_action(self.target_user_id)
        await interaction.response.send_modal(ActionSettingModal(current))

    @discord.ui.button(label="切換動畫", style=discord.ButtonStyle.secondary, emoji="🎬")
    async def toggle_animated_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_user_id:
            await interaction.response.send_message("❌ 你無法操作他人的設定。", ephemeral=True)
            return
        current = user_db.get_user_action(self.target_user_id)
        new_state = not current.get('animated')
        user_db.set_user_animated(self.target_user_id, new_state)
        embed = build_action_reference_embed(user_db.get_user_action(self.target_user_id))
        embed.add_field(
            name="​",
            value=(f"🎬 動畫已開啟，/character 與 /exptracking 的角色圖會以動作動畫顯示。"
                   if new_state else "動畫已關閉，恢復靜態圖片。"),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="重設為預設", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.target_user_id:
            await interaction.response.send_message("❌ 你無法操作他人的設定。", ephemeral=True)
            return
        user_db.set_user_action(self.target_user_id, None, None, None)
        embed = build_action_reference_embed(user_db.get_user_action(self.target_user_id))
        embed.add_field(name="​", value="🔄 已重設為預設動作。", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


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
        embed.set_footer(text="使用 /setting設定 type:角色 type2:1本~6本 來修改設定")
        return embed

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


class Slash_Setting(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    async def _show_overview(self, interaction: discord.Interaction):
        """顯示設定總覽（含刪除按鈕 + 合成角色圖片）"""
        user_id = str(interaction.user.id)
        view = SettingOverviewView(user_id)
        embed = view._build_embed(interaction)

        characters = user_db.get_all_user_characters(user_id)
        combined_image = await combine_character_images(characters)

        if combined_image:
            file = discord.File(combined_image, filename="characters.png")
            embed.set_image(url="attachment://characters.png")
            await interaction.response.send_message(embed=embed, view=view, file=file, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="setting設定", description="TMS_Bug個人設定")
    @app_commands.describe(
        type="類型（不選則顯示設定總覽）",
        type2="細項（選「角色」後可填 1本~6本；「角色動作」免填）",
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="角色", value="character"),
        app_commands.Choice(name="角色動作", value="action"),
    ])
    async def setting(self, interaction: discord.Interaction,
                      type: Optional[app_commands.Choice[str]] = None,
                      type2: Optional[str] = None):
        user_id = str(interaction.user.id)
        type_value = type.value if type else None
        UseSlashCommand('setting', interaction)

        # 角色動作：直接顯示引導 Embed（忽略 type2）
        if type_value == 'action':
            current = user_db.get_user_action(user_id)
            embed = build_action_reference_embed(current)
            view = ActionSettingView(user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        # 角色 + 指定本數 → 開啟登記 Modal
        if type_value == 'character' and type2:
            slot = NAME_TO_SLOT.get(type2.strip())
            if slot is None:
                await interaction.response.send_message(
                    f"❌ 無效的本數：`{type2}`（請從 1本~6本 中選擇）", ephemeral=True
                )
                return
            await interaction.response.send_modal(UserSetting(slot=slot))
            return

        # 其他情況（未選 type，或選了角色但沒指定本數）→ 顯示設定總覽
        await self._show_overview(interaction)

    @setting.autocomplete('type2')
    async def setting_type2_autocomplete(self, interaction: discord.Interaction, current: str):
        """type2 依 type 動態預填：選「角色」時提供 1本~6本"""
        selected_type = getattr(interaction.namespace, 'type', None)
        if selected_type == 'character':
            current = current or ''
            return [
                app_commands.Choice(name=label, value=label)
                for label in SLOT_NAMES.values()
                if current in label
            ][:25]
        # 角色動作 不需要 type2
        return []


async def setup(client: commands.Bot):
    await client.add_cog(Slash_Setting(client))
