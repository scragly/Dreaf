from .model import GiftCode
from .commands import GiftCodeCommands


def setup(bot):
    bot.add_cog(GiftCodeCommands(bot))
