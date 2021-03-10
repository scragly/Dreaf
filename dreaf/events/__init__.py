from .commands import EventCommands


def setup(bot):
    bot.add_cog(EventCommands(bot))
