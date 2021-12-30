from __future__ import annotations

from .commands import UserCommands
from .model import User, Player


def setup(bot):
    bot.add_cog(UserCommands(bot))
