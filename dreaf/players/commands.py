from __future__ import annotations

import logging
import typing as t

import discord
from discord.ext import commands

from .model import Player

from dreaf import checks
from ..giftcodes import redeem_session

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)


class PlayerCommands(commands.Cog, name="Player Info"):
    """Commands relating to player info."""

    def __init__(self, bot: DreafBot):
        self.bot = bot

    @commands.command()
    async def rank(self, ctx, member: t.Optional[discord.Member] = None):
        """
        Returns the rank the bot sees you as.

        Useful for debugging when commands seem to have a permission issue that doesn't seem right.
        """
        member = member or ctx.author
        if ctx.bot.is_master(member):
            return await ctx.send(f"{member.display_name} is a Guild Master")
        if ctx.bot.is_deputy(member):
            return await ctx.send(f"{member.display_name} is a Guild Deputy")
        if ctx.bot.is_exemplar(member):
            return await ctx.send(f"{member.display_name} is a Exemplar")
        await ctx.send(f"{member.display_name} is a Member")

    @commands.group(invoke_without_command=True)
    async def player(self, ctx, game_id: int):
        """Show information on a Player."""
        player = Player.get(game_id)
        if not player:
            await ctx.send(f"Player with ID {game_id} not found.")
            return

        member = self.bot.guild.get_member(player.discord_id) if player.discord_id else None
        name = player.name or "No name set."
        embed = discord.Embed(
            title=game_id,
            description=f"Name: {name}\nRegistered to: {member.display_name}\nMain: {bool(player.main)}"
        )
        await ctx.send(embed=embed)

    @player.command(name="main")
    async def player_main(self, ctx, game_id: int):
        """Set specific Player as your main account."""
        player = Player.get(game_id)
        if not player:
            await ctx.send(f"Player with ID {game_id} not found.")
            return

        player.main = True
        player.save()
        await ctx.send(f"Player '{player.name or player.game_id}' is now set to main.")

    @checks.is_exemplar()
    @player.command(name="name")
    async def player_name(self, ctx, game_id: int, *, in_game_name: str):
        """Set the in-game name for a specific Player."""
        player = Player.get(game_id)
        if not player:
            await ctx.send(f"Player with ID {game_id} not found.")
            return

        player.set_name(in_game_name)
        await ctx.send(f"Player name is now set to '{in_game_name}'.")

    @commands.group(name="id", invoke_without_command=True)
    async def game_id(self, ctx, member: discord.Member = None):
        """
        Show the ID for yourself or another guild member.

        See your ID: `!id`
        See another's ID: `!id @Scragly`
        """
        member = member or ctx.author
        players = Player.get_by_discord_id(member.id)
        if not players:
            await ctx.send(f"No ID is set yet for {member.display_name}. You can add it with `!id yourgameid`.")
            return

        p = [f"{'*' if p.main else ''}{p.game_id}{' - ' + p.name if p.name else ''}" for p in players]
        embed = discord.Embed(title="Registered IDs", description="\n".join(p))
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        await ctx.send(embed=embed)

    @game_id.group(name="add", aliases=["set", "register"], invoke_without_command=True)
    async def set_game_id(self, ctx, game_id: int, member: discord.Member = None):
        """
        Set a game ID.

        Set your ID: `!id set 12345678`
        Set another's ID: `!id set 12345678 @Scragly`  (Deputy and Guild Leader only)
        """
        if member:
            if not self.bot.is_exemplar(ctx.author):
                await ctx.send("Unable to set the ID of other members, sorry!")
        else:
            member = ctx.author

        player = Player.get(game_id)
        if not player:
            player = Player(game_id, member.id)
            player.save()
            await ctx.send(f"Player '{game_id}' added to {member.display_name}.")
            return
        member = ctx.guild.get_member(player.discord_id)
        member = member.display_name if member else f"User ID {player.discord_id}"
        await ctx.send(f"Player '{game_id}' is already registered to {member}.")

    @game_id.command(name="remove", aliases=["delete"])
    async def remove_game_id(self, ctx, game_id: int):
        """Remove a game ID."""
        player = Player.get(game_id)
        if not player:
            await ctx.send("This ID doesn't exist.")
            return
        is_own = player.discord_id == ctx.author.id
        if is_own or self.bot.is_exemplar(ctx.author):
            player.delete()
            member = ctx.author if is_own else self.bot.guild.get_member(player.discord_id)
            if member:
                await ctx.send(f"ID {game_id} has been removed from {member.display_name}.")
            else:
                await ctx.send(f"ID {game_id} has been removed.")
        else:
            await ctx.send("Unable to delete IDs belonging to other members, sorry!")

    @commands.group(invoke_without_command=True)
    async def verified(self, ctx):
        """Checks if you have a valid code redemption session still."""
        players = Player.get_by_discord_id(ctx.author.id)
        if not players:
            await ctx.send("You don't have an ID registered. You can add it with `!id set youringameid`")
            return
        verified = []
        for player in players:
            session = redeem_session.SESSIONS.get(player.game_id)
            if not session:
                continue
            if await session.is_verified():
                verified.append(player)

        if verified:
            v = "\n".join([f"{p.game_id}" + (f" - {p.name}" if p.name else '') for p in verified])
            await ctx.send(f"The following Player IDs are still verified:\n{v}")
        else:
            await ctx.send("None of your Player IDs are verified currently.")

    @checks.is_deputy()
    @verified.command(name="all")
    async def verified_all(self, ctx):
        sessions = await redeem_session.RedeemSession.all_verified()
        if not sessions:
            await ctx.send("No Player IDs are verified currently.")

        players = [Player.get(s.game_id) for s in sessions]
        verified = []
        for player in players:
            member = self.bot.guild.get_member(player.discord_id)
            discord_name = member.display_name if member else "Not in guild"
            player_name = f"{player.name} ({player.game_id})" if player.name else f"{player.game_id}"
            verified.append(f"{discord_name}: {player_name}")
        verified = "\n".join(verified)
        await ctx.send(f"The following Player IDs are still verified:\n{verified}")

    async def cog_command_error(self, ctx, error):
        await ctx.send(f"Error: {error.original}")
