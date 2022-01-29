from typing import TypedDict, Literal, List


class SlashCommandArgument(TypedDict):
    name: str
    description: str
    required: bool
    autocomplete: bool
    type: Literal[3, 4, 5, 6, 7, 8, 9, 10]


class ApplicationCommand(TypedDict):
    name: str
    type: Literal[1, 2, 3]


class SlashCommand(ApplicationCommand):
    description: str
    options: List[SlashCommandArgument]
