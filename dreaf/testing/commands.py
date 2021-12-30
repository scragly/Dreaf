from __future__ import annotations

import io
import logging
import textwrap
import traceback
import typing as t
from contextlib import redirect_stdout, suppress

import discord
from discord.ext import commands

from dreaf import checks, ctx as dctx

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)

packs = {
    "usd": (99.99, "$", "USD"),
    "cad": (139.99, "$", "CAD"),
    "aud": (159.99, "$", "AUD"),
    "sar": (449.99, "", "riyals"),
    "gbp": (109.99, "£"),
    "mxn": (2500, "$", "MXN"),
    "pln": (479.99, "", "złoty"),
    "eur": (99.99, "€", "EUR"),
    "eur-android": (109.99, "€", "EUR"),
}


def currency_pack(currency: str) -> t.Optional[t.Tuple[float, t.Optional[str], str]]:
    currency = currency.casefold()
    if currency not in packs:
        return None
    value, symbol, currency = packs[currency]
    return value, symbol, currency


ftp_vip = {
    0: 0,
    20: 100,
    40: 300,
    70: 1000,
    80: 2000,
    100: 4000,
    120: 7000,
    140: 10000,
    150: 14000,
    170: 20000,
    200: 30000,
}


def free_vip(level: int):
    key = max(i for i in ftp_vip if i < level)
    return ftp_vip[key]


class TestCommands(commands.Cog, name="Gift Codes"):
    """Commands for testing the bot."""

    def __init__(self, bot: DreafBot):
        self.bot = bot
        self._last_result = None

    @staticmethod
    def cleanup_code(content: str):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @checks.is_owner()
    @commands.command(category='Developer', name='eval')
    async def _eval(self, ctx: commands.Context, *, body: str):
        """Evaluates provided python code"""

        env = {
            'dctx': dctx,
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '__': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']

        # noinspection PyBroadException
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()

            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            with suppress(discord.Forbidden):
                await ctx.message.add_reaction('\u2705')

            if ret is None:
                if value:
                    await ctx.send(f"```\n{value}\n```")
            else:
                self._last_result = ret
                await ctx.send(f"```\n{value}{ret}\n```")

    @commands.command()
    async def vip(self, ctx, player_level: int, vip_points: int, *, currency: str = "usd"):
        """
        Estimates how much you've spent ingame on your account.

        Supports currencies:
         - USD (default)
         - CAD
         - AUD
         - GBP
         - SAR
         - EUR
         - EUR-ANDROID
         - MXN
         - PLN
        """
        data = currency_pack(currency)
        if not data:
            return ctx.send("That currency is not found.")

        price, symbol, currency = currency_pack(currency)
        value = round((vip_points-free_vip(player_level))/(7600/price))
        await ctx.send(f"Estimated spent: {symbol}{value} {currency}")
