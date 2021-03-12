from __future__ import annotations

import io
import textwrap
import traceback
import typing as t
from contextlib import redirect_stdout, suppress

import discord
from discord.ext import commands

from dreaf import checks, ctx as dctx

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot


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
