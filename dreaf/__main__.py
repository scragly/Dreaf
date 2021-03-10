from .bot import DreafBot

bot = DreafBot()

bot.load_extension("dreaf.testing")
bot.load_extension("dreaf.giftcodes")
bot.load_extension("dreaf.players")
bot.load_extension("dreaf.events")
bot.load_extension("dreaf.items")
bot.load_extension("dreaf.reddit")

bot.run()
