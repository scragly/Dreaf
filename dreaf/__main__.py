from .bot import DreafBot

bot = DreafBot()


@bot.check
async def only_dev(ctx):
    return ctx.author.id == 174764205927432192


bot.load_extension("dreaf.testing")
# bot.load_extension("dreaf.giftcodes")
# bot.load_extension("dreaf.players")
# bot.load_extension("dreaf.afk_events")
# bot.load_extension("dreaf.items")
# bot.load_extension("dreaf.reddit")
# bot.load_extension("dreaf.hero_img")

bot.run()
