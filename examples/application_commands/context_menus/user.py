import discord
from discord import app

client = discord.Client(intents=discord.Intents.none())

@client.application_command
class UserInfoCommand(app.UserCommand, name="userinfo"):

    async def callback(self):

        # self.target is the user that was right clicked
        user = self.target

        # Construct the message we want to send in response.
        message = (
            f"**Username:** {user.name}\n"
            + f"**Discriminator:** {user.discriminator}\n"
            + f"**ID:** {user.id}\n"
            + f"**Created at:** {discord.utils.format_dt(user.created_at)}\n"
            + f"**Is bot:** {user.bot}\n"
        )

        # Send the message
        await self.interaction.response.send_message(message)

client.run("TOKEN")