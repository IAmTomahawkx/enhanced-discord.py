import discord
from discord import app

client = discord.Client(intents=discord.Intents.none())

# Set name=value to set the name of the command. This is optional. If not provided, the name of the class will be used.

# Set description=value or a docstring to set the description of the command. This is optional.
# If not provided, it will be set as "no description"

# Set guilds=[guild_ids] to set the guilds that the command can be used in. This is optional.
# If not provided, the command will be global, i.e., it can be used in all guilds.
@client.application_command  # This is a decorator. It is used to register the class as an slash command.
class EphemeralCommand(
    app.SlashCommand,
    name="ephemeral_message",
    description="Send a message that only you can see!",
):
    # Use app.Option to describe the option's description.
    # Use typehints to define the type of the option. Check out arguments.py for more info.
    message: str = app.Option(description="The message to send.")

    # This is the function that will be called when the command is executed.
    # The function is a coroutine.
    async def callback(self):

        # send_message accepts ephemeral keyword parameter to send a message that only the user can see.
        await self.interaction.response.send_message(self.message, ephemeral=True)


client.run("token")