from __future__ import annotations

import typing as t

from .commands import PlayerCommands
from .model import Player

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot


def setup(bot: DreafBot):
    bot.add_cog(PlayerCommands(bot))
