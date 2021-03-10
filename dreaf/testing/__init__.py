from .commands import TestCommands


def setup(bot):
    bot.add_cog(TestCommands(bot))
