from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import os
import asyncio
import sys
import traceback

from .item import Item
from itertools import groupby

from .view import _ViewWeights as _ModalWeights
from ..interactions import Interaction

if TYPE_CHECKING:
    from ..state import ConnectionState


__all__ = ("Modal",)


class Modal:
    """Represents a UI Modal.

    This object must be inherited to create a UI within Discord.

    .. versionadded:: 2.0

    Parameters
    ------------
    title: :class:`str`
        The title of the modal.
    custom_id: Optional[:class:`str`]
        The ID of the modal that gets received during an interaction.

    Attributes
    ------------
    title: :class:`str`
        The title of the modal.
    custom_id: Optional[:class:`str`]
        The ID of the modal that gets received during an interaction.
    children: List[:class:`Item`]
        The children of the modal.
    """

    def __init__(self, title: str, custom_id: Optional[str] = None) -> None:

        self.title = title
        self.custom_id = custom_id or os.urandom(16).hex()
        self.children: List[Item] = []
        self.__weights = _ModalWeights(self.children)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.title=} {self.custom_id=}>"

    def add_item(self, item: Item):
        if not isinstance(item, Item):
            raise TypeError(f"expected Item not {item.__class__!r}")

        if len(self.children) > 5:
            raise ValueError("Modal can only have a maximum of 5 items")

        self.__weights.add_item(item)
        self.children.append(item)

    def remove_item(self, item: Item):

        try:
            self.children.remove(item)
        except ValueError:
            pass
        else:
            self.__weights.remove_item(item)

    def to_components(self) -> List[Dict[str, Any]]:
        def key(item: Item) -> int:
            return item._rendered_row or 0

        children = sorted(self.children, key=key)
        components: List[Dict[str, Any]] = []
        for _, group in groupby(children, key=key):
            children = [item.to_component_dict() for item in group]
            if not children:
                continue

            components.append(
                {
                    "type": 1,
                    "components": children,
                }
            )

        return components

    async def callback(self, interaction: Interaction):
        """|coro|

        The callback associated with this Modal.

        This can be overriden by subclasses.

        Parameters
        -----------
        interaction: :class:`.Interaction`
            The interaction that submitted this Modal.
        """
        pass

    async def on_error(self, error: Exception, interaction: Interaction):
        """|coro|

        The callback for when an error occurs in the :meth:`callback`.

        The default implementation prints the traceback to stderr.

        Parameters
        -----------
        error: :class:`Exception`
            The error that occurred.
        interaction: :class:`.Interaction`
            The interaction that submitted this Modal.
        """
        print(f"Ignoring exception in modal {self}:", file=sys.stderr)
        traceback.print_exception(error.__class__, error, error.__traceback__, file=sys.stderr)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "custom_id": self.custom_id,
            "components": self.to_components(),
        }


class ModalStore:
    def __init__(self, state: ConnectionState) -> None:
        # (user_id, custom_id) : Modal
        self._modals: Dict[Tuple[int, str], Modal] = {}
        self._state = state

    def add_modal(self, modal: Modal, user_id: int):

        self._modals[(user_id, modal.custom_id)] = modal

    def remove_modal(self, modal: Modal, user_id: int):
        self._modals.pop((user_id, modal.custom_id))

    async def _scheduled_task(self, modal: Modal, interaction: Interaction):
        try:
            await modal.callback(interaction)
        except Exception as e:
            await modal.on_error(e, interaction)

    def dispatch(self, user_id: int, custom_id: str, interaction: Interaction):

        key = (user_id, custom_id)
        modal = self._modals.get(key)
        if modal is None:
            return
        assert interaction.data is not None
        components = [
            component for action_row in interaction.data["components"] for component in action_row["components"]
        ]
        for component in components:
            component_custom_id = component["custom_id"]
            for child in modal.children:
                if child.custom_id == component_custom_id:  # type: ignore
                    child.refresh_state(component)
                    break

        asyncio.create_task(
            self._scheduled_task(modal, interaction), name=f"discord-ui-modal-dispatch-{modal.custom_id}"
        )
        self.remove_modal(modal, user_id)
