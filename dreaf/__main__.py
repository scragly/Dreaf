from .bot import DreafBot

bot = DreafBot()

bot.load_extension("dreaf.testing")
# bot.load_extension("dreaf.giftcodes")
# bot.load_extension("dreaf.players")
# bot.load_extension("dreaf.afk_events")
# bot.load_extension("dreaf.items")
bot.load_extension("dreaf.reddit")
bot.load_extension("dreaf.commands.hero_images")

bot.run()
