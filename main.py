
import os
import io
import json
import random
import string
import time
import logging
from collections import deque
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============================================================
# KONFIGURATION
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
SECURITY_LOG_CHANNEL_ID = int(os.getenv("SECURITY_LOG_CHANNEL_ID", "0"))
CONFIG_FILE = os.getenv("VERIFICATION_CONFIG_FILE", "verification_config.json")

JOIN_WINDOW_SECONDS = 20
JOIN_SPIKE_LIMIT = 8
JOIN_TIMES = deque()

BLOCK_NEW_BOTS = os.getenv("BLOCK_NEW_BOTS", "false").lower() == "true"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("server-security")

if not TOKEN:
    raise RuntimeError("Die Railway-Variable DISCORD_TOKEN fehlt!")

# ============================================================
# INTENTS UND BOT
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True
intents.webhooks = True
intents.message_content = True


class SecurityBot(commands.Bot):
    async def setup_hook(self):
        # Persistent View: Verifizierungsbutton bleibt nach Neustarts aktiv.
        self.add_view(VerifyPanel())

        synced = await self.tree.sync()
        log.info("%s Slash-Befehle synchronisiert.", len(synced))


bot = SecurityBot(command_prefix="!", intents=intents)

# ============================================================
# PERSISTENTE KONFIGURATION
# ============================================================

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


config = load_config()


def get_guild_config(guild_id):
    return config.get(str(guild_id), {})


def set_verification_roles(guild_id, role_ids):
    key = str(guild_id)
    config.setdefault(key, {})
    config[key]["verification_role_ids"] = role_ids
    save_config(config)


def get_configured_roles(guild):
    """Gibt die eingerichteten Rollen zurück, die noch existieren."""
    role_ids = get_guild_config(guild.id).get("verification_role_ids", [])
    roles = []

    for role_id in role_ids:
        try:
            role = guild.get_role(int(role_id))
        except (TypeError, ValueError):
            continue

        if role is not None:
            roles.append(role)

    return roles


def is_already_verified(member):
    """Als verifiziert gilt ein Mitglied, wenn es alle eingerichteten Rollen hat."""
    roles = get_configured_roles(member.guild)
    return bool(roles) and all(role in member.roles for role in roles)


# ============================================================
# SICHERHEITSLOGS
# ============================================================

async def security_log(title, description, color=discord.Color.orange()):
    if not SECURITY_LOG_CHANNEL_ID:
        log.warning("%s — %s", title, description)
        return

    channel = bot.get_channel(SECURITY_LOG_CHANNEL_ID)

    if channel is None:
        try:
            channel = await bot.fetch_channel(SECURITY_LOG_CHANNEL_ID)
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            log.warning("Sicherheits-Log-Kanal nicht erreichbar.")
            return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )

    try:
        await channel.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        log.exception("Sicherheitsmeldung konnte nicht gesendet werden.")


def is_manageable_role(guild, role):
    me = guild.me
    if me is None:
        return False

    return (
        role != guild.default_role
        and not role.managed
        and role < me.top_role
    )


# ============================================================
# CAPTCHA-BILD — wird automatisch erstellt
# ============================================================

def generate_captcha():
    alphabet = string.ascii_uppercase + string.digits
    answer = "".join(random.choices(alphabet, k=6))

    width, height = 480, 170
    image = Image.new("RGB", (width, height), (12, 12, 12))
    draw = ImageDraw.Draw(image)

    for _ in range(12):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        shade = random.randint(35, 65)
        draw.line((x1, y1, x2, y2), fill=(shade, shade, shade), width=1)

    for _ in range(150):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        shade = random.randint(45, 85)
        draw.point((x, y), fill=(shade, shade, shade))

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
    except OSError:
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                52,
            )
        except OSError:
            font = ImageFont.load_default()

    char_widths = [
        draw.textbbox((0, 0), char, font=font)[2]
        for char in answer
    ]
    total_width = sum(char_widths) + 12 * (len(answer) - 1)
    x = max(10, (width - total_width) // 2)

    for char, char_width in zip(answer, char_widths):
        y = random.randint(48, 70)
        draw.text((x, y), char, font=font, fill=(245, 245, 245))
        x += char_width + 12

    image = image.filter(ImageFilter.SMOOTH)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return answer, buffer


# ============================================================
# CAPTCHA-AUSWAHL — privat für den jeweiligen Nutzer
# ============================================================

class CaptchaAnswerSelect(discord.ui.Select):
    def __init__(self, answer, options):
        self.correct_answer = answer

        super().__init__(
            placeholder="Wähle den Code aus dem Bild",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=option, value=option)
                for option in options
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Diese Verifizierung funktioniert nur auf dem Server.",
                ephemeral=True,
            )
            return

        if self.values[0] != self.correct_answer:
            answer, buffer = generate_captcha()
            options = [answer]

            while len(options) < 4:
                candidate = "".join(
                    random.choices(
                        string.ascii_uppercase + string.digits,
                        k=6,
                    )
                )
                if candidate not in options:
                    options.append(candidate)

            random.shuffle(options)

            embed = discord.Embed(
                title="Verifizierung",
                description=(
                    "Der Code war leider falsch. "
                    "Versuche es mit dem neuen Bild erneut."
                ),
                color=discord.Color.dark_grey(),
            )
            embed.set_image(url="attachment://captcha.png")

            await interaction.response.send_message(
                embed=embed,
                file=discord.File(buffer, filename="captcha.png"),
                view=CaptchaView(answer, interaction.user.id),
                ephemeral=True,
            )
            return

        guild = interaction.guild
        member = interaction.user

        if not isinstance(member, discord.Member):
            member = guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "Dein Mitgliedsstatus konnte nicht geladen werden. "
                "Bitte versuche es erneut.",
                ephemeral=True,
            )
            return

        # Prüfen, ob die Person inzwischen schon verifiziert wurde.
        if is_already_verified(member):
            await interaction.response.send_message(
                "✅ Du bist bereits verifiziert!",
                ephemeral=True,
            )
            return

        role_ids = get_guild_config(guild.id).get(
            "verification_role_ids", []
        )

        if not role_ids:
            await interaction.response.send_message(
                "Die Verifizierung wurde noch nicht vollständig eingerichtet. "
                "Bitte informiere das Serverteam.",
                ephemeral=True,
            )
            return

        roles_to_add = []
        for role_id in role_ids:
            try:
                role = guild.get_role(int(role_id))
            except (TypeError, ValueError):
                continue

            if role and is_manageable_role(guild, role):
                roles_to_add.append(role)

        if not roles_to_add:
            await interaction.response.send_message(
                "Der Bot kann die eingerichteten Rollen nicht vergeben. "
                "Bitte prüfe die Rollenposition des Bots.",
                ephemeral=True,
            )
            return

        try:
            await member.add_roles(
                *roles_to_add,
                reason="Erfolgreiche CAPTCHA-Verifizierung",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Der Bot darf die Rollen nicht vergeben. "
                "Prüfe seine Berechtigungen und Rollenposition.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Die Rollen konnten gerade nicht vergeben werden. "
                "Bitte versuche es später erneut.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "✅ Verifizierung erfolgreich! Du hast jetzt Zugriff auf "
            "die freigeschalteten Bereiche des Servers.",
            ephemeral=True,
        )

        await security_log(
            "Verifizierung erfolgreich",
            f"{member.mention} (`{member.id}`) hat das CAPTCHA bestanden.",
            discord.Color.green(),
        )


class CaptchaView(discord.ui.View):
    def __init__(self, answer, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id

        options = [answer]
        while len(options) < 4:
            candidate = "".join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=6,
                )
            )
            if candidate not in options:
                options.append(candidate)

        random.shuffle(options)
        self.add_item(CaptchaAnswerSelect(answer, options))

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Dieses CAPTCHA gehört zu einer anderen Person.",
                ephemeral=True,
            )
            return False
        return True


# ============================================================
# VERIFIZIERUNGS-PANEL
# ============================================================

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Verifizieren",
            style=discord.ButtonStyle.success,
            custom_id="verification:start",
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Bitte nutze diese Schaltfläche auf dem Server.",
                ephemeral=True,
            )
            return

        member = interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)

        if member is None:
            await interaction.response.send_message(
                "Dein Mitgliedsstatus konnte nicht geladen werden. "
                "Bitte versuche es erneut.",
                ephemeral=True,
            )
            return

        # NEU: Bereits verifizierte Mitglieder brauchen kein CAPTCHA mehr.
        if is_already_verified(member):
            await interaction.response.send_message(
                "✅ Du bist bereits verifiziert!",
                ephemeral=True,
            )
            return

        answer, buffer = generate_captcha()

        embed = discord.Embed(
            title="CAPTCHA-Verifizierung",
            description="Lies den Code im Bild und wähle die passende Antwort.",
            color=discord.Color.dark_grey(),
        )
        embed.set_image(url="attachment://captcha.png")

        await interaction.response.send_message(
            embed=embed,
            file=discord.File(buffer, filename="captcha.png"),
            view=CaptchaView(answer, interaction.user.id),
            ephemeral=True,
        )


class VerifyPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


# ============================================================
# ADMIN-EINRICHTUNG — ROLLEN AUSWÄHLEN
# ============================================================

class VerificationRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="Rollen auswählen, die nach der Verifizierung vergeben werden",
            min_values=1,
            max_values=25,
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Dafür brauchst du die Berechtigung „Server verwalten“.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Diese Einrichtung funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        invalid = [
            role for role in self.values
            if not is_manageable_role(guild, role)
        ]

        if invalid:
            names = ", ".join(role.name for role in invalid)
            await interaction.response.send_message(
                "Diese Rollen kann der Bot nicht vergeben: "
                f"{names}. Wähle nur Rollen unterhalb der höchsten Bot-Rolle "
                "und keine verwalteten Rollen oder @everyone.",
                ephemeral=True,
            )
            return

        self.view.selected_role_ids = [role.id for role in self.values]

        role_names = ", ".join(role.name for role in self.values)
        await interaction.response.edit_message(
            content=(
                "**Verifizierungsrollen ausgewählt:**\n"
                f"{role_names}\n\n"
                "Klicke auf „Panel veröffentlichen“, um die Verifizierung "
                "im aktuellen Kanal zu veröffentlichen."
            ),
            view=self.view,
        )


class PublishVerificationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Panel veröffentlichen",
            style=discord.ButtonStyle.primary,
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "Dafür brauchst du die Berechtigung „Server verwalten“.",
                ephemeral=True,
            )
            return

        role_ids = getattr(self.view, "selected_role_ids", [])
        if not role_ids:
            await interaction.response.send_message(
                "Wähle zuerst die Verifizierungsrollen aus.",
                ephemeral=True,
            )
            return

        guild = interaction.guild
        channel = interaction.channel

        if guild is None or channel is None:
            await interaction.response.send_message(
                "Der Server oder Kanal wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        for role_id in role_ids:
            role = guild.get_role(role_id)
            if role is None or not is_manageable_role(guild, role):
                await interaction.response.send_message(
                    "Mindestens eine ausgewählte Rolle ist nicht mehr "
                    "vergebbar. Bitte richte die Rollen erneut ein.",
                    ephemeral=True,
                )
                return

        set_verification_roles(guild.id, role_ids)

        embed = discord.Embed(
            title="Verifizierung",
            description=(
                "Willkommen auf dem Server!\n\n"
                "Klicke auf **Verifizieren** und löse das CAPTCHA, "
                "um auf weitere Inhalte des Servers zuzugreifen."
            ),
            color=discord.Color.dark_grey(),
        )

        try:
            await channel.send(embed=embed, view=VerifyPanel())
        except discord.Forbidden:
            await interaction.response.send_message(
                "Der Bot darf in diesem Kanal keine Nachrichten senden. "
                "Prüfe seine Kanalberechtigungen.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Das Panel konnte nicht veröffentlicht werden.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Das Verifizierungspanel wurde veröffentlicht.",
            ephemeral=True,
        )

        await security_log(
            "Verifizierung eingerichtet",
            f"{interaction.user.mention} hat das Panel in "
            f"{channel.mention} veröffentlicht.",
            discord.Color.green(),
        )


class VerificationSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_role_ids = []
        self.add_item(VerificationRoleSelect())
        self.add_item(PublishVerificationButton())


@bot.tree.command(
    name="verification_system",
    description="Richte das CAPTCHA-Verifizierungssystem ein",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def verification_system(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Dieser Befehl funktioniert nur auf einem Server.",
            ephemeral=True,
        )
        return

    embed = discord.Embed(
        title="Verifizierung einrichten",
        description=(
            "Wähle die Rollen aus, die Mitglieder nach erfolgreicher "
            "Verifizierung erhalten sollen. Der Bot akzeptiert nur Rollen, "
            "die er laut seiner Rollenposition verwalten kann.\n\n"
            "Danach klickst du auf „Panel veröffentlichen“."
        ),
        color=discord.Color.dark_grey(),
    )

    await interaction.response.send_message(
        embed=embed,
        view=VerificationSetupView(),
        ephemeral=True,
    )


# ============================================================
# EMBED-SYSTEM — /embed
# ============================================================

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):
    embed_title = discord.ui.TextInput(
        label="Titel",
        placeholder="Titel deiner Nachricht",
        max_length=256,
    )
    embed_description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Text deiner Nachricht",
        style=discord.TextStyle.paragraph,
        max_length=4000,
    )
    embed_color = discord.ui.TextInput(
        label="Farbe als HEX (optional)",
        placeholder="#5865F2",
        required=False,
        max_length=7,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "Dieser Befehl funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        raw_color = self.embed_color.value.strip().lstrip("#")

        try:
            if raw_color and len(raw_color) != 6:
                raise ValueError("Ungültige HEX-Länge")

            color = (
                discord.Color(int(raw_color, 16))
                if raw_color
                else discord.Color.blurple()
            )
        except ValueError:
            await interaction.response.send_message(
                "Ungültige Farbe. Nutze zum Beispiel `#5865F2`.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=color,
        )

        try:
            await interaction.channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Der Bot darf in diesem Kanal keine Nachrichten senden.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Das Embed konnte nicht gesendet werden.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Embed erfolgreich gesendet.",
            ephemeral=True,
        )


@bot.tree.command(name="embed", description="Erstelle ein eigenes Embed")
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_command(interaction: discord.Interaction):
    await interaction.response.send_modal(EmbedModal())


# ============================================================
# ANTI-BOT / JOIN-SPIKE-SCHUTZ
# ============================================================

@bot.event
async def on_member_join(member: discord.Member):
    now = time.monotonic()
    JOIN_TIMES.append(now)

    while JOIN_TIMES and now - JOIN_TIMES[0] > JOIN_WINDOW_SECONDS:
        JOIN_TIMES.popleft()

    if len(JOIN_TIMES) >= JOIN_SPIKE_LIMIT:
        await security_log(
            "Möglicher Join-Raid erkannt",
            f"{len(JOIN_TIMES)} Mitglieder sind innerhalb von "
            f"{JOIN_WINDOW_SECONDS} Sekunden beigetreten.",
            discord.Color.red(),
        )
        JOIN_TIMES.clear()

    if member.bot:
        await security_log(
            "Neuer Bot-Account beigetreten",
            f"{member.mention} (`{member.id}`) ist dem Server beigetreten.",
            discord.Color.orange(),
        )

        if BLOCK_NEW_BOTS:
            try:
                await member.kick(
                    reason="Automatischer Schutz: neue Bots blockiert"
                )
                await security_log(
                    "Bot-Account entfernt",
                    f"Der neue Bot-Account `{member.id}` wurde entfernt.",
                    discord.Color.red(),
                )
            except (discord.Forbidden, discord.HTTPException):
                await security_log(
                    "Bot konnte nicht entfernt werden",
                    f"Der Bot-Account `{member.id}` konnte nicht automatisch "
                    "entfernt werden. Prüfe die Berechtigungen.",
                    discord.Color.red(),
                )


# ============================================================
# ANTI-NUKE — VERDÄCHTIGE AKTIONEN PROTOKOLLIEREN
# ============================================================

async def audit_actor(guild, action):
    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            if (
                datetime.now(timezone.utc) - entry.created_at
            ).total_seconds() < 10:
                return entry.user
    except (discord.Forbidden, discord.HTTPException):
        return None

    return None


@bot.event
async def on_guild_channel_delete(channel):
    actor = await audit_actor(
        channel.guild,
        discord.AuditLogAction.channel_delete,
    )
    await security_log(
        "Anti-Nuke: Kanal gelöscht",
        f"**Kanal:** {channel.name}\n"
        f"**Ausgeführt von:** {actor.mention if actor else 'Unbekannt'}",
        discord.Color.red(),
    )


@bot.event
async def on_guild_role_delete(role):
    actor = await audit_actor(
        role.guild,
        discord.AuditLogAction.role_delete,
    )
    await security_log(
        "Anti-Nuke: Rolle gelöscht",
        f"**Rolle:** {role.name}\n"
        f"**Ausgeführt von:** {actor.mention if actor else 'Unbekannt'}",
        discord.Color.red(),
    )


@bot.event
async def on_member_ban(guild, user):
    actor = await audit_actor(guild, discord.AuditLogAction.ban)
    await security_log(
        "Moderationsereignis: Ban",
        f"**Nutzer:** {user} (`{user.id}`)\n"
        f"**Ausgeführt von:** {actor.mention if actor else 'Unbekannt'}",
        discord.Color.red(),
    )


@bot.event
async def on_webhooks_update(channel):
    actor = await audit_actor(
        channel.guild,
        discord.AuditLogAction.webhook_create,
    )

    if actor is None:
        actor = await audit_actor(
            channel.guild,
            discord.AuditLogAction.webhook_delete,
        )

    await security_log(
        "Sicherheitsereignis: Webhooks geändert",
        f"**Kanal:** {channel.mention}\n"
        f"**Möglicher Auslöser:** "
        f"{actor.mention if actor else 'Unbekannt'}",
        discord.Color.orange(),
    )


# ============================================================
# FEHLERBEHANDLUNG
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Du hast nicht die nötigen Berechtigungen für diesen Befehl."
    else:
        log.error(
            "Fehler bei einem Slash-Befehl",
            exc_info=(type(error), error, error.__traceback__),
        )
        message = "Beim Ausführen des Befehls ist ein Fehler aufgetreten."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(
                message,
                ephemeral=True,
            )
    except discord.HTTPException:
        pass


# ============================================================
# START
# ============================================================

@bot.event
async def on_ready():
    log.info(
        "Eingeloggt als %s (%s)",
        bot.user,
        bot.user.id if bot.user else "?",
    )
    log.info("Bot ist bereit.")


bot.run(TOKEN)
