from __future__ import annotations

import logging
import typing as t

from discord.ext import commands

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)


class UserCommands(commands.Cog, name="Users"):
    """Commands for managing users."""

    def __init__(self, bot):
        self.bot: DreafBot = bot
