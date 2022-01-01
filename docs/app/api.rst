.. currentmodule:: discord

API Reference
===============

The following section outlines the API of enhanced-discord.py's application commands framework.

.. _app_commands_api:

Commands
--------

SlashCommand
~~~~~~~~~~~~~

.. attributetable:: discord.app.SlashCommand

.. autoclass:: discord.app.SlashCommand
    :members:
    :inherited-members:

    .. attribute:: client

        The :class:`.Client` instance that this command is attached to.
    .. attribute:: interaction

        The :class:`.Interaction` instance that called the command.

UserCommand
~~~~~~~~~~~~

.. attributetable:: discord.app.UserCommand

.. autoclass:: discord.app.UserCommand
    :members:
    :inherited-members:
    :exclude-members: autocomplete
    
    .. attribute:: client

        The :class:`.Client` instance that this command is attached to.
    .. attribute:: interaction

        The :class:`.Interaction` instance that called the command.
    .. attribute:: target

        The :class:`.discord.User` instance on which the command was called.

MessageCommand
~~~~~~~~~~~~~~~

.. attributetable:: discord.app.MessageCommand

.. autoclass:: discord.app.MessageCommand
    :members:
    :inherited-members:
    :exclude-members: autocomplete

    .. attribute:: client

        The :class:`.Client` instance that this command is attached to.
    .. attribute:: interaction

        The :class:`.Interaction` instance that called the command.
    .. attribute:: target
    
        The :class:`.Message` instance on which the command was called.

Unknown
---------

Option
~~~~~~~

.. attributetable:: discord.app.Option

.. autoclass:: discord.app.Option
    :members:
    :inherited-members:

AutoCompleteResponse
~~~~~~~~~~~~~~~~~~~~~

.. attributetable:: discord.app.AutoCompleteResponse

.. autoclass:: discord.app.AutoCompleteResponse
    :members: