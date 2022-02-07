import discord
from discord import app

from typing import Optional, Literal

client = discord.Client(intents=discord.Intents.none())


@client.application_command
class TestCommand(app.SlashCommand, name="mycommand", description="Just a testing command :)"):

    # Use typehints to define the type of the option. In this case, it is a string.
    # Use app.Option to describe the option's description using the description keyword argument.
    name: str = app.Option(description="Name of the person")

    # Creates a required number argument which is of type integer.
    # You can set the minimum and maximum enterable value by the user (inclusive) using the min and max keyword arguments.
    # In this case, the minimum value is 1 and the maximum value is 100.
    age: int = app.Option(description="Age of the person (must be between 1 and 100)", min=1, max=100)
    
    # Creates a required string argument with strict choices. i.e. the user must choose from one of the given choices.
    # This is how the user will see it: https://imgur.com/PN2YXhC
    gender: Literal["male", "female", "other"] = app.Option(description="Gender of the person")  # type: ignore

    # Creates an optional argument of type text channel
    # A list of text channels belonging to that guild will be shown to the user to select from.
    # If not entered by user, it will be set to the channel the command was sent in
    # That is done by using the default keyword argument with a lambda expression
    # The default argument accepts a function with a single argument which is the interaction.
    # The function is run when the argument is not entered by the user.
    # In this case, it's a lambda function that returns the channel the command was sent in.
    location: Optional[discord.PartialSlashChannel] = app.Option(
      description="Location of the person",
      default=lambda interaction: interaction.channel
    )

    # Creates an optional string type
    # If not entered by user, it will be set to earth
    planet: Optional[str] = app.Option(description="Planet of the person", default="earth")

    # Create an optional argument of type Member
    # A list of members will be shown to the user to select from
    # If not entered by user, it will be set to None
    friend: Optional[discord.Member] = app.Option(description="Friend of the person", default="(not specified)")

    async def callback(self):
        # Set "user friendly" values for the optional arguments instead of showing "None"
        gender = self.gender if self.gender != "other" else "(not specified)"
        await self.interaction.response.send_message(
            f"Hello {self.name}! "
            f"You are {self.age} years old. "
            f"Your gender is {gender}. "
            f"You live in {self.location} on {self.planet}. "
            f"Your friend is {self.friend}."
        )


client.run("TOKEN")
