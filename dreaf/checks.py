import typing as t

import discord
from discord.ext import commands


def _ensure_member(ctx) -> t.Optional[discord.Member]:
    return ctx.author if ctx.guild else ctx.bot.guild.get_member(ctx.author.id)


def is_owner():
    async def predicate(ctx):
        return await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def is_master():
    async def predicate(ctx):
        author = _ensure_member(ctx)
        return ctx.bot.is_master(author) if author else False
    return commands.check(predicate)


def is_deputy():
    async def predicate(ctx):
        author = _ensure_member(ctx)
        return ctx.bot.is_deputy(author) if author else False
    return commands.check(predicate)


def is_exemplar():
    async def predicate(ctx):
        author = _ensure_member(ctx)
        return ctx.bot.is_exemplar(author) if author else False
    return commands.check(predicate)
