from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import os
from .item import Item
from ..enums import TextInputStyle
from ..utils import MISSING
from ..components import TextInput as TextInputComponent


__all__ = ("TextInput",)

if TYPE_CHECKING:
    from ..types.components import TextInput as TextInputPayload
    from ..types.interactions import (
        ComponentInteractionData,
    )


class TextInput(Item):
    """
    Represents a UI Text Input Field.

    .. versionadded:: 2.0

    Parameters
    ------------
    label: :class:`str`
        The label of the text input.
    placeholder: Optional[:class:`str`]
        The placeholder text that is shown if nothing is typed, if any.
    min_length: Optional[:class:`int`]
        The minimum length of the text input. Defaults to `0`.
    max_length: Optional[:class:`int`]
        The maximum length of the text input.
    style: :class:`discord.TextInputStyle`
        The style of the text input.
    custom_id: Optional[:class:`str`]
        The ID of the text input that gets received during an interaction.
    row: Optional[:class:`int`]
        The row of the text input.
    required: Optional[:class:`bool`]
        Whether the text input is required. Defaults to True.
    value: Optional[:class:`str`]
        The pre filled value of the text input.
    """

    def __init__(
        self,
        label: str,
        placeholder: Optional[str] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        style: TextInputStyle = TextInputStyle.short,
        custom_id: Optional[str] = MISSING,
        row: Optional[int] = None,
        required: Optional[bool] = True,
        value: Optional[str] = None,
    ):

        super().__init__()
        custom_id = os.urandom(16).hex() if custom_id is MISSING else custom_id
        self._received_value = ""
        self._underlying = TextInputComponent._raw_construct(
            custom_id=custom_id,
            label=label,
            placeholder=placeholder,
            min_length=min_length,
            max_length=max_length,
            style=style,
            required=required,
            value=value,
        )
        self.row = row

    @property
    def width(self) -> int:
        return 5

    @property
    def custom_id(self) -> str:
        """:class:`str`: The ID of the text input that gets received during an interaction."""
        return self._underlying.custom_id

    @custom_id.setter
    def custom_id(self, value: str):
        if not isinstance(value, str):
            raise TypeError("custom_id must be None or str")

        self._underlying.custom_id = value

    @property
    def placeholder(self) -> Optional[str]:
        """Optional[:class:`str`]: The placeholder text that is shown if nothing is typed, if any."""
        return self._underlying.placeholder

    @placeholder.setter
    def placeholder(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise TypeError("placeholder must be None or str")

        self._underlying.placeholder = value

    @property
    def label(self) -> str:
        """:class:`str`: The label of the text input."""
        return self._underlying.label

    @label.setter
    def label(self, value: str):
        if not isinstance(value, str):
            raise TypeError("label must be str")

        self._underlying.label = value

    @property
    def min_length(self) -> Optional[int]:
        """Optional[:class:`int`]: The minimum length of the text input. Defaults to `0`."""
        return self._underlying.min_length

    @min_length.setter
    def min_length(self, value: Optional[int]):
        if value is not None and not isinstance(value, int):
            raise TypeError("min_length must be None or int")

        self._underlying.min_length = value

    @property
    def max_length(self) -> Optional[int]:
        """Optional[:class:`int`]: The maximum length of the text input."""
        return self._underlying.max_length

    @max_length.setter
    def max_length(self, value: Optional[int]):
        if value is not None and not isinstance(value, int):
            raise TypeError("max_length must be None or int")

        self._underlying.max_length = value

    @property
    def style(self) -> TextInputStyle:
        """:class:`discord.TextInputStyle`: The style of the text input."""
        return self._underlying.style

    @style.setter
    def style(self, value: TextInputStyle):
        if not isinstance(value, TextInputStyle):
            raise TypeError("style must be TextInputStyle")

        self._underlying.style = value

    @property
    def required(self) -> bool:
        """Optional[:class:`bool`] Whether the text input is required. Defaults to true."""
        return self._underlying.required

    @required.setter
    def required(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError("required must be bool")

        self._underlying.required = value

    @property
    def value(self) -> Optional[str]:
        """Optional[:class:`str`] The pre filled value of the text input."""
        return self._received_value or self._underlying.value

    @value.setter
    def value(self, value: Optional[str]):
        if value is not None and not isinstance(value, str):
            raise TypeError("value must be None or str")
        self._underlying.value = value

    def to_component_dict(self) -> TextInputPayload:
        return self._underlying.to_dict()

    def refresh_state(self, data) -> None:
        self._received_value = data["value"]
