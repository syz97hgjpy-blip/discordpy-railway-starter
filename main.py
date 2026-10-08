import os
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


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

        color_text = self.embed_color.value.strip().replace("#", "")

        try:
            if len(color_text) != 6:
                raise ValueError

            color = int(color_text, 16)

        except ValueError:
            await interaction.response.send_message(
                "❌ Ungültige Hex-Farbe. Beispiel: `#5865F2`",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=self.embed_title.value,
            description=self.embed_description.value,
            color=discord.Color(color)
        )

        await interaction.response.send_message(
            "📢 **Wähle den Kanal aus, in dem der Embed gesendet werden soll:**",
            view=ChannelSelectView(embed),
            ephemeral=True
        )


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

        channel = select.values[0]

        # Discord kann hier verschiedene Channel-Typen liefern.
        # Wir prüfen deshalb nur, ob der Kanal Nachrichten senden kann.
        if not hasattr(channel, "send"):
            await interaction.response.send_message(
                "❌ Dieser Kanal kann keine Nachrichten empfangen.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ Kanal ausgewählt: {channel.mention}\n"
            f"Drücke **Embed senden**, um den Embed zu posten.",
            view=ConfirmView(self.embed, channel),
            ephemeral=True
        )


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
            await self.channel.send(embed=self.embed)

            await interaction.response.send_message(
                f"✅ Embed wurde in {self.channel.mention} gesendet!",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Ich darf in diesem Kanal keine Nachrichten senden. "
                "Bitte prüfe die Kanalrechte.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                f"❌ Fehler: `{error}`",
                ephemeral=True
            )


@bot.event
async def on_ready():

    print(f"Bot ist online: {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} Slash Commands synchronisiert.")

    except Exception as error:
        print(f"Fehler beim Synchronisieren: {error}")


@bot.tree.command(
    name="embed",
    description="Erstellt einen Discord Embed"
)
async def embed_command(interaction: discord.Interaction):

    await interaction.response.send_modal(EmbedModal())


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN wurde nicht gefunden.")

bot.run(TOKEN)
