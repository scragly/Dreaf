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


class ProxyMember:
    def __init__(self, user: discord.User):
        self.id = user.id
        self.name = user.name
        self.display_name = user.name
        self.avatar_url = user.avatar_url


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
    async def player(self, ctx, player_id: t.Union[discord.Member, int] = None):
        """Show information on a Player."""
        if isinstance(player_id, discord.Member):
            players = Player.get_by_discord_id(player_id.id)
        elif not player_id:
            players = Player.get_by_discord_id(ctx.author.id)
        else:
            player = Player.get(player_id)
            players = [player] if player else []

        if not players:
            await ctx.send(f"No players found.")
            return

        if not isinstance(player_id, discord.Member):
            player = players[0]
            if ctx.guild:
                member = ctx.guild.get_member(player.discord_id)
            else:
                user = ctx.bot.get_user(player.discord_id)
                member = ProxyMember(user) if user else None
            if not member:
                await ctx.send("I can't see that player!")

        else:
            member = player_id

        embed = discord.Embed()
        embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        multi = len(players) > 1
        for player in players:
            if player.main and multi:
                name = f"**__{player.name}__**"
                embed.set_footer(text="Main account is underlined.")
            else:
                name = player.name

            player_id = f"**ID:** {player.game_id}\n"
            level = f"**Level:** {player.level or 'Unknown'}\n"
            server = f"**Server:** {player.server or 'Unknown'}\n"
            embed.add_field(name=name, value=f"{player_id}{level}{server}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(aliases=["verify", "update"])
    async def link(self, ctx, ingame_id: t.Optional[int] = None):
        """Link or update your in-game accounts to your discord account."""
        if not ingame_id:
            player = Player.get_main(ctx.author.id)
            if not player:
                await ctx.send(
                    f"You don't have a main account linked yet."
                    f"Please try again with your in-game ID: `!{ctx.invoked_with} <your_game_id>`."
                )
                return
            ingame_id = player.game_id

        session = redeem_session.RedeemSession.get(ingame_id)
        if session.in_active_session(ctx.author.id):
            await ctx.send("You are already in the middle of verifying.")
            return

        try:
            players = await session.get_users()
        except redeem_session.SessionExpired:
            await session.send_mail()
            try:
                await session.request_verification_code(ctx.bot, ctx.channel, ctx.author)
            except discord.Forbidden:
                await ctx.send(
                    "I need to verify your account, but I'm unable to send a DM. "
                    "Please adjust your privacy settings and try again."
                )
                return
            players = await session.get_users()

        names = ", ".join(p.name for p in players)
        count = len(players)
        s = "s" if count > 1 else ""
        await ctx.send(f"{len(players)} player{s} found and updated:\n{names}")

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
        await ctx.send(f"Error: {error}")
