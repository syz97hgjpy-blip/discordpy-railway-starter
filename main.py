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
# EMBED STUDIO – HILFSFUNKTIONEN
# =========================================================

def format_status(view):
    german = "✅ Konfiguriert" if view.german_title and view.german_description else "⚪ Nicht konfiguriert"

    if view.bilingual:
        english = "✅ Konfiguriert" if view.english_title and view.english_description else "⚪ Nicht konfiguriert"
        language = "🟢 Aktiv"
    else:
        english = "➖ Deaktiviert"
        language = "⚪ Nur Deutsch"

    return (
        "## ✦ Embed Studio\n"
        "Erstelle hier deinen Discord-Embed.\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**🇩🇪 Deutsche Version**\n"
        f"{german}\n\n"
        f"**🌐 Zweitsprache**\n"
        f"{language}\n"
        f"Englische Version: {english}\n\n"
        f"**🎨 Design**\n"
        f"`#{view.color_value:06X}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Konfiguriere die Bereiche über die Buttons unten."
    )


# =========================================================
# EMBED STUDIO
# =========================================================

class EmbedStudioView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=600)

        self.german_title = None
        self.german_description = None

        self.english_title = None
        self.english_description = None

        self.color_value = 0x5865F2

        self.bilingual = False

        self.update_buttons()

    def update_buttons(self):

        # Englisch bearbeiten
        self.english_button.disabled = not self.bilingual

        # Sprachstatus
        if self.bilingual:
            self.language_button.label = "Zweitsprache aktiviert"
            self.language_button.emoji = "🌐"
            self.language_button.style = discord.ButtonStyle.success
        else:
            self.language_button.label = "Zweitsprache aktivieren"
            self.language_button.emoji = "🌐"
            self.language_button.style = discord.ButtonStyle.secondary

        # Veröffentlichungsbutton
        german_ready = (
            self.german_title
            and self.german_description
        )

        english_ready = (
            self.english_title
            and self.english_description
        )

        if self.bilingual:
            self.publish_button.disabled = not (
                german_ready and english_ready
            )
        else:
            self.publish_button.disabled = not german_ready

    # =====================================================
    # DEUTSCH
    # =====================================================

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
            GermanModal(self)
        )

    # =====================================================
    # ENGLISCH
    # =====================================================

    @discord.ui.button(
        label="English bearbeiten",
        emoji="🇬🇧",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def english_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not self.bilingual:
            await interaction.response.send_message(
                "Aktiviere zuerst die Zweitsprache.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            EnglishModal(self)
        )

    # =====================================================
    # ZWEITSPRACHE
    # =====================================================

    @discord.ui.button(
        label="Zweitsprache aktivieren",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def language_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.bilingual = not self.bilingual

        if not self.bilingual:
            self.english_title = None
            self.english_description = None

        self.update_buttons()

        await interaction.response.edit_message(
            content=format_status(self),
            view=self
        )

    # =====================================================
    # DESIGN
    # =====================================================

    @discord.ui.button(
        label="Design",
        emoji="🎨",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def design_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            DesignModal(self)
        )

    # =====================================================
    # VERÖFFENTLICHEN
    # =====================================================

    @discord.ui.button(
        label="Veröffentlichen",
        emoji="🚀",
        style=discord.ButtonStyle.success,
        row=2
    )
    async def publish_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.update_buttons()

        if button.disabled:
            await interaction.response.send_message(
                "❌ Der Embed ist noch nicht vollständig konfiguriert.",
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
            content=(
                "## 📢 Veröffentlichung\n\n"
                "Wähle jetzt den Kanal aus, in dem dein Embed "
                "veröffentlicht werden soll."
            ),
            view=ChannelSelectView(
                german_embed,
                english_embed,
                self.bilingual
            )
        )


# =========================================================
# DEUTSCHES MODAL
# =========================================================

class GermanModal(discord.ui.Modal):

    def __init__(self, studio):
        super().__init__(title="Deutsche Version")

        self.studio = studio

        self.title_input = discord.ui.TextInput(
            label="Titel",
            placeholder="z. B. SERVER REGELN",
            required=True,
            max_length=256
        )

        self.description_input = discord.ui.TextInput(
            label="Nachricht",
            placeholder="Schreibe hier deinen deutschen Inhalt...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction):

        self.studio.german_title = self.title_input.value
        self.studio.german_description = self.description_input.value

        self.studio.update_buttons()

        await interaction.response.edit_message(
            content=format_status(self.studio),
            view=self.studio
        )


# =========================================================
# ENGLISCHES MODAL
# =========================================================

class EnglishModal(discord.ui.Modal):

    def __init__(self, studio):
        super().__init__(title="English Version")

        self.studio = studio

        self.title_input = discord.ui.TextInput(
            label="Title",
            placeholder="e.g. SERVER RULES",
            required=True,
            max_length=256
        )

        self.description_input = discord.ui.TextInput(
            label="Message",
            placeholder="Write your English content here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=4000
        )

        self.add_item(self.title_input)
        self.add_item(self.description_input)

    async def on_submit(self, interaction):

        self.studio.english_title = self.title_input.value
        self.studio.english_description = self.description_input.value

        self.studio.update_buttons()

        await interaction.response.edit_message(
            content=format_status(self.studio),
            view=self.studio
        )


# =========================================================
# DESIGN MODAL
# =========================================================

class DesignModal(discord.ui.Modal):

    def __init__(self, studio):
        super().__init__(title="Embed Design")

        self.studio = studio

        self.color_input = discord.ui.TextInput(
            label="Embed-Farbe",
            placeholder="#5865F2",
            default=f"#{studio.color_value:06X}",
            required=True,
            max_length=7
        )

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

        self.studio.color_value = color_value

        self.studio.update_buttons()

        await interaction.response.edit_message(
            content=format_status(self.studio),
            view=self.studio
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
        placeholder="Zielkanal auswählen...",
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
                "## ✦ Veröffentlichung vorbereiten\n\n"
                f"**Zielkanal:** {channel.mention}\n\n"
                "Überprüfe deine Auswahl und veröffentliche "
                "den Embed anschließend."
            ),
            view=PublishConfirmView(
                self.german_embed,
                self.english_embed,
                self.bilingual,
                channel
            )
        )


# =========================================================
# VERÖFFENTLICHUNG BESTÄTIGEN
# =========================================================

class PublishConfirmView(discord.ui.View):

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
        label="Embed veröffentlichen",
        emoji="🚀",
        style=discord.ButtonStyle.success
    )
    async def publish(
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
                    "## ✅ Erfolgreich veröffentlicht\n\n"
                    f"Der Embed wurde in {self.channel.mention} "
                    "veröffentlicht."
                ),
                view=self
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ich habe in diesem Kanal nicht die nötigen "
                "Berechtigungen.\n\n"
                "Benötigt werden:\n"
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
# SPRACHBUTTONS AUF DEM ÖFFENTLICHEN EMBED
# =========================================================

class LanguageView(discord.ui.View):

    def __init__(
        self,
        german_embed,
        english_embed
    ):
        super().__init__(timeout=None)

        self.german_embed = german_embed
        self.english_embed = english_embed

    @discord.ui.button(
        label="Deutsch",
        emoji="🇩🇪",
        style=discord.ButtonStyle.secondary
    )
    async def german(
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
    async def english(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_message(
            embed=self.english_embed,
            ephemeral=True
        )


# =========================================================
# BOT READY
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
    description="Öffnet das Embed Studio"
)
async def embed_command(
    interaction: discord.Interaction
):

    studio = EmbedStudioView()

    await interaction.response.send_message(
        content=format_status(studio),
        view=studio,
        ephemeral=True
    )


# =========================================================
# TOKEN
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
