from .commands import HeroImg


def setup(bot):
    bot.add_cog(HeroImg(bot))
