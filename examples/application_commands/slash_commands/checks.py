import discord
from discord import app


client = discord.Client(intents=discord.Intents.none())

@client.application_command
class SlapCommand(app.SlashCommand, name="slap", description="Slap someone!"):
    
    member: discord.Member = app.Option(description="The member you want to slap.")

    async def error(self, error: Exception):
        # RuntimeError is raised when a check fails.
        if isinstance(error, RuntimeError):
            await self.interaction.response.send_message("You can't slap yourself!", ephemeral=True)
        else:
            # For other errors call the default error handler.
            await super().error(error)
    
    async def callback(self):
        await self.interaction.response.send_message(f"{self.member.mention} just got slapped by {self.interaction.user.mention}!")

    # This method is called before callback is called.
    # Return True to allow the command to be executed, or False to deny it.
    async def check(self):
        return self.member.id != self.interaction.user.id


client.run("TOKEN")