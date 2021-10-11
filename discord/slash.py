from __future__ import annotations

import inspect
import json
import traceback
from typing import List, Optional, TypeVar, Dict, Any, TYPE_CHECKING, Union, Type, Literal, Tuple, Iterable

from discord.types.interactions import InteractionResponseType, InteractionType

from .utils import MISSING
from .enums import ApplicationCommandType, InteractionType, InteractionResponseType
from .interactions import Interaction
from .member import Member
from .message import Message
from .user import User
from .channel import PartialSlashChannel
from .role import Role


if TYPE_CHECKING:
    from .client import Client
    from .state import ConnectionState
    from .http import HTTPClient
    from .types.snowflake import Snowflake
    from .types.interactions import (
        ApplicationCommand,
        ApplicationCommandInteractionData,
        ApplicationCommandInteractionDataOption,
    )

__all__ = ("Command", "Option")

application_option_type__lookup = {
    str: 3,
    int: 4,
    bool: 5,
    Member: 6,
    User: 6,
    PartialSlashChannel: 7,
    Role: 8,
    float: 10,
}


def _option_to_dict(option: _OptionData) -> dict:
    origin = getattr(option.type, "__origin__", None)
    arg = option.type

    payload = {
        "name": option.name,
        "description": option.description or "none provided",
        "required": True,
        "autocomplete": option.autocomplete,
    }

    if origin is Union:
        if arg.__args__[1] is type(None):  # type: ignore
            payload["required"] = False
            arg = arg.__args__[0]  # type: ignore

        if arg == Union[Member, Role]:
            payload["type"] = 9

    elif origin is Literal:
        values = arg.__args__  # type: ignore
        python_type_ = type(values[0])
        if (
            all(type(value) == python_type_ for value in values)
            and python_type_ in application_option_type__lookup.keys()
        ):
            payload["type"] = application_option_type__lookup[python_type_]
            payload["choices"] = [{"name": literal_value, "value": literal_value} for literal_value in values]

    if origin is not Literal:
        payload["type"] = application_option_type__lookup.get(arg, 3)

    return payload


def _parse_user(
    interaction: Interaction, state: ConnectionState, argument: ApplicationCommandInteractionDataOption
) -> Union[User, Member]:
    target = argument["value"]
    if "members" in interaction.data["resolved"]:  # we're in a guild, parse a member not a user
        payload = interaction.data["resolved"]["members"][target]
        payload["user"] = interaction.data["resolved"]["users"][target]
        return Member(data=payload, state=state, guild=interaction.guild)  # type: ignore

    return User(state=state, data=interaction.data["resolved"]["users"][target])


def _parse_channel(
    interaction: Interaction, state: ConnectionState, argument: ApplicationCommandInteractionDataOption
) -> PartialSlashChannel:
    target = argument["value"]
    resolved = interaction.data["resolved"]["channels"][target]

    return PartialSlashChannel(state=state, data=resolved, guild=interaction.guild)  # type: ignore


def _parse_role(
    interaction: Interaction, state: ConnectionState, argument: ApplicationCommandInteractionDataOption
) -> Role:
    target = argument["value"]
    resolved = interaction.data["resolved"]["roles"][target]

    return Role(guild=interaction.guild, state=state, data=resolved)  # type: ignore


_parse_index = {6: _parse_user, 7: _parse_channel, 8: _parse_role}

T = TypeVar("T")


class Option:
    __slots__ = ("description", "default", "autocomplete")

    def __init__(self, description: str = MISSING, *, default: T = MISSING, autocomplete: bool = False) -> None:
        self.description = description
        self.default = default
        self.autocomplete = autocomplete


class _OptionData:
    __slots__ = ("name", "type", "description", "default", "autocomplete")

    def __init__(
        self,
        name: str,
        type_: Type[Any],
        description: Optional[str] = MISSING,
        default: T = MISSING,
        autocomplete: bool = False,
    ) -> None:
        self.name = name
        self.type = type_
        self.description = description
        self.default = default
        self.autocomplete = autocomplete

    def __repr__(self):
        return f"<OptionData name={self.name} type={self.type} default={self.default} autocomplete={self.autocomplete}>"


class CommandMeta(type):
    def __new__(
        mcs,
        classname: str,
        bases: tuple,
        attrs: Dict[str, Any],
        *,
        type: ApplicationCommandType = ApplicationCommandType.slash_command,
        name: str = MISSING,
        description: str = MISSING,
        parent: Command = MISSING,
        guilds: List[Snowflake] = MISSING,
    ):
        attrs["_arguments_"] = arguments = []  # type: List[_OptionData]
        attrs["_type_"] = type
        attrs["_children_"] = []
        attrs["_permissions_"] = {}

        if name is not MISSING:
            attrs["_name_"] = name
        else:
            attrs["_name_"] = classname

        if description:
            attrs["_description_"] = description
        elif attrs.get("__doc__") is not None:
            attrs["_description_"] = inspect.cleandoc(attrs["__doc__"])
        else:
            attrs["_description_"] = MISSING

        attrs["_parent_"] = parent

        if guilds is not MISSING:
            attrs["_guilds_"] = guilds

        ann = attrs.get("__annotations__", {})

        for k, v in ann.items():
            attr = attrs.get(k, MISSING)
            default = description = MISSING
            autocomplete = False
            if isinstance(attr, Option):
                default = attr.default
                description = attr.description
                autocomplete = attr.autocomplete

            elif attr is not MISSING:
                default = attr

            arguments.append(_OptionData(k, v, description, default, autocomplete))

        if type is ApplicationCommandType.user_command and (len(arguments) != 1 or arguments[0].name != "target"):
            print(arguments)
            raise RuntimeError("User Commands must take exactly one argument, named 'target'")  # TODO: exceptions
        elif type is ApplicationCommandType.message_command and (len(arguments) != 1 or arguments[0].name != "message"):
            raise RuntimeError("Message Commands must take exactly one argument, named 'message'")  # TODO: exceptions

        t = super().__new__(mcs, classname, bases, attrs)

        if parent is not MISSING:
            parent._children_.append(t)  # type: ignore

        return t


class Command(metaclass=CommandMeta):
    _arguments_: List[_OptionData]
    _name_: str
    _type_: ApplicationCommandType
    _description_: Union[str, MISSING]
    _parent_: Optional[Type[Command]]
    _children_: List[Type[Command]]
    _id_: Optional[int] = None
    _guilds_: Optional[List[Snowflake]]
    _permissions_: Optional[
        Dict[int, Dict[Snowflake, Tuple[Literal[1, 2], bool]]]
    ]  # guild id: { role/member id: (type, enabled) }

    interaction: Interaction
    client: Client

    @classmethod
    def set_permissions(cls, guild_id: Snowflake, permissions: Dict[Union[Role, Member], bool]) -> None:
        data: Dict[Snowflake, Tuple[Literal[1, 2], bool]] = {}
        for k, v in permissions.items():
            data[k.id] = (1 if isinstance(k, Role) else 2, v)  # type: ignore

        cls._permissions_[int(guild_id)].update(data)

    @classmethod
    def id(cls) -> Optional[int]:
        return cls._id_

    @classmethod
    def type(cls) -> ApplicationCommandType:
        return cls._type_

    @classmethod
    def to_permissions_dict(cls, guild_id: Snowflake) -> dict:
        payload = {"id": cls.id(), "permissions": []}
        if int(guild_id) not in cls._permissions_:
            return payload

        for k, (t, p) in cls._permissions_[guild_id].items():
            payload["permissions"].append({"id": k, "type": t, "permission": p})

        return payload

    @classmethod
    def to_dict(cls) -> dict:
        if cls._type_ is ApplicationCommandType.slash_command and cls._children_:
            return {
                "name": cls._name_,
                "description": cls._description_ or "no description",
                "options": [x.to_dict() for x in cls._children_],
            }

        options = []
        payload = {
            "name": cls._name_,
            "type": cls._type_.value,  # type: ignore
        }

        if cls._type_ is ApplicationCommandType.slash_command:
            for option in cls._arguments_:
                options.append(_option_to_dict(option))

            payload["description"] = cls._description_ or "no description"
            payload["options"] = options

        return payload

    def _handle_arguments(self, state: ConnectionState):
        intr: ApplicationCommandInteractionData = self.interaction.data

        # This is to use the default value provided in the Option
        parsed = {x.name: x.default for x in self._arguments_}

        # Check if command had any options
        if self._type_ is ApplicationCommandType.slash_command and "options" in intr:
            for option in intr["options"]:
                if option["type"] in {3, 4, 5, 10}:
                    parsed[option["name"]] = option["value"]
                else:
                    parsed[option["name"]] = _parse_index[option["type"]](self.interaction, state, option)
        elif self._type_ is ApplicationCommandType.message_command:
            item = intr["resolved"]["messages"].popitem()[1]
            parsed["message"] = Message(state=state, channel=self.interaction.channel, data=item)  # type: ignore

        elif self._type_ is ApplicationCommandType.user_command:
            user = intr["resolved"]["users"].popitem()[1]
            if "members" in intr["resolved"]:
                p = intr["resolved"]["members"].popitem()[1]
                p["user"] = user
                target = Member(data=p, guild=self.interaction.guild, state=state)  # type: ignore

            else:
                target = User(state=state, data=user)

            parsed["target"] = target

        self.__dict__.update(parsed)

    async def callback(self) -> None:
        ...

    async def autocomplete_callback(self, option_name: str, value) -> List[Dict[str, str]]:
        ...

    async def error(self, exception: Exception) -> None:
        traceback.print_exception(type(exception), exception, exception.__traceback__)


class CommandState:
    def __init__(self, state: ConnectionState, http: HTTPClient) -> None:
        self.state = state
        self.http = http
        self._application_id: Optional[str] = None

        self.command_store: Dict[int, Type[Command]] = {}  # not using Snowflake to keep one type
        self.pre_registration: Dict[Optional[int], List[Type[Command]]] = {}  # the None key will hold global commands

    async def upload_global_commands(self) -> None:
        """
        This function will upload all *global* Application Commands to discord, overwriting previous ones.
        """
        if not self._application_id:
            appinfo = await self.http.application_info()
            self._application_id = appinfo["id"]

        global_commands = self.pre_registration.get(None, [])
        if global_commands:
            store = {(x._name_, x.type().value): x for x in global_commands}  # type: ignore
            payload: List[ApplicationCommand] = await self.http.bulk_upsert_global_commands(
                self._application_id, [x.to_dict() for x in global_commands]
            )
            for x in payload:  # type: ApplicationCommand
                self.command_store[int(x["id"])] = t = store[(x["name"], x["type"])]
                t._id_ = int(x["id"])

    async def upload_guild_commands(self, guild: Optional[Snowflake] = None) -> None:
        """
        This function will upload all *guild* slash commands to discord, overwriting the previous ones.
        Note: this can be fairly slow, as it involves an api call for every guild you have set slash commands for
        """
        if not self._application_id:
            appinfo = await self.http.application_info()
            self._application_id = appinfo["id"]

        targets: Iterable[Tuple[Optional[Snowflake], List[Type[Command]]]] = None  # type: ignore

        if guild:
            if int(guild) not in self.pre_registration:
                raise ValueError(f"guild {guild} has no slash commands set")

            targets = ((guild, self.pre_registration[int(guild)]),)

        else:
            targets = self.pre_registration.items()  # type: ignore

        for (guild, commands) in targets:
            if guild is None:
                continue  # global commands

            store = {(x._name_, x.type().value): x for x in commands}  # type: ignore
            t = [x.to_dict() for x in commands]
            print(t)
            payload: List[ApplicationCommand] = await self.http.bulk_upsert_guild_commands(
                self._application_id, guild, t
            )
            for x in payload:
                self.command_store[int(x["id"])] = t = store[(x["name"], x["type"])]
                t._id_ = int(x["id"])

    async def upload_guild_command_permissions(self, guild_id: Snowflake) -> None:
        commands: List[Type[Command]] = self.pre_registration.get(int(guild_id))
        if not commands:
            raise RuntimeError(
                "No application commands exist for this guild"
            )  # TODO replace this exception with something better

        await self.http.bulk_edit_guild_application_command_permissions(
            self._application_id, guild_id, [x.to_permissions_dict(guild_id) for x in commands]
        )

    def add_command(self, command: Type[Command]) -> None:
        if command._guilds_ is None:
            if None not in self.pre_registration:
                self.pre_registration[None] = []

            self.pre_registration[None].append(command)

        else:
            for x in command._guilds_:
                x = int(x)
                if x not in self.pre_registration:
                    self.pre_registration[x] = []

                self.pre_registration[int(x)].append(command)

    async def dispatch(self, client: Client, interaction: Interaction) -> None:
        cls = self.command_store.get(int(interaction.data["id"]))
        if cls is None:
            return

        inst = cls()
        inst.client = client
        inst.interaction = interaction
        if interaction.type is InteractionType.application_command:
            # TODO: Handle arguments in both cases rather than in only application_command
            inst._handle_arguments(self.state)

            await inst.callback()

        else:  # Type is autocomplete

            # An autocomplete interaction will always have at least one focused option
            focused_option = [x for x in interaction.data["options"] if x.get("focused")][0]

            choices_result: List[Dict[str, str]] = await inst.autocomplete_callback(
                focused_option["name"], focused_option["value"]
            )

            await client.http.create_interaction_response(
                interaction.id,
                interaction.token,
                type=InteractionResponseType.application_command_autocomplete_result.value,
                data={"choices": choices_result},
            )
