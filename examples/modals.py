import discord
from discord.ext import commands
from discord.ui import Modal, TextInput

# Defines a custom Modal with questions
# that user has to answer. The callback function
# of this class is called when the user submits the modal
class MyModal(Modal):
    def __init__(self) -> None:
        super().__init__("My Cool Form 1")

        # Set the questions that will be shown in the modal
        # The placeholder is what will be shown when nothing is typed
        self.add_item(TextInput(label="What is your name?", placeholder="Reveal your secrets!"))

        # Provide value argument to prefill the input
        # The style parameter allows you to set the style of the input
        # You can choose from short and long
        self.add_item(
            TextInput(
                label="What is the meaning of life?",
                value="The meaning of life is ",
                style=discord.TextInputStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's name or choice. The self object refers to the
        # Modal object, and the values attribute gets a list of the user's
        # answers. We only want the first one.
        await interaction.response.send_message(
            f"Your name is {self.children[0].value}\n" f"The meaning of life is {self.children[1].value}\n"
        )


class ModalView(discord.ui.View):
    @discord.ui.button(label="Open Modal", style=discord.ButtonStyle.green)
    async def open_modal(self, button: discord.Button, interaction: discord.Interaction):
        # Create the modal
        modal = MyModal()

        # Sending a message containing our modal
        await interaction.response.send_modal(modal)


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("$"),
            intents=discord.Intents(guilds=True, messages=True),
            slash_commands=True,
        )

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")


bot = Bot()


@bot.command()
async def form(ctx: commands.Context):
    """Sends a message with our modal"""

    # Create the view containing our modal
    view = ModalView()
    # Sending a message containing our view
    await ctx.send("Click to open modal:", view=view)


# Can also be used from slash commands directly
@bot.command(message_command=False)
async def modal(ctx: commands.Context):
    # Create the modal
    modal = MyModal()

    # Sending the modal
    await ctx.interaction.response.send_modal(modal)


bot.run("token")
