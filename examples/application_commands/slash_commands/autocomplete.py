from typing import Any, Dict, List, Union

import aiohttp
import datetime

import discord
from discord import app

# https://github.com/joke2k/faker
from faker import Faker


client = discord.Client(intents=discord.Intents.none())

# Create the faker object
fake = Faker()

# Create some fake names
fake_names = sorted([fake.unique.first_name() for _ in range(500)])


@client.application_command
class RandomCommand(
    app.SlashCommand,
    name="person_info",
    description="Sends information for a fake person."
):
    # Use app.Option to enable autocomplete on an option by setting autocomplete=True
    # Only str, int, and float supports autocomplete.
    name: str = app.Option(description="Name of the person", autocomplete=True)

    async def callback(self):
        
        # Get the name that the user typed
        name = self.name
        
        # Create a random fake profie
        profile = fake.profile()

        # Generate the fake information message
        message = f"Here is the information for {name}:\n" + \
                  f"**Sex:** {profile['sex']}\n" + \
                  f"**Age:** {int((datetime.date.today()-profile['birthdate']).days / 365)}\n" + \
                  f"**Job:** {profile['job']}\n" + \
                  f"**Address:** {profile['residence']}\n"
                
        # Send the message
        await self.interaction.response.send_message(message)

    # options is a dictionary of all the options that the user has filled until now
    # this also includes the option that triggered the autocomplete
    # focused is the name of the option that triggered the autocomplete
    # The method must return app.AutocompleteResult
    async def autocomplete(self, options: Dict[str, Union[int, float, str]], focused: str) -> app.AutoCompleteResponse:
        
        # Create the response object
        response = app.AutoCompleteResponse()        

        # Get the value that the user typed
        value = options[focused]
        
        # Discord sends blank strings at the beginning of the autocomplete. So in that case we can return an empty response.
        if not value:
            return response
    
        # Lowercase the value that user typed to prevent case sensitivity
        assert isinstance(value, str)
        value = value.lower()
        
        for name in fake_names:
            
            if value in name.lower():
                # Add the option to the response
                # name is the value that the user will see
                # value is the value that we will receive if user selects that option
                response.add_option(name=name, value=name)
                
                # A maximum of 25 options can be returned
                if len(response) == 25: 
                    break

        return response
        

@client.application_command
class ColourCommand(
    app.SlashCommand,
    name="colour_info",
    description="Sends information about a colour."
):
    # Use app.Option to enable autocomplete on an option by setting autocomplete=True
    # Only str, int, and float supports autocomplete.
    colour: str = app.Option(description="The colour", autocomplete=True)

    async def callback(self):

        await self.interaction.response.defer()

        # We are using the Alexflipnote API to get some basic information about the colour
        # The colour endpoint to be precise.
        # https://alexflipnote.dev/colour/<hex_colour>


        # self.colour is the value that the user selected.
        # We need to remove the # from the colour so we can send it to the API.
        colour_hex = self.colour[1:]

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.alexflipnote.dev/colour/{colour_hex}") as response:

                # Get the response as a json.
                # This is a dictionary containing the colour information.
                json_data: Dict[str, Any] = await response.json()

        # Construct the message with the information we got from the API.
        message = f"🎨 **Information about {json_data['name']}**\n" + \
                  f"**Hex:** {json_data['hex']}\n" + \
                  f"**RGB:** {json_data['rgb']}\n" + \
                  f"**Image:** {json_data['image']}\n"

        # Send the message.
        await self.interaction.followup.send(message)

    async def autocomplete(self, options: Dict[str, Union[int, float, str]], focused: str) -> app.AutoCompleteResponse:
        # Create the response object.
        response = app.AutoCompleteResponse()

        # Get the value that the user typed.
        value = options[focused]
        assert isinstance(value, str)
        
        # Create a list of random colours.
        # range(25) = loop 25 times.
        # _ is a placeholder for the value that we are not using.
        colours: List[discord.Colour] = [discord.Colour.random() for _ in range(25)]

        # Discord sends blank strings at the beginning of the autocomplete. So in that case we show all options to the user.
        if not value:
            # Add all the colours to the response.
            for colour in colours:
                response.add_option(name=str(colour), value=str(colour))
            
            # Return the response
            return response

        # Loop through all our colours.
        # Check if the value that the user typed is in the color.
        # If it does, add it to the response.
        for colour in colours:
            if str(value).strip("#") in str(colour)[1:]:
                response.add_option(name=str(colour), value=str(colour))
        
        # Return the response
        return response


client.run("token")