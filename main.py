
import os
import random
import string

import discord
from discord import app_commands
from discord.ext import commands


# ==========================================
# BOT-EINSTELLUNGEN
# ==========================================

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ==========================================
# EMBED-SYSTEM
# ==========================================

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):
    embed_title = discord.ui.TextInput(
        label="Titel",
        placeholder="Titel deines Embeds",
        max_length=256
    )

    embed_description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Text für dein Embed",
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    embed_color = discord.ui.TextInput(
        label="Farbe als HEX-Code",
        placeholder="5865F2",
        required=False,
        max_length=6
    )

    def __init__(self, channel: discord.TextChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        color_text = self.embed_color.value.strip().replace("#", "")

        try:
            color_value = int(color_text, 16) if color_text else 0x5865F2
            if not 0 <= color_value <= 0xFFFFFF:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Bitte gib eine gültige HEX-Farbe ein, z. B. 5865F2.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=discord.Color(color_value)
        )

        try:
            await self.channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich kann in diesem Kanal keine Nachrichten senden.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"Embed wurde in {self.channel.mention} gesendet.",
            ephemeral=True
        )


@bot.tree.command(
    name="embed",
    description="Erstelle ein eigenes Embed."
)
@app_commands.describe(
    kanal="Kanal, in dem das Embed veröffentlicht werden soll."
)
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_command(
    interaction: discord.Interaction,
    kanal: discord.TextChannel
):
    await interaction.response.send_modal(EmbedModal(kanal))


# ==========================================
# CAPTCHA
# ==========================================

def create_captcha_code():
    characters = string.ascii_uppercase + string.digits
    return "".join(random.choices(characters, k=4))


def make_captcha_embed(code: str):
    return discord.Embed(
        title="🔐 Verifizierung",
        description=(
            "Wähle die richtige Antwort, um deine Verifizierung "
            "abzuschließen.\n\n"
            f"**Gesuchter Code:**\n# `{code}`"
        ),
        color=discord.Color.blurple()
    )


class CaptchaAnswerButton(discord.ui.Button):
    def __init__(
        self,
        answer: str,
        correct_answer: str,
        role_ids: list[int],
        user_id: int
    ):
        super().__init__(
            label=answer,
            style=discord.ButtonStyle.primary
        )
        self.answer = answer
        self.correct_answer = correct_answer
        self.role_ids = role_ids
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Diese CAPTCHA gehört zu einer anderen Person.",
                ephemeral=True
            )
            return

        if self.answer != self.correct_answer:
            new_view = CaptchaView(self.role_ids, self.user_id)
            await interaction.response.edit_message(
                embed=make_captcha_embed(new_view.correct_answer),
                view=new_view
            )
            return

        if interaction.guild is None:
            await interaction.response.edit_message(
                content="Diese Verifizierung funktioniert nur auf einem Server.",
                embed=None,
                view=None
            )
            return

        member = interaction.user

        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.edit_message(
                content="Dein Servermitglied konnte nicht gefunden werden.",
                embed=None,
                view=None
            )
            return

        guild = interaction.guild
        bot_member = guild.get_member(bot.user.id) if bot.user else None

        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            await interaction.response.edit_message(
                content="Der Bot benötigt die Berechtigung „Rollen verwalten“.",
                embed=None,
                view=None
            )
            return

        roles = []

        for role_id in self.role_ids:
            role = guild.get_role(role_id)

            if role is None:
                await interaction.response.edit_message(
                    content=(
                        "Eine ausgewählte Rolle wurde gelöscht. "
                        "Bitte kontaktiere die Serveradministration."
                    ),
                    embed=None,
                    view=None
                )
                return

            if (
                role.is_default()
                or role.managed
                or role >= bot_member.top_role
            ):
                await interaction.response.edit_message(
                    content=(
                        f"Die Rolle **{role.name}** kann vom Bot nicht "
                        "vergeben werden. Prüfe die Rollen-Hierarchie."
                    ),
                    embed=None,
                    view=None
                )
                return

            roles.append(role)

        roles_to_add = [
            role for role in roles
            if role not in member.roles
        ]

        if not roles_to_add:
            await interaction.response.edit_message(
                content="✅ Du hast bereits alle ausgewählten Rollen.",
                embed=None,
                view=None
            )
            return

        try:
            await member.add_roles(
                *roles_to_add,
                reason="Verifizierung erfolgreich"
            )
        except discord.Forbidden:
            await interaction.response.edit_message(
                content=(
                    "Ich darf diese Rollen nicht vergeben. "
                    "Prüfe die Bot-Berechtigungen und Rollen-Hierarchie."
                ),
                embed=None,
                view=None
            )
            return
        except discord.HTTPException:
            await interaction.response.edit_message(
                content="Beim Vergeben der Rollen ist ein Fehler aufgetreten.",
                embed=None,
                view=None
            )
            return

        await interaction.response.edit_message(
            content="✅ Verifizierung erfolgreich! Deine Rollen wurden vergeben.",
            embed=None,
            view=None
        )


class CaptchaView(discord.ui.View):
    def __init__(self, role_ids: list[int], user_id: int):
        super().__init__(timeout=180)

        self.role_ids = role_ids
        self.user_id = user_id
        self.correct_answer = create_captcha_code()

        answers = [self.correct_answer]

        while len(answers) < 4:
            candidate = create_captcha_code()
            if candidate not in answers:
                answers.append(candidate)

        random.shuffle(answers)

        for answer in answers:
            self.add_item(
                CaptchaAnswerButton(
                    answer=answer,
                    correct_answer=self.correct_answer,
                    role_ids=self.role_ids,
                    user_id=self.user_id
                )
            )


# ==========================================
# VERIFY-NACHRICHT
# ==========================================

def encode_role_ids(role_ids: list[int]) -> str:
    return ",".join(str(role_id) for role_id in role_ids)


def decode_role_ids(value: str) -> list[int]:
    try:
        return [
            int(part)
            for part in value.split(",")
            if part.strip()
        ]
    except ValueError:
        return []


class VerifyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verify",
        emoji="🛡️",
        style=discord.ButtonStyle.success,
        custom_id="verify:begin"
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.guild is None or interaction.message is None:
            await interaction.response.send_message(
                "Bitte verwende die Schaltfläche auf einem Server.",
                ephemeral=True
            )
            return

        if not interaction.message.embeds:
            await interaction.response.send_message(
                "Die Verify-Konfiguration wurde nicht gefunden.",
                ephemeral=True
            )
            return

        footer = interaction.message.embeds[0].footer.text or ""

        if not footer.startswith("verify-roles:"):
            await interaction.response.send_message(
                "Die Rollen-Konfiguration fehlt. Bitte informiere die Administration.",
                ephemeral=True
            )
            return

        role_ids = decode_role_ids(footer[len("verify-roles:"):])

        if not role_ids:
            await interaction.response.send_message(
                "Es wurden keine gültigen Rollen gefunden.",
                ephemeral=True
            )
            return

        view = CaptchaView(role_ids, interaction.user.id)

        await interaction.response.send_message(
            embed=make_captcha_embed(view.correct_answer),
            view=view,
            ephemeral=True
        )


# ==========================================
# VERIFY-EINRICHTUNG MIT MEHRFACHAUSWAHL
# ==========================================

class VerifySetupView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=300)
        self.guild = guild
        self.selected_roles: list[discord.Role] = []
        self.create_panel.disabled = True

    def setup_text(self):
        if self.selected_roles:
            role_text = "\n".join(
                f"• {role.mention}"
                for role in self.selected_roles
            )
        else:
            role_text = "Noch keine Rollen ausgewählt."

        return (
            "🛡️ **Verify-System einrichten**\n\n"
            "Wähle im einzigen Rollenfeld eine oder mehrere Rollen aus. "
            "Nach erfolgreicher Verifizierung werden alle ausgewählten "
            "Rollen vergeben.\n\n"
            f"**Ausgewählte Rollen:**\n{role_text}\n\n"
            "Klicke anschließend auf **Verify-Nachricht erstellen**."
        )

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Rollen nach der Verifizierung auswählen",
        min_values=1,
        max_values=25,
        row=0
    )
    async def role_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.RoleSelect
    ):
        self.selected_roles = list(select.values)
        self.create_panel.disabled = not bool(self.selected_roles)

        await interaction.response.edit_message(
            content=self.setup_text(),
            view=self
        )

    @discord.ui.button(
        label="Verify-Nachricht erstellen",
        emoji="🛡️",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def create_panel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if not self.selected_roles:
            await interaction.response.send_message(
                "Bitte wähle mindestens eine Rolle aus.",
                ephemeral=True
            )
            return

        guild = interaction.guild

        if guild is None or not isinstance(
            interaction.channel, discord.TextChannel
        ):
            await interaction.response.send_message(
                "Verwende diesen Befehl in einem normalen Textkanal.",
                ephemeral=True
            )
            return

        bot_member = guild.get_member(bot.user.id) if bot.user else None

        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "Der Bot benötigt die Berechtigung „Rollen verwalten“.",
                ephemeral=True
            )
            return

        for role in self.selected_roles:
            if (
                role.is_default()
                or role.managed
                or role >= bot_member.top_role
            ):
                await interaction.response.send_message(
                    f"Die Rolle **{role.name}** kann vom Bot nicht vergeben "
                    "werden. Verschiebe die Bot-Rolle über diese Rolle.",
                    ephemeral=True
                )
                return

        embed = discord.Embed(
            title="🛡️ Verify",
            description=(
                "Willkommen auf dem Server!\n\n"
                "Klicke unten auf **Verify**, löse die CAPTCHA-Aufgabe "
                "und erhalte anschließend deine ausgewählten Rollen."
            ),
            color=discord.Color.blurple()
        )

        embed.set_footer(
            text="verify-roles:" + encode_role_ids(
                [role.id for role in self.selected_roles]
            )
        )

        try:
            await interaction.channel.send(
                embed=embed,
                view=VerifyPanelView()
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich darf in diesem Kanal keine Nachrichten senden.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="✅ Die Verify-Nachricht wurde erstellt.",
            view=None
        )


verify_group = app_commands.Group(
    name="verify",
    description="Verifizierungssystem verwalten"
)


@verify_group.command(
    name="erstellen",
    description="Erstellt eine Verify-Nachricht."
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_erstellen(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Dieser Befehl funktioniert nur auf einem Server.",
            ephemeral=True
        )
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message(
            "Bitte verwende den Befehl in einem normalen Textkanal.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        content="Wähle eine oder mehrere Rollen für die Verifizierung aus.",
        view=VerifySetupView(interaction.guild),
        ephemeral=True
    )


bot.tree.add_command(verify_group)


# ==========================================
# FEHLERMELDUNGEN
# ==========================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Du benötigst die erforderlichen Berechtigungen für diesen Befehl."
    else:
        message = "Beim Ausführen des Befehls ist ein Fehler aufgetreten."
        print(f"Slash-Command-Fehler: {error}")

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# ==========================================
# START UND REGISTRIERUNG
# ==========================================

@bot.event
async def setup_hook():
    # Persistente Verify-Schaltflächen nach Neustarts registrieren.
    bot.add_view(VerifyPanelView())

    # Slash-Befehle bei Discord registrieren.
    await bot.tree.sync()


@bot.event
async def on_ready():
    print(f"Bot online: {bot.user} (ID: {bot.user.id})")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN fehlt. Hinterlege ihn in den Railway-Variablen."
    )

bot.run(TOKEN)
