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
# EMBED MODAL
# =========================================================

class EmbedModal(discord.ui.Modal, title="Embed erstellen"):

    embed_title = discord.ui.TextInput(
        label="Titel",
        placeholder="z. B. SERVER RULES",
        required=True,
        max_length=256
    )

    embed_description = discord.ui.TextInput(
        label="Nachricht",
        placeholder="Deine Nachricht...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    embed_color = discord.ui.TextInput(
        label="Hex-Farbe",
        placeholder="#5865F2",
        default="#5865F2",
        required=True,
        max_length=7
    )

    async def on_submit(self, interaction: discord.Interaction):

        # Hex-Farbe prüfen
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

        # Embed erstellen
        embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=discord.Color(color_value)
        )

        # Kanal-Auswahl anzeigen
        await interaction.response.send_message(
            "📢 **Wähle den Kanal aus, in dem der Embed gesendet werden soll:**",
            view=ChannelSelectView(embed),
            ephemeral=True
        )


# =========================================================
# CHANNEL SELECT
# =========================================================

class ChannelSelectView(discord.ui.View):

    def __init__(self, embed):
        super().__init__(timeout=300)
        self.embed = embed

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

        # Discord liefert hier ein AppCommandChannel.
        # Wir nehmen deshalb nur die ID und holen den echten Kanal.
        selected_channel = select.values[0]
        channel_id = selected_channel.id

        channel = interaction.guild.get_channel(channel_id)

        # Falls der Kanal nicht im Cache ist:
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
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

        # Nur Textkanäle erlauben
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Bitte wähle einen normalen Textkanal.",
                ephemeral=True
            )
            return

        # Bestätigung anzeigen
        await interaction.response.send_message(
            f"✅ **Kanal ausgewählt:** {channel.mention}\n\n"
            "Drücke **Embed senden**, um den Embed dort zu posten.",
            view=ConfirmView(self.embed, channel),
            ephemeral=True
        )


# =========================================================
# CONFIRM BUTTON
# =========================================================

class ConfirmView(discord.ui.View):

    def __init__(self, embed, channel):
        super().__init__(timeout=300)

        self.embed = embed
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

            # Embed im ausgewählten Kanal senden
            await self.channel.send(embed=self.embed)

            await interaction.response.send_message(
                f"✅ **Embed wurde erfolgreich in "
                f"{self.channel.mention} gesendet!**",
                ephemeral=True
            )

            # Button deaktivieren
            button.disabled = True

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ **Keine Berechtigung.**\n\n"
                "Der Bot braucht in diesem Kanal mindestens:\n"
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
# BOT START
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
# /EMBED COMMAND
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
