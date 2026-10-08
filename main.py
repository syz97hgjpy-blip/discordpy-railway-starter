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

        # Englisch bearbeiten nur aktiv,
        # wenn Zweitsprache aktiviert wurde.
        self.language_edit_button.disabled = not self.data.bilingual

        if self.data.bilingual:

            self.language_toggle_button.label = "Zweitsprache: AN"
            self.language_toggle_button.style = (
                discord.ButtonStyle.success
            )

        else:

            self.language_toggle_button.label = "Zweitsprache: AUS"
            self.language_toggle_button.style = (
                discord.ButtonStyle.secondary
            )

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
    async def german_edit_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.send_modal(
            EmbedContentModal(self.data)
        )

    @discord.ui.button(
        label="Zweitsprache: AUS",
        emoji="🌐",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def language_toggle_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

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
    async def language_edit_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

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
    async def continue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if (
            not self.data.german_title
            or not self.data.german_description
        ):

            await interaction.response.send_message(
                "❌ Bitte fülle zuerst die deutsche Version aus.",
                ephemeral=True
            )

            return

        if self.data.bilingual:

            if (
                not self.data.english_title
                or not self.data.english_description
            ):

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
                "❌ Ungültige Hex-Farbe.\n"
                "Beispiel: `#5865F2`",
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
        emoji="🚀",
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
    description="Erstellt einen Discord Embed"
)
async def embed_command(
    interaction: discord.Interaction
):

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

    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden."
    )


bot.run(TOKEN)
