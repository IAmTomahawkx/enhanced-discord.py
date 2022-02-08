import discord
from discord import app

client = discord.Client(intents=discord.Intents.none())

# Register the message command.
# This is done by inheriting from app.MessageCommand.
@client.application_command
class ParrotCommand(app.MessageCommand, name="parrot"):
    
    # This will be called when the command is executed.
    # from <right click on a message> -> Apps > parrot
    async def callback(self):
        # self.message is the message that was right clicked
        original_message = self.message

        # Construct the message we want to send in response.
        message = (
            f"*{self.interaction.user} parrot'd a message by {original_message.author}*\n"
            + f"**Content:** {original_message.content}\n"
            + f"**Message was sent:** {discord.utils.format_dt(original_message.created_at)}\n"
        )

        # Send the message
        await self.interaction.response.send_message(message)

client.run("TOKEN")