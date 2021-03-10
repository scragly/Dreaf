from .commands import ItemCommands


def setup(bot):
    bot.add_cog(ItemCommands(bot))
