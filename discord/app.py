from __future__ import annotations

import inspect
import sys
import json
import traceback
from typing import List, Optional, TypeVar, Dict, Any, TYPE_CHECKING, Union, Type, Literal, Tuple, Iterable, Generic

from .utils import MISSING, maybe_coroutine, evaluate_annotation
from .enums import ApplicationCommandType, InteractionType
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
        ApplicationCommandOptionChoice,
    )

__all__ = ("AutoCompleteResponse", "Command", "UserCommand", "MessageCommand", "SlashCommand", "Option")

CommandT = TypeVar("CommandT", bound="Command")
NoneType = type(None)

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
        if arg.__args__[1] is NoneType:  # type: ignore
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

    if option.min is not MISSING or option.max is not MISSING:
        if arg not in {int, float}:
            raise ValueError(
                f"min or max specified for argument {option.name}, but is not an int or float."
            )  # TODO: exceptions

        if option.min and option.max and option.min > option.max:
            raise ValueError(f"{option} has a min value that is greater than the max value")

        if option.min:
            payload["min_value"] = option.min
        if option.max:
            payload["max_value"] = option.max

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
AutoCompleteResponseT = TypeVar("AutoCompleteResponseT", bound="AutoCompleteResponse")


class AutoCompleteResponse(dict):  # TODO: docs
    def add_option(self, name: str, value: Union[str, int]) -> AutoCompleteResponseT:
        self[name] = value
        return self

    def remove_option(self, name: str) -> AutoCompleteResponseT:
        del self[name]
        return self

    def __iter__(self):
        return iter([{"name": k, "value": v} for k, v in self.items()])


class Option:
    __slots__ = ("autocomplete", "default", "description", "max", "min")

    def __init__(
        self,
        description: str = MISSING,
        *,
        autocomplete: bool = False,
        min: Union[int, float] = MISSING,
        max: Union[int, float] = MISSING,
        default: T = MISSING,
    ) -> None:
        self.description = description
        self.default = default
        self.autocomplete = autocomplete
        self.min = min
        self.max = max


class _OptionData:
    __slots__ = ("autocomplete", "default", "description", "max", "min", "name", "type")

    def __init__(
        self,
        name: str,
        type_: Type[Any],
        autocomplete: bool,
        description: Optional[str] = MISSING,
        default: T = MISSING,
        min: Union[int, float] = MISSING,
        max: Union[int, float] = MISSING,
    ) -> None:
        self.name = name
        self.type = type_
        self.autocomplete = autocomplete
        self.description = description
        self.default = default
        self.min = min
        self.max = max

    def __repr__(self):
        return f"<OptionData name={self.name} type={self.type} default={self.default}>"

    def handle_default(self, interaction: Interaction) -> Any:
        resp = self.default

        if callable(resp):
            resp = resp(interaction)

        return resp


class CommandMeta(type):
    def __new__(
        mcs,
        classname: str,
        bases: tuple,
        attrs: Dict[str, Any],
        *,
        name: str = MISSING,
        description: str = MISSING,
        parent: Command = MISSING,
        guilds: List[Snowflake] = MISSING,
    ):
        attrs["_arguments_"] = arguments = []  # type: List[_OptionData]
        attrs["_children_"] = {}
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

        attrs["_guilds_"] = guilds or None

        ann = attrs.get("__annotations__", {})

        for k, v in ann.items():
            attr = attrs.get(k, MISSING)
            default = description = min_ = max_ = MISSING
            autocomplete = False
            if isinstance(attr, Option):
                default = attr.default
                description = attr.description
                autocomplete = attr.autocomplete
                min_ = attr.min
                max_ = attr.max

            elif attr is not MISSING:
                default = attr

            arguments.append(_OptionData(k, v, autocomplete, description, default, min_, max_))

        if type is ApplicationCommandType.user_command and (len(arguments) != 1 or arguments[0].name != "target"):
            raise RuntimeError("User Commands must take exactly one argument, named 'target'")  # TODO: exceptions
        elif type is ApplicationCommandType.message_command and (len(arguments) != 1 or arguments[0].name != "message"):
            raise RuntimeError("Message Commands must take exactly one argument, named 'message'")  # TODO: exceptions

        t = super().__new__(mcs, classname, bases, attrs)

        if parent is not MISSING:
            parent._children_[attrs["_name_"]] = t  # type: ignore

        return t


class Command(metaclass=CommandMeta):
    _arguments_: List[_OptionData]
    _name_: str
    _type_: ApplicationCommandType
    _description_: Union[str, MISSING]
    _parent_: Optional[Type[Command]]
    _children_: Dict[str, Type[Command]]
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
            payload = {
                "name": cls._name_,
                "description": cls._description_ or "no description",
                "options": [x.to_dict() for x in cls._children_.values()],
            }

            if cls._parent_:
                payload["type"] = 2

            return payload

        options = []
        payload = {
            "name": cls._name_,
            "type": cls._type_.value,  # type: ignore
        }

        if cls._type_ is ApplicationCommandType.slash_command:
            for option in cls._arguments_:
                if isinstance(option.type, str):
                    option.type = evaluate_annotation(option.type, sys.modules[cls.__module__].__dict__, {}, {})
                options.append(_option_to_dict(option))

            payload["description"] = cls._description_ or "no description"
            payload["options"] = options

        return payload

    async def callback(self) -> None:
        ...

    async def autocomplete(
        self, options: Dict[str, Union[int, float, str]], focused: str
    ) -> List[ApplicationCommandOptionChoice]:
        ...

    async def check(self) -> bool:
        return True

    async def pre_check(self) -> bool:
        return True

    async def error(self, exception: Exception) -> None:
        traceback.print_exception(type(exception), exception, exception.__traceback__)


class UserCommand(Command, Generic[CommandT]):
    _type_ = ApplicationCommandType.user_command

    target: Union[Member, User]

    def _handle_arguments(self, interaction: Interaction, state: ConnectionState, _, __) -> None:
        intr: ApplicationCommandInteractionData = interaction.data

        user = intr["resolved"]["users"].popitem()[1]
        if "members" in intr["resolved"]:
            p = intr["resolved"]["members"].popitem()[1]
            p["user"] = user
            target = Member(data=p, guild=interaction.guild, state=state)  # type: ignore

        else:
            target = User(state=state, data=user)

        self.target = target


class MessageCommand(Command, Generic[CommandT]):
    _type_ = ApplicationCommandType.message_command

    message: Message

    def _handle_arguments(self, interaction: Interaction, state: ConnectionState, _, __) -> None:
        intr: ApplicationCommandInteractionData = interaction.data
        item = intr["resolved"]["messages"].popitem()[1]
        self.message = Message(state=state, channel=interaction.channel, data=item)  # type: ignore


class SlashCommand(Command, Generic[CommandT]):
    _type_ = ApplicationCommandType.slash_command

    def _handle_arguments(
        self,
        interaction: Interaction,
        state: ConnectionState,
        options: List[ApplicationCommandInteractionDataOption],
        arguments: List[_OptionData],
    ) -> None:
        parsed = {}

        for option in options:
            if option["type"] in {3, 4, 5, 10}:
                parsed[option["name"]] = option["value"]
            else:
                parsed[option["name"]] = _parse_index[option["type"]](interaction, state, option)

        unset = {x.name for x in arguments} - set(parsed.keys())
        if unset:
            args: Dict[str, _OptionData] = {x.name: x for x in arguments}
            parsed.update({x: args[x].handle_default(interaction) for x in unset})

        self.__dict__.update(parsed)


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
                self._application_id, [x.to_dict() for x in global_commands if not x._parent_]  # type: ignore
            )
            for x in payload:  # type: ApplicationCommand
                self.command_store[int(x["id"])] = t = store[(x["name"], x["type"])]
                t._id_ = int(x["id"])

    async def upload_guild_commands(
        self,
        ext_commands: Dict[int | None, Any],
        guild: Optional[Snowflake] = None,
    ) -> None:
        """
        This function will upload all *guild* slash commands to discord, overwriting the previous ones.
        Note: this can be fairly slow, as it involves an api call for every guild you have set slash commands for
        """
        # ext_commands is a dict of guild_id -> command payloads

        if not self._application_id:
            appinfo = await self.http.application_info()
            self._application_id = appinfo["id"]

        targets: Iterable[Tuple[Optional[Snowflake], List[Type[Command]]]]

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
            t = [x.to_dict() for x in commands if not x._parent_]  # All tom's commands for a specific guild
            if guild in ext_commands:
                t.extend(ext_commands[guild])  # All ext commands for a specific guild
            payload: List[ApplicationCommand] = await self.http.bulk_upsert_guild_commands(
                self._application_id, guild, t
            )
            for x in payload:
                if (x["name"], x["type"]) not in store:
                    continue  # This is an ext command
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
        if not hasattr(command, "_type_"):
            raise ValueError("Application Command does not have a type mixin")

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
        print(json.dumps(interaction.data, indent=4))
        cls = self.command_store.get(int(interaction.data["id"]))
        if cls is None:
            return

        # first check if we're dealing with a subcommand

        options = interaction.data.get("options")
        if cls._type_ is ApplicationCommandType.slash_command:
            while options and options[0]["type"] in {1, 2}:
                name = options[0]["name"]
                options = options[0]["options"]
                cls = cls._children_[name]

        inst = cls()
        inst.client = client
        inst.interaction = interaction

        if interaction.type is InteractionType.application_command_autocomplete:
            try:
                await self._dispatch_autocomplete(inst, options)
            except Exception as e:
                client.dispatch("application_command_error", interaction, e)  # TODO: document this one
                await maybe_coroutine(inst.error, e)

        else:
            try:
                await self._dispatch(inst, options)
            except Exception as e:
                client.dispatch("application_command_error", interaction, e)  # TODO: document this one
                await maybe_coroutine(inst.error, e)

    async def _dispatch(self, inst: CommandT, options: List[ApplicationCommandInteractionDataOption]):
        if not await maybe_coroutine(inst.pre_check):
            raise RuntimeError(f"The pre-check for {inst._name_} failed.")

        inst._handle_arguments(inst.interaction, self.state, options or [], inst._arguments_)

        if not await maybe_coroutine(inst.check):
            raise RuntimeError(f"The check for {inst._name_} failed.")

        await inst.callback()

    async def _dispatch_autocomplete(self, inst: CommandT, data: List[ApplicationCommandInteractionDataOption]):
        options: Dict[str, Optional[Union[str, int, float]]] = {x.name: None for x in inst._arguments_}
        focused = None
        print(data)

        for x in data:
            val = x["value"]

            if x["type"] in {6, 7, 8}:
                options[x["name"]] = int(val)

            else:
                options[x["name"]] = val

            if "focused" in x:
                focused = x["name"]

        resp = await inst.autocomplete(options, focused)
        try:
            resp = list(resp)
        except Exception as e:
            raise ValueError(f"Could not format the returned autocomplete object properly.") from e  # TODO: exceptions

        await inst.interaction.response.autocomplete_result(resp)
