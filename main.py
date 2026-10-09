import os
import random
import string
import discord
from discord import app_commands
from discord.ext import commands
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
bot = commands.Bot(
    command_prefix="!",
    intents=intents
)
# =========================================================
# SPRACHBUTTONS AUF DEM FERTIGEN EMBED
# =========================================================
class LanguageView(discord.ui.View):
    def __init__(self, german_embed, english_embed):
        super().__init__(timeout=None)
        self.german_embed = german_embed
        self.english_embed = english_embed
    @discord.ui.button(
        label="Deutsch",
        emoji="🇩🇪",
        style=discord.ButtonStyle.secondary
    )
    async def german_button(self, interaction, button):
        await interaction.response.send_message(
            embed=self.german_embed,
            ephemeral=True
        )
    @discord.ui.button(
        label="English",
        emoji="🇬🇧",
        style=discord.ButtonStyle.secondary
    )
    async def english_button(self, interaction, button):
        await interaction.response.send_message(
            embed=self.english_embed,
            ephemeral=True
        )
# =========================================================
# EMBED DATEN
# =========================================================
class EmbedData:
    def __init__(self):
        self.german_title = ""
        self.german_description = ""
        self.english_title = ""
        self.english_description = ""
        self.color = 0x5865F2
        self.bilingual = False
# =========================================================
# HAUPTMENÜ
# =========================================================
class EmbedMenuView(discord.ui.View):
    def __init__(self, data):
        super().__init__(timeout=600)
        self.data = data
        self.update_buttons()
    def update_buttons(self):
        self.language_edit_button.disabled = not self.data.bilingual
        if self.data.bilingual:
            self.language_toggle_button.label = "Zweitsprache: AN"
            self.language_toggle_button.style = discord.ButtonStyle.success
        else:
            self.language_toggle_button.label = "Zweitsprache: AUS"
            self.language_toggle_button.style = discord.ButtonStyle.secondary
    def menu_text(self):
        german_status = (
            "✅ Ausgefüllt"
            if self.data.german_title and self.data.german_description
            else "⚪ Nicht ausgefüllt"
        )
        english_status = (
            "✅ Ausgefüllt"
            if self.data.english_title and self.data.english_description
            else "⚪ Nicht ausgefüllt"
        )
        language_status = (
            "🟢 Aktiv"
            if self.data.bilingual
            else "⚪ Deaktiviert"
        )
        return (
            "## 📝 Embed erstellen\n\n"
            "**🇩🇪 Deutsch**\n"
            f"{german_status}\n\n"
            "**🇬🇧 Englisch**\n"
            f"{english_status}\n\n"
            "**🌐 Zweitsprache**\n"
            f"{language_status}\n\n"
            "**🎨 Embed-Farbe**\n"
            f"`#{self.data.color:06X}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Bearbeite die gewünschten Bereiche über die Buttons."
        )
    @discord.ui.button(
        label="Deutsch & Design bearbeiten",
        emoji="📝",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def german_edit_button(self, interaction, button):
        await interaction.response.send_modal(
            EmbedContentModal(self.data)
        )
    @discord.ui.button(
        label="Zweitsprache: AUS",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def language_toggle_button(self, interaction, button):
        self.data.bilingual = not self.data.bilingual
        self.update_buttons()
        await interaction.response.edit_message(
            content=self.menu_text(),
            view=self
        )
    @discord.ui.button(
        label="English bearbeiten",
        emoji="🇬🇧",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def language_edit_button(self, interaction, button):
        if not self.data.bilingual:
            await interaction.response.send_message(
                "❌ Aktiviere zuerst **Zweitsprache**, "
                "bevor du Englisch bearbeiten kannst.",
                ephemeral=True
            )
            return
        await interaction.response.send_modal(
            EnglishModal(self.data)
        )
    @discord.ui.button(
        label="Weiter",
        emoji="➡️",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def continue_button(self, interaction, button):
        if not self.data.german_title or not self.data.german_description:
            await interaction.response.send_message(
                "❌ Bitte fülle zuerst die deutsche Version aus.",
                ephemeral=True
            )
            return
        if self.data.bilingual:
            if not self.data.english_title or not self.data.english_description:
                await interaction.response.send_message(
                    "❌ Du hast die Zweitsprache aktiviert. "
                    "Bitte fülle auch die englische Version aus.",
                    ephemeral=True
                )
                return
        german_embed = discord.Embed(
            title=self.data.german_title,
            description=self.data.german_description,
            color=discord.Color(self.data.color)
        )
        english_embed = None
        if self.data.bilingual:
            english_embed = discord.Embed(
                title=self.data.english_title,
                description=self.data.english_description,
                color=discord.Color(self.data.color)
            )
        await interaction.response.edit_message(
            content=(
                "## 📢 Kanal auswählen\n\n"
                "Wähle den Textkanal aus, in dem der Embed "
                "veröffentlicht werden soll."
            ),
            view=ChannelSelectView(
                german_embed,
                english_embed,
                self.data.bilingual
            )
        )
# =========================================================
# DEUTSCH + FARBE
# =========================================================
class EmbedContentModal(discord.ui.Modal):
    def __init__(self, data):
        super().__init__(title="Embed bearbeiten")
        self.data = data
        self.german_title = discord.ui.TextInput(
            label="Deutscher Titel",
            placeholder="z. B. SERVER REGELN",
            default=data.german_title or None,
            required=True,
            max_length=256
        )
        self.german_description = discord.ui.TextInput(
            label="Deutsche Nachricht",
            placeholder="Dein deutscher Inhalt...",
            default=data.german_description or None,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.color_input = discord.ui.TextInput(
            label="Hex-Farbe",
            placeholder="#5865F2",
            default=f"#{data.color:06X}",
            required=True,
            max_length=7
        )
        self.add_item(self.german_title)
        self.add_item(self.german_description)
        self.add_item(self.color_input)
    async def on_submit(self, interaction):
        color_text = self.color_input.value.strip()
        if color_text.startswith("#"):
            color_text = color_text[1:]
        try:
            if len(color_text) != 6:
                raise ValueError
            color_value = int(color_text, 16)
        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültige Hex-Farbe.\nBeispiel: `#5865F2`",
                ephemeral=True
            )
            return
        self.data.german_title = self.german_title.value
        self.data.german_description = self.german_description.value
        self.data.color = color_value
        view = EmbedMenuView(self.data)
        await interaction.response.edit_message(
            content=view.menu_text(),
            view=view
        )
# =========================================================
# ENGLISCH
# =========================================================
class EnglishModal(discord.ui.Modal):
    def __init__(self, data):
        super().__init__(title="Englische Version")
        self.data = data
        self.english_title = discord.ui.TextInput(
            label="Englischer Titel",
            placeholder="z. B. SERVER RULES",
            default=data.english_title or None,
            required=True,
            max_length=256
        )
        self.english_description = discord.ui.TextInput(
            label="Englische Nachricht",
            placeholder="Your English content...",
            default=data.english_description or None,
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )
        self.add_item(self.english_title)
        self.add_item(self.english_description)
    async def on_submit(self, interaction):
        self.data.english_title = self.english_title.value
        self.data.english_description = self.english_description.value
        view = EmbedMenuView(self.data)
        await interaction.response.edit_message(
            content=view.menu_text(),
            view=view
        )
# =========================================================
# KANAL AUSWÄHLEN
# =========================================================
class ChannelSelectView(discord.ui.View):
    def __init__(self, german_embed, english_embed, bilingual):
        super().__init__(timeout=300)
        self.german_embed = german_embed
        self.english_embed = english_embed
        self.bilingual = bilingual
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Zielkanal auswählen...",
        channel_types=[discord.ChannelType.text],
        min_values=1,
        max_values=1
    )
    async def channel_select(self, interaction, select):
        selected_channel = select.values[0]
        channel_id = selected_channel.id
        channel = interaction.guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    "❌ Der Kanal wurde nicht gefunden.",
                    ephemeral=True
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich kann diesen Kanal nicht abrufen.",
                    ephemeral=True
                )
                return
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bitte wähle einen normalen Textkanal.",
                ephemeral=True
            )
            return
        await interaction.response.edit_message(
            content=(
                "## 📤 Embed veröffentlichen\n\n"
                f"**Ziel:** {channel.mention}\n\n"
                "Drücke den Button unten, um den Embed zu senden."
            ),
            view=ConfirmView(
                self.german_embed,
                self.english_embed,
                self.bilingual,
                channel
            )
        )
# =========================================================
# EMBED BESTÄTIGUNG
# =========================================================
class ConfirmView(discord.ui.View):
    def __init__(self, german_embed, english_embed, bilingual, channel):
        super().__init__(timeout=300)
        self.german_embed = german_embed
        self.english_embed = english_embed
        self.bilingual = bilingual
        self.channel = channel
    @discord.ui.button(
        label="Embed senden",
        emoji="🚀",
        style=discord.ButtonStyle.success
    )
    async def send_embed(self, interaction, button):
        try:
            if self.bilingual:
                await self.channel.send(
                    embed=self.german_embed,
                    view=LanguageView(
                        self.german_embed,
                        self.english_embed
                    )
                )
            else:
                await self.channel.send(embed=self.german_embed)
            button.disabled = True
            await interaction.response.edit_message(
                content=(
                    f"✅ Embed wurde erfolgreich in "
                    f"{self.channel.mention} veröffentlicht."
                ),
                view=self
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Der Bot hat in diesem Kanal nicht die "
                "benötigten Berechtigungen.\n\n"
                "Benötigt:\n"
                "• Kanal ansehen\n"
                "• Nachrichten senden\n"
                "• Links einbetten",
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Dieser Kanal existiert nicht mehr.",
                ephemeral=True
            )
        except Exception as error:
            await interaction.response.send_message(
                f"❌ Unerwarteter Fehler:\n`{error}`",
                ephemeral=True
            )
# =========================================================
# VERIFIZIERUNG: ZUFÄLLIGE ZEICHEN UND ANTWORTEN
# =========================================================
CAPTCHA_CHARACTERS = string.ascii_uppercase + string.digits
def create_captcha():
    """Erzeugt einen Code und drei unterschiedliche falsche Antworten."""
    code = "".join(random.choices(CAPTCHA_CHARACTERS, k=4))
    answers = [code]
    while len(answers) < 4:
        chars = list(code)
        position = random.randrange(len(chars))
        alternatives = CAPTCHA_CHARACTERS.replace(chars[position], "")
        chars[position] = random.choice(alternatives)
        decoy = "".join(chars)
        if decoy not in answers:
            answers.append(decoy)
    random.shuffle(answers)
    return code, answers
def captcha_embed(code):
    embed = discord.Embed(
        title="🛡️ Sicherheitsprüfung",
        description=(
            "Klicke auf die Antwort, die **genau** dem folgenden "
            "Code entspricht:\n\n"
            f"# `{code}`\n\n"
            "Du hast vier Antwortmöglichkeiten."
        ),
        color=discord.Color.blurple()
    )
    return embed
class CaptchaAnswerButton(discord.ui.Button):
    def __init__(self, answer):
        super().__init__(
            label=answer,
            style=discord.ButtonStyle.secondary
        )
        self.answer = answer
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not isinstance(view, CaptchaChallengeView):
            await interaction.response.send_message(
                "❌ Diese Prüfung ist nicht mehr gültig. "
                "Klicke erneut auf Verify.",
                ephemeral=True
            )
            return
        if interaction.guild is None or interaction.guild.id != view.guild_id:
            await interaction.response.send_message(
                "❌ Diese Prüfung gehört zu einem anderen Server.",
                ephemeral=True
            )
            return
        if self.answer != view.correct_answer:
            new_view = CaptchaChallengeView(
                view.guild_id,
                view.member_role_id,
                view.verifier_role_id
            )
            await interaction.response.edit_message(
                embed=captcha_embed(new_view.correct_answer),
                view=new_view
            )
            return
        guild = interaction.guild
        member = interaction.user
        member_role = guild.get_role(view.member_role_id)
        verifier_role = guild.get_role(view.verifier_role_id)
        if member_role is None or verifier_role is None:
            await interaction.response.edit_message(
                content=(
                    "❌ Eine der konfigurierten Rollen existiert nicht mehr. "
                    "Bitte lass das Verifizierungspanel erneut erstellen."
                ),
                embed=None,
                view=None
            )
            return
        try:
            await member.add_roles(
                member_role,
                verifier_role,
                reason="Discord-Verifizierung erfolgreich abgeschlossen"
            )
            await interaction.response.edit_message(
                content=(
                    "✅ **Du bist erfolgreich verifiziert!**\n"
                    f"Du hast die Rollen {member_role.mention} und "
                    f"{verifier_role.mention} erhalten."
                ),
                embed=None,
                view=None
            )
        except discord.Forbidden:
            await interaction.response.edit_message(
                content=(
                    "❌ Der Bot darf diese Rollen nicht vergeben. "
                    "Prüfe seine Berechtigung **Rollen verwalten** "
                    "und seine Position in der Rollenliste."
                ),
                embed=None,
                view=None
            )
        except discord.HTTPException:
            await interaction.response.edit_message(
                content=(
                    "❌ Discord konnte die Rollen nicht vergeben. "
                    "Bitte versuche es erneut oder informiere einen Admin."
                ),
                embed=None,
                view=None
            )
class CaptchaChallengeView(discord.ui.View):
    def __init__(self, guild_id, member_role_id, verifier_role_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.member_role_id = member_role_id
        self.verifier_role_id = verifier_role_id
        self.correct_answer, answers = create_captcha()
        for answer in answers:
            self.add_item(CaptchaAnswerButton(answer))
# =========================================================
# VERIFIZIERUNGS-BUTTON
# Funktioniert auch nach einem Bot-Neustart weiter.
# =========================================================
class VerifyButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"verify:(?P<guild_id>[0-9]+):(?P<member_role_id>[0-9]+):(?P<verifier_role_id>[0-9]+)"
):
    def __init__(self, guild_id, member_role_id, verifier_role_id):
        self.guild_id = int(guild_id)
        self.member_role_id = int(member_role_id)
        self.verifier_role_id = int(verifier_role_id)
        button = discord.ui.Button(
            label="Verify",
            emoji="🛡️",
            style=discord.ButtonStyle.success,
            custom_id=(
                f"verify:{self.guild_id}:"
                f"{self.member_role_id}:{self.verifier_role_id}"
            )
        )
        super().__init__(button)
    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(
            int(match["guild_id"]),
            int(match["member_role_id"]),
            int(match["verifier_role_id"])
        )
    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message(
                "❌ Dieses Verifizierungspanel gehört zu einem anderen Server.",
                ephemeral=True
            )
            return
        member_role = interaction.guild.get_role(self.member_role_id)
        verifier_role = interaction.guild.get_role(self.verifier_role_id)
        if member_role is None or verifier_role is None:
            await interaction.response.send_message(
                "❌ Eine der Verifizierungsrollen existiert nicht mehr. "
                "Bitte lass das Panel neu erstellen.",
                ephemeral=True
            )
            return
        member = interaction.user
        if (
            member_role in member.roles
            and verifier_role in member.roles
        ):
            await interaction.response.send_message(
                "✅ Du bist bereits verifiziert!",
                ephemeral=True
            )
            return
        view = CaptchaChallengeView(
            self.guild_id,
            self.member_role_id,
            self.verifier_role_id
        )
        await interaction.response.send_message(
            embed=captcha_embed(view.correct_answer),
            view=view,
            ephemeral=True
        )
# Registriert den dynamischen Button, damit er nach Neustarts erkannt wird.
bot.add_dynamic_items(VerifyButton)
# =========================================================
# /VERIFY ERSTELLEN
# =========================================================
verify_group = app_commands.Group(
    name="verify",
    description="Verifizierungssystem verwalten"
)
@verify_group.command(
    name="erstellen",
    description="Erstellt ein Verifizierungspanel in diesem Kanal"
)
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    member_rolle="Die Rolle, die verifizierte Mitglieder erhalten",
    verifizierer_rolle="Die zusätzliche Rolle nach erfolgreicher Verifizierung"
)
async def verify_erstellen(
    interaction: discord.Interaction,
    member_rolle: discord.Role,
    verifizierer_rolle: discord.Role
):
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "❌ Dieser Befehl funktioniert nur auf einem Server.",
            ephemeral=True
        )
        return
    if member_rolle.id == verifizierer_rolle.id:
        await interaction.response.send_message(
            "❌ Bitte wähle zwei unterschiedliche Rollen aus.",
            ephemeral=True
        )
        return
    if (
        member_rolle.guild.id != guild.id
        or verifizierer_rolle.guild.id != guild.id
    ):
        await interaction.response.send_message(
            "❌ Beide Rollen müssen zu diesem Server gehören.",
            ephemeral=True
        )
        return
    bot_member = guild.me
    if bot_member is None or not bot_member.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "❌ Der Bot benötigt die Berechtigung **Rollen verwalten**.",
            ephemeral=True
        )
        return
    if (
        member_rolle >= bot_member.top_role
        or verifizierer_rolle >= bot_member.top_role
    ):
        await interaction.response.send_message(
            "❌ Beide Zielrollen müssen in der Rollenliste "
            "unterhalb der Bot-Rolle stehen.",
            ephemeral=True
        )
        return
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "❌ Bitte verwende den Befehl in einem normalen Textkanal.",
            ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🛡️ Verify",
        description=(
            "Willkommen auf unserem Server!\n\n"
            "Klicke auf **Verify**, um die Sicherheitsprüfung zu starten. "
            "Wenn du sie erfolgreich abschließt, erhältst du Zugang "
            "zum Server und deine Mitgliedsrollen."
        ),
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Verifizierungssystem")
    view = discord.ui.View(timeout=None)
    view.add_item(
        VerifyButton(
            guild.id,
            member_rolle.id,
            verifizierer_rolle.id
        )
    )
    try:
        await channel.send(embed=embed, view=view)
        await interaction.followup.send(
            f"✅ Das Verifizierungspanel wurde in {channel.mention} erstellt.\n"
            f"Rollen nach erfolgreicher Prüfung: {member_rolle.mention} "
            f"und {verifizierer_rolle.mention}.",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Der Bot darf in diesem Kanal keine Nachrichten senden "
            "oder Embeds veröffentlichen.",
            ephemeral=True
        )
bot.tree.add_command(verify_group)
# =========================================================
# BOT READY
# =========================================================
@bot.event
async def on_ready():
    print(f"Bot ist online: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} Slash Commands synchronisiert.")
    except Exception as error:
        print(f"Fehler beim Synchronisieren: {error}")
# =========================================================
# /EMBED
# =========================================================
@bot.tree.command(
    name="embed",
    description="Erstellt einen Discord Embed"
)
async def embed_command(interaction: discord.Interaction):
    data = EmbedData()
    view = EmbedMenuView(data)
    await interaction.response.send_message(
        content=view.menu_text(),
        view=view,
        ephemeral=True
    )
# =========================================================
# TOKEN
# =========================================================
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN wurde nicht gefunden.")
bot.run(TOKEN)
