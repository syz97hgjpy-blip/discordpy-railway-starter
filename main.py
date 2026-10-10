import os
import asyncio
import random
import time
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands


# =========================================================
# EINSTELLUNGEN – werden in Railway unter Variables gesetzt
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("SECURITY_LOG_CHANNEL_ID", "0"))
VERIFY_ROLE_ID = int(os.getenv("VERIFY_ROLE_ID", "0"))

RAID_JOIN_LIMIT = 8
RAID_TIME_WINDOW = 60


# =========================================================
# BOT UND INTENTS
# =========================================================

intents = discord.Intents.default()
intents.members = True
intents.moderation = True


class SecurityBot(commands.Bot):
    async def setup_hook(self):
        # Slash-Befehle bei Discord registrieren
        await self.tree.sync()
        # Dauerhafte Verify-Buttons nach einem Neustart laden
        self.add_view(VerifyPanelView())


bot = SecurityBot(
    command_prefix="!",
    intents=intents,
)


# =========================================================
# SECURITY-LOG
# =========================================================

async def send_security_log(guild, message):
    if guild is None or LOG_CHANNEL_ID == 0:
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    if not hasattr(channel, "send"):
        return

    try:
        await channel.send(
            message,
            allowed_mentions=discord.AllowedMentions.none(),
        )
    except (discord.Forbidden, discord.HTTPException):
        pass


# =========================================================
# EMBED-SYSTEM
# =========================================================

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):
    embed_title = discord.ui.TextInput(
        label="Titel",
        placeholder="Titel deines Embeds",
        max_length=256,
    )

    embed_description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Text für dein Embed",
        style=discord.TextStyle.paragraph,
        max_length=4000,
    )

    embed_color = discord.ui.TextInput(
        label="Farbe als Hex-Code",
        placeholder="5865F2",
        default="5865F2",
        required=True,
        max_length=7,
    )

    async def on_submit(self, interaction: discord.Interaction):
        color_text = self.embed_color.value.strip().lstrip("#")

        try:
            color_value = int(color_text, 16)
            if len(color_text) not in (3, 6) or not (
                0 <= color_value <= 0xFFFFFF
            ):
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Ungültige Farbe. Verwende zum Beispiel `5865F2` oder `#5865F2`.",
                ephemeral=True,
            )
            return

        if len(color_text) == 3:
            color_text = "".join(char * 2 for char in color_text)
            color_value = int(color_text, 16)

        embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=discord.Color(color_value),
        )
        embed.set_footer(text=f"Erstellt von {interaction.user.display_name}")

        await interaction.response.send_message(
            "Dein Embed wurde erstellt.",
            ephemeral=True,
        )

        try:
            await interaction.channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            await interaction.followup.send(
                "Ich konnte das Embed hier nicht senden. Prüfe meine Kanalrechte.",
                ephemeral=True,
            )


@bot.tree.command(
    name="embed",
    description="Erstellt ein Embed mit Titel, Text und Farbe.",
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_command(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())


@embed_command.error
async def embed_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Du brauchst die Berechtigung „Nachrichten verwalten“."
    else:
        message = "Beim Öffnen des Embed-Menüs ist ein Fehler aufgetreten."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# =========================================================
# VERIFIZIERUNG MIT CAPTCHA
# =========================================================

class CaptchaModal(discord.ui.Modal, title="Verifizierung"):
    def __init__(self, first_number: int, second_number: int):
        super().__init__()
        self.correct_answer = first_number + second_number

        self.answer = discord.ui.TextInput(
            label=f"Was ist {first_number} + {second_number}?",
            placeholder="Gib die Zahl ein",
            max_length=5,
        )
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.answer.value.strip().isdigit():
            await interaction.response.send_message(
                "Das ist keine gültige Zahl. Versuche es erneut.",
                ephemeral=True,
            )
            return

        if int(self.answer.value.strip()) != self.correct_answer:
            await interaction.response.send_message(
                "Leider falsch. Drücke den Verifizieren-Button und versuche es erneut.",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            await interaction.response.send_message(
                "Die Verifizierung funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        if VERIFY_ROLE_ID == 0:
            await interaction.response.send_message(
                "Die Verify-Rolle ist noch nicht eingerichtet. Bitte informiere einen Admin.",
                ephemeral=True,
            )
            return

        role = interaction.guild.get_role(VERIFY_ROLE_ID)

        if role is None:
            await interaction.response.send_message(
                "Die eingestellte Verify-Rolle wurde nicht gefunden. Bitte informiere einen Admin.",
                ephemeral=True,
            )
            return

        member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "Dein Mitgliedsprofil wurde nicht gefunden. Bitte versuche es erneut.",
                ephemeral=True,
            )
            return

        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "Meine Bot-Rolle muss in den Servereinstellungen über der Verify-Rolle stehen.",
                ephemeral=True,
            )
            return

        try:
            await member.add_roles(role, reason="CAPTCHA-Verifizierung erfolgreich")
        except discord.Forbidden:
            await interaction.response.send_message(
                "Ich darf diese Rolle nicht vergeben. Prüfe meine Rollenrechte.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord hat die Rolle gerade nicht vergeben. Versuche es erneut.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Du bist erfolgreich verifiziert!",
            ephemeral=True,
        )


class VerifyPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Jetzt verifizieren",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="security_bot:verify",
    )
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Das funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        if VERIFY_ROLE_ID == 0:
            await interaction.response.send_message(
                "Die Verify-Rolle ist noch nicht eingerichtet. Bitte informiere einen Admin.",
                ephemeral=True,
            )
            return

        first = random.randint(1, 9)
        second = random.randint(1, 9)

        await interaction.response.send_modal(CaptchaModal(first, second))


@bot.tree.command(
    name="verify_erstellen",
    description="Erstellt das Verifizierungs-Panel in diesem Kanal.",
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_guild=True)
async def verify_erstellen(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Server-Verifizierung",
        description=(
            "Willkommen auf dem Server!\n\n"
            "Klicke auf **Jetzt verifizieren** und löse die kurze Rechenaufgabe, "
            "um die Verify-Rolle zu erhalten."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Security System")

    await interaction.response.send_message(
        "Das Verifizierungs-Panel wurde erstellt.",
        ephemeral=True,
    )
    await interaction.channel.send(embed=embed, view=VerifyPanelView())


@verify_erstellen.error
async def verify_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Du brauchst die Berechtigung „Server verwalten“."
    else:
        message = "Das Verify-Panel konnte nicht erstellt werden."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# =========================================================
# ANTI-RAID: VIELE BEITRITTE IN KURZER ZEIT
# =========================================================

recent_joins = {}


@bot.event
async def on_member_join(member: discord.Member):
    now = time.monotonic()
    joins = recent_joins.setdefault(member.guild.id, deque())

    joins.append(now)

    while joins and now - joins[0] > RAID_TIME_WINDOW:
        joins.popleft()

    if len(joins) >= RAID_JOIN_LIMIT:
        await send_security_log(
            member.guild,
            "⚠️ **Möglicher Join-Raid erkannt**\n"
            f"Auf dem Server sind innerhalb von {RAID_TIME_WINDOW} Sekunden "
            f"{len(joins)} Mitglieder beigetreten.\n"
            "Bitte prüfe die Beitritte und aktiviere bei Bedarf zusätzliche Schutzmaßnahmen.",
        )


# =========================================================
# ANTI-NUKE: AUDIT-LOG-ÜBERWACHUNG
# =========================================================

async def log_latest_audit_action(
    guild: discord.Guild,
    action: discord.AuditLogAction,
    title: str,
):
    await asyncio.sleep(1.5)

    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            # Nur relativ neue Aktionen berücksichtigen
            age = (discord.utils.utcnow() - entry.created_at).total_seconds()

            if age > 20:
                continue

            target = entry.target
            target_name = getattr(target, "name", str(target))
            actor = entry.user
            actor_name = str(actor) if actor else "Unbekannt"

            await send_security_log(
                guild,
                f"🚨 **{title}**\n"
                f"**Ausgeführt von:** {actor_name}\n"
                f"**Betroffen:** {target_name}\n"
                f"**Audit-Log-ID:** `{entry.id}`\n"
                "Hinweis: Dies ist eine Erkennung und Meldung, keine automatische Rücknahme.",
            )
            return

    except (discord.Forbidden, discord.HTTPException):
        await send_security_log(
            guild,
            f"⚠️ **{title}** erkannt, aber ich konnte das Audit-Log nicht lesen. "
            "Prüfe meine Berechtigung „Audit-Log einsehen“.",
        )


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    await log_latest_audit_action(
        channel.guild,
        discord.AuditLogAction.channel_delete,
        "Kanal gelöscht – mögliche Nuke-Aktion",
    )


@bot.event
async def on_guild_role_delete(role: discord.Role):
    await log_latest_audit_action(
        role.guild,
        discord.AuditLogAction.role_delete,
        "Rolle gelöscht – mögliche Nuke-Aktion",
    )


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    await log_latest_audit_action(
        guild,
        discord.AuditLogAction.ban,
        f"Ban erkannt für {user}",
    )


@bot.event
async def on_webhooks_update(channel: discord.abc.GuildChannel):
    await log_latest_audit_action(
        channel.guild,
        discord.AuditLogAction.webhook_create,
        "Webhook erstellt oder geändert – bitte Audit-Log prüfen",
    )


# =========================================================
# START
# =========================================================

@bot.event
async def on_ready():
    print(f"Bot online: {bot.user} (ID: {bot.user.id})")
    print("Security-Bot wurde gestartet.")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN fehlt. Bitte setze die Variable in Railway."
    )

bot.run(TOKEN)
