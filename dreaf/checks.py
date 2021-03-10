import typing as t

from discord.ext import commands

if t.TYPE_CHECKING:
    from .bot import DreafBot


def is_owner():
    async def predicate(ctx):
        return await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def is_master():
    async def predicate(ctx):
        return ctx.bot.is_master(ctx.author)
    return commands.check(predicate)


def is_deputy():
    async def predicate(ctx):
        return ctx.bot.is_deputy(ctx.author)
    return commands.check(predicate)


def is_exemplar():
    async def predicate(ctx):
        return ctx.bot.is_exemplar(ctx.author)
    return commands.check(predicate)
