from __future__ import annotations

import typing as t

from .commands import RedditCommands

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot


def setup(bot: DreafBot):
    bot.add_cog(RedditCommands(bot))
