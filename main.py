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
    async def german_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            embed=self.german_embed,
            ephemeral=True
        )

    @discord.ui.button(
        label="English",
        emoji="🇬🇧",
        style=discord.ButtonStyle.secondary
    )
    async def english_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.send_message(
            embed=self.english_embed,
            ephemeral=True
        )


# =========================================================
# HAUPTMENÜ
# =========================================================

class EmbedSetupView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=300)

        self.german_title = None
        self.german_description = None

        self.english_title = None
        self.english_description = None

        self.color_value = 0x5865F2

        self.bilingual = False

        self.update_buttons()

    def update_buttons(self):

        # English-Button
        self.english_button.disabled = not self.bilingual

        # Status des Sprachbuttons
        if self.bilingual:
            self.language_button.label = "Zweitsprache: AN"
            self.language_button.style = discord.ButtonStyle.success
        else:
            self.language_button.label = "Zweitsprache: AUS"
            self.language_button.style = discord.ButtonStyle.secondary

        # Kanal-Button
        if self.german_title and self.german_description:
            if self.bilingual:
                self.channel_button.disabled = not (
                    self.english_title and self.english_description
                )
            else:
                self.channel_button.disabled = False
        else:
            self.channel_button.disabled = True

    def status_text(self):

        german_status = (
            "✅ Deutsch ausgefüllt"
            if self.german_title and self.german_description
            else "⬜ Deutsch noch nicht ausgefüllt"
        )

        if self.bilingual:
            english_status = (
                "✅ Englisch ausgefüllt"
                if self.english_title and self.english_description
                else "⬜ Englisch noch nicht ausgefüllt"
            )
        else:
            english_status = "➖ Zweitsprache deaktiviert"

        return (
            "## 📝 Embed erstellen\n\n"
            f"{german_status}\n"
            f"{english_status}\n\n"
            "Wähle unten die gewünschten Einstellungen."
        )

    # -----------------------------------------------------
    # DEUTSCH BEARBEITEN
    # -----------------------------------------------------

    @discord.ui.button(
        label="Deutsch bearbeiten",
        emoji="🇩🇪",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def german_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            GermanEmbedModal(self)
        )

    # -----------------------------------------------------
    # ZWEITSPRACHE AN / AUS
    # -----------------------------------------------------

    @discord.ui.button(
        label="Zweitsprache: AUS",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def language_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.bilingual = not self.bilingual

        self.update_buttons()

        await interaction.response.edit_message(
            content=self.status_text(),
            view=self
        )

    # -----------------------------------------------------
    # ENGLISH BEARBEITEN
    # -----------------------------------------------------

    @discord.ui.button(
        label="English bearbeiten",
        emoji="🇬🇧",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def english_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not self.bilingual:
            await interaction.response.send_message(
                "❌ Aktiviere zuerst die Zweitsprache.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            EnglishEmbedModal(self)
        )

    # -----------------------------------------------------
    # KANAL AUSWÄHLEN
    # -----------------------------------------------------

    @discord.ui.button(
        label="Kanal auswählen",
        emoji="📢",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def channel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.update_buttons()

        if button.disabled:
            await interaction.response.send_message(
                "❌ Bitte fülle zuerst alle benötigten Felder aus.",
                ephemeral=True
            )
            return

        german_embed = discord.Embed(
            title=self.german_title,
            description=self.german_description,
            color=discord.Color(self.color_value)
        )

        english_embed = None

        if self.bilingual:
            english_embed = discord.Embed(
                title=self.english_title,
                description=self.english_description,
                color=discord.Color(self.color_value)
            )

        await interaction.response.edit_message(
            content="📢 **Wähle den Kanal aus, in dem der Embed gesendet werden soll:**",
            view=ChannelSelectView(
                german_embed,
                english_embed,
                self.bilingual
            )
        )


# =========================================================
# DEUTSCHES MODAL
# =========================================================

class GermanEmbedModal(discord.ui.Modal):

    def __init__(self, setup_view):
        super().__init__(title="Deutsch bearbeiten")

        self.setup_view = setup_view

        self.title_input = discord.ui.TextInput(
            label="Deutscher Titel",
            placeholder="z. B. SERVER REGELN",
            required=True,
            max_length=256
        )

        self.description_input = discord.ui.TextInput(
            label="Deutsche Nachricht",
            placeholder="Dein deutsches Regelwerk...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.color_input = discord.ui.TextInput(
            label="Hex-Farbe",
            placeholder="#5865F2",
            default="#5865F2",
            required=True,
            max_length=7
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)
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
                "❌ Ungültige Hex-Farbe.\n"
                "Beispiel: `#5865F2`",
                ephemeral=True
            )
            return

        self.setup_view.german_title = self.title_input.value
        self.setup_view.german_description = self.description_input.value
        self.setup_view.color_value = color_value

        self.setup_view.update_buttons()

        await interaction.response.edit_message(
            content=self.setup_view.status_text(),
            view=self.setup_view
        )


# =========================================================
# ENGLISCHES MODAL
# =========================================================

class EnglishEmbedModal(discord.ui.Modal):

    def __init__(self, setup_view):
        super().__init__(title="English bearbeiten")

        self.setup_view = setup_view

        self.title_input = discord.ui.TextInput(
            label="Englischer Titel",
            placeholder="z. B. SERVER RULES",
            required=True,
            max_length=256
        )

        self.description_input = discord.ui.TextInput(
            label="Englische Nachricht",
            placeholder="Your English rules...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction):

        self.setup_view.english_title = self.title_input.value
        self.setup_view.english_description = self.description_input.value

        self.setup_view.update_buttons()

        await interaction.response.edit_message(
            content=self.setup_view.status_text(),
            view=self.setup_view
        )


# =========================================================
# KANALAUSWAHL
# =========================================================

class ChannelSelectView(discord.ui.View):

    def __init__(
        self,
        german_embed,
        english_embed,
        bilingual
    ):
        super().__init__(timeout=300)

        self.german_embed = german_embed
        self.english_embed = english_embed
        self.bilingual = bilingual

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

        channel_id = selected_channel.id

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

        if not isinstance(channel, discord.TextChannel):

            await interaction.response.send_message(
                "❌ Bitte wähle einen normalen Textkanal.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content=(
                f"✅ **Kanal ausgewählt:** {channel.mention}\n\n"
                "Drücke **Embed senden**, um den Embed dort zu posten."
            ),
            view=ConfirmView(
                self.german_embed,
                self.english_embed,
                self.bilingual,
                channel
            )
        )


# =========================================================
# BESTÄTIGUNG
# =========================================================

class ConfirmView(discord.ui.View):

    def __init__(
        self,
        german_embed,
        english_embed,
        bilingual,
        channel
    ):
        super().__init__(timeout=300)

        self.german_embed = german_embed
        self.english_embed = english_embed
        self.bilingual = bilingual
        self.channel = channel

    @discord.ui.button(
        label="Embed senden",
        emoji="📨",
        style=discord.ButtonStyle.success
    )
    async def send_embed(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

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

                await self.channel.send(
                    embed=self.german_embed
                )

            button.disabled = True

            await interaction.response.edit_message(
                content=(
                    f"✅ **Embed wurde erfolgreich in "
                    f"{self.channel.mention} gesendet!**"
                ),
                view=self
            )

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
                f"❌ Unerwarteter Fehler:\n`{error}`",
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
# /EMBED
# =========================================================

@bot.tree.command(
    name="embed",
    description="Erstellt einen Discord Embed"
)
async def embed_command(
    interaction: discord.Interaction
):

    view = EmbedSetupView()

    await interaction.response.send_message(
        content=view.status_text(),
        view=view,
        ephemeral=True
    )


# =========================================================
# TOKEN PRÜFEN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
