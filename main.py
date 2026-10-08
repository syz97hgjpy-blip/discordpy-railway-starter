import os
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# PERSÖNLICHE SPRACHANZEIGE
# =========================================================

class LanguageView(discord.ui.View):

    def __init__(self, german_embed, english_embed):
        super().__init__(timeout=None)

        self.german_embed = german_embed
        self.english_embed = english_embed

    @discord.ui.button(
        label="Deutsch",
        emoji="🇩🇪",
        style=discord.ButtonStyle.success,
        custom_id="language_german"
    )
    async def german(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # Persönliche deutsche Version.
        # Nur die Person, die geklickt hat, sieht sie.
        await interaction.response.send_message(
            embed=self.german_embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="English",
        emoji="🇬🇧",
        style=discord.ButtonStyle.success,
        custom_id="language_english"
    )
    async def english(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # Persönliche englische Version.
        # Nur die Person, die geklickt hat, sieht sie.
        await interaction.response.send_message(
            embed=self.english_embed,
            ephemeral=True
        )


# =========================================================
# EMBED ERSTELLEN
# =========================================================

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):

    # DEUTSCHER TITEL
    embed_title = discord.ui.TextInput(
        label="Deutscher Titel",
        placeholder="z. B. SERVER REGELN",
        required=True,
        max_length=256
    )

    # DEUTSCHE NACHRICHT
    embed_description = discord.ui.TextInput(
        label="Deutsche Nachricht",
        placeholder="Dein deutsches Regelwerk...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    # ENGLISCHER TITEL
    english_title = discord.ui.TextInput(
        label="Englischer Titel",
        placeholder="z. B. SERVER RULES",
        required=True,
        max_length=256
    )

    # ENGLISCHE NACHRICHT
    english_description = discord.ui.TextInput(
        label="Englische Nachricht",
        placeholder="Your English rules...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    # FARBE
    embed_color = discord.ui.TextInput(
        label="Hex-Farbe",
        placeholder="#5865F2",
        default="#5865F2",
        required=True,
        max_length=7
    )

    async def on_submit(self, interaction: discord.Interaction):

        # =================================================
        # HEX-FARBE
        # =================================================

        color_text = self.embed_color.value.strip()

        if color_text.startswith("#"):
            color_text = color_text[1:]

        try:
            if len(color_text) != 6:
                raise ValueError

            color_value = int(color_text, 16)

        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültige Hex-Farbe.\n"
                "Beispiel: `#5865F2`",
                ephemeral=True
            )
            return

        # =================================================
        # DEUTSCHES EMBED
        # =================================================

        german_embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=discord.Color(color_value)
        )

        # =================================================
        # ENGLISCHES EMBED
        # =================================================

        english_embed = discord.Embed(
            title=self.english_title.value,
            description=self.english_description.value,
            color=discord.Color(color_value)
        )

        # =================================================
        # KANAL AUSWÄHLEN
        # =================================================

        await interaction.response.send_message(
            "📢 **Wähle den Kanal aus, in dem der Embed "
            "gesendet werden soll:**",
            view=ChannelSelectView(
                german_embed,
                english_embed
            ),
            ephemeral=True
        )


# =========================================================
# KANAL AUSWÄHLEN
# =========================================================

class ChannelSelectView(discord.ui.View):

    def __init__(self, german_embed, english_embed):
        super().__init__(timeout=300)

        self.german_embed = german_embed
        self.english_embed = english_embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        placeholder="Kanal auswählen...",
        channel_types=[discord.ChannelType.text],
        min_values=1,
        max_values=1
    )
    async def channel_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.ChannelSelect
    ):

        selected_channel = select.values[0]

        # Nur die ID verwenden
        channel_id = selected_channel.id

        # Echten Kanal aus Discord holen
        channel = interaction.guild.get_channel(channel_id)

        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(
                    channel_id
                )

            except discord.NotFound:
                await interaction.response.send_message(
                    "❌ Der ausgewählte Kanal wurde nicht gefunden.",
                    ephemeral=True
                )
                return

            except discord.Forbidden:
                await interaction.response.send_message(
                    "❌ Ich darf diesen Kanal nicht abrufen.",
                    ephemeral=True
                )
                return

        # Prüfen, ob es ein normaler Textkanal ist
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bitte wähle einen normalen Textkanal.",
                ephemeral=True
            )
            return

        # Bestätigung
        await interaction.response.send_message(
            f"✅ **Kanal ausgewählt:** {channel.mention}\n\n"
            "Drücke **Embed senden**, um das Regelwerk zu posten.",
            view=ConfirmView(
                german_embed=self.german_embed,
                english_embed=self.english_embed,
                channel=channel
            ),
            ephemeral=True
        )


# =========================================================
# EMBED SENDEN
# =========================================================

class ConfirmView(discord.ui.View):

    def __init__(
        self,
        german_embed,
        english_embed,
        channel
    ):
        super().__init__(timeout=300)

        self.german_embed = german_embed
        self.english_embed = english_embed
        self.channel = channel

    @discord.ui.button(
        label="Embed senden",
        style=discord.ButtonStyle.success,
        emoji="📨"
    )
    async def send_embed(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        try:

            # =================================================
            # DEUTSCH IST DIE FESTE STANDARDVERSION
            # =================================================

            await self.channel.send(
                embed=self.german_embed,
                view=LanguageView(
                    self.german_embed,
                    self.english_embed
                )
            )

            await interaction.response.send_message(
                f"✅ **Embed wurde erfolgreich in "
                f"{self.channel.mention} gesendet!**",
                ephemeral=True
            )

            button.disabled = True

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ **Keine Berechtigung.**\n\n"
                "Der Bot braucht in diesem Kanal:\n"
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
                f"❌ Unerwarteter Fehler:\n"
                f"`{error}`",
                ephemeral=True
            )


# =========================================================
# BOT IST ONLINE
# =========================================================

@bot.event
async def on_ready():

    print(f"Bot ist online: {bot.user}")

    try:
        synced = await bot.tree.sync()

        print(
            f"{len(synced)} Slash Commands synchronisiert."
        )

    except Exception as error:

        print(
            f"Fehler beim Synchronisieren: {error}"
        )


# =========================================================
# /EMBED
# =========================================================

@bot.tree.command(
    name="embed",
    description="Erstellt einen Discord Embed"
)
async def embed_command(
    interaction: discord.Interaction
):

    await interaction.response.send_modal(
        EmbedModal()
    )


# =========================================================
# TOKEN
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )

bot.run(TOKEN)
