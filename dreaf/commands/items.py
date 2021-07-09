from __future__ import annotations

import logging
import typing as t

import discord
from discord.ext import commands

from .model import Item

from dreaf import checks

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)


class ItemCommands(commands.Cog, name="Item Info"):
    """Commands relating to player info."""

    def __init__(self, bot: DreafBot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def item(self, ctx, *, item: Item):
        """Item information."""
        embed_kwargs = {'title': item.name.title(), 'colour': discord.Colour.blue()}

        if item.description:
            embed_kwargs['description'] = item.description

        embed = discord.Embed(**embed_kwargs)

        if item.emoji_id:
            emoji: discord.Emoji = self.bot.get_emoji(item.emoji_id)
            embed.set_thumbnail(url=emoji.url)

        await ctx.send(embed=embed)

    @item.command()
    async def list(self, ctx, *, search_name: str = None):
        items = Item.get_all(search_name)
        if not items:
            await ctx.send("No items found.")
            return

        output = [f"{self.bot.get_emoji(item.emoji_id) if item.emoji_id else ' — '} {item.name.title()}" for item in items]
        await ctx.send("\n".join(output))

    @checks.is_exemplar()
    @item.command(name="add", aliases=["edit"])
    async def add_item(self, ctx, name: str, emoji: discord.Emoji = None, *, description: str = None):
        """Add or edit an item in the database."""
        item = Item(name, description, emoji.id if emoji else None)
        dirty = item.is_dirty()
        if dirty is None:
            item.save()
            await ctx.send(f"Item {item.name.title()} has been added.")
        elif dirty is True:
            item.save()
            await ctx.send(f"Item {item.name.title()} has been edited.")
        else:
            await ctx.send(f"Item {item.name.title()} has not been changed.")

    @checks.is_exemplar()
    @item.command(name="remove", aliases=["delete"])
    async def remove_item(self, ctx, item: Item):
        """Remove an item from the database."""
        item.delete()
        await ctx.send(f"Item {item.name} has been deleted.")

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send("Argument not found.")
        else:
            await ctx.send(f"Error: {error}")


def setup(bot):
    bot.add_cog(ItemCommands(bot))
