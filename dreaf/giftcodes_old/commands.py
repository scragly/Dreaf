from __future__ import annotations

import asyncio
import logging
import re
import typing as t

import discord
import pendulum
from discord.ext import commands

from . import redeem_session
from .model import GiftCode
from .redeem_session import RedeemSession, SessionExpired
from .. import checks, constants
from ..items.model import Item
from ..players import Player

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)

AFK_FEED_CODE_PATTERN = re.compile(r".?```\s*(\w+[^\s]\w+)\s*```")
AFK_FEED_DATETIME_PATTERN = re.compile(r"(\d\d\d\d/\d\d/\d\d \d\d:\d\d:\d\d) UTC")


class GiftReward:
    @classmethod
    async def convert(cls, ctx, arg):
        item = Item.get(arg)
        if item:
            return item

        try:
            emoji = await commands.EmojiConverter().convert(ctx, arg)
        except commands.EmojiNotFound:
            raise commands.BadArgument("Couldn't find item.")

        item = Item.get_by_emoji(emoji)
        if item:
            return item

        raise commands.BadArgument("Couldn't find item.")


class GiftCodeCommands(commands.Cog, name="Gift Codes"):
    """Commands relating to AFK Arena redemption codes."""

    def __init__(self, bot: DreafBot):
        self.bot = bot
        self._gift_emoji = "\U0001f381"
        task = bot.loop.create_task(self.update_code_message())
        task.add_done_callback(self.task_error)

    @property
    def code_message_id(self):
        m_id = constants.persistent_globals.get("code_message_id")
        return int(m_id) if m_id else None

    @code_message_id.setter
    def code_message_id(self, value):
        constants.persistent_globals["code_message_id"] = value

    async def update_code_message(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(constants.CODE_CHANNEL)
        if not channel:
            log.warning("Code channel not found.")
            return

        message_id = self.code_message_id
        embed = self.code_list_embed(GiftCode.get_all(), global_list=True)

        if not message_id:
            log.info("Code message ID not found.")
            await self.create_code_message(channel, embed)
            return

        try:
            message: discord.Message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await self.create_code_message(channel, embed)
        else:
            await message.edit(embed=embed)
            await message.add_reaction(self._gift_emoji)

    async def create_code_message(self, channel, embed):
        log.info("Creating new message.")
        message: discord.Message = await channel.send(embed=embed)
        await message.add_reaction(self._gift_emoji)
        self.code_message_id = message.id
        return

    @commands.group(invoke_without_command=True)
    async def code(self, ctx, code: GiftCode):
        """See what info the database has on a given gift code."""
        rewards = code.rewards_formatted(self.bot)
        embed = discord.Embed(
            description=rewards,
            title=code.code,
            timestamp=code.expiry if code.expiry else discord.Embed.Empty,
            colour=discord.Colour.red() if code.is_expired() else discord.Colour.green()
        )
        if code.expiry:
            embed.set_footer(text="Gift Code Expiry")
        else:
            embed.set_footer(text="Expiry Unknown")
        await ctx.send(embed=embed)

    @code.group(name="expires", aliases=["expiry", "expire"])
    async def code_expiry(self, ctx, code: GiftCode, *, expiry: pendulum.parse):
        """Set the expiry for an existing code."""
        code.set_expiry(expiry)

        rewards = code.rewards_formatted(self.bot)
        embed = discord.Embed(
            description=rewards,
            title=code.code,
            timestamp=code.expiry if code.expiry else discord.Embed.Empty,
            colour=discord.Colour.red() if code.is_expired() else discord.Colour.green()
        )
        if code.expiry:
            embed.set_footer(text="Gift Code Expiry")
        else:
            embed.set_footer(text="Expiry Unknown")
        await ctx.send(embed=embed)

    @code.group(name="add", aliases=["new", "edit"], invoke_without_command=True)
    async def code_add(self, ctx, code: str, *, expiry: t.Optional[pendulum.parse]):
        """Add a new code."""
        new_code = GiftCode(code, expiry.timestamp() if expiry else None)

        existing_code = GiftCode.get(code)
        if existing_code:

            if existing_code.expiry == expiry:
                await ctx.send(f"Code '{code}' already exists")
                return

            new_code.save()
            await ctx.send(f"Code '{code}' has been updated.")
            return

        new_code.save()

        player_ids = [p.game_id for p in Player.get_by_discord_id(ctx.author.id)]
        redeemed_for_author = False

        for session in redeem_session.SESSIONS.values():
            if await session.is_verified():
                results = await session.redeem_codes(new_code)
                success = any(code in good_codes for good_codes in results.values())
                if not success:
                    await ctx.send("Code is not valid.")
                    return

                if session.game_id in player_ids:
                    redeemed_for_author = True

        if redeemed_for_author:
            await ctx.send(f"Code '{code}' has been added and automatically redeemed to your account.")
        else:
            await ctx.send(f"Code '{code}' has been added.")

        task = asyncio.create_task(self.update_code_message())
        task.add_done_callback(self.task_error)

    @code.group(name="reward", invoke_without_command=True)
    async def code_reward(self, ctx, code: GiftCode, item: Item, qty: int):
        """Add a reward to an existing code."""
        code.add_reward(item, qty)
        emoji = f"{self.bot.get_emoji(item.emoji_id)} " if item.emoji_id else ''
        await ctx.send(f"Added {qty} x {emoji}{item.name.title()} to gift code '{code}'")
        task = asyncio.create_task(self.update_code_message())
        task.add_done_callback(self.task_error)

    @code_reward.command(name="remove", aliases=["delete"])
    async def code_reward_remove(self, ctx, code: GiftCode, item: Item):
        """Remove a reward from a code."""
        code.remove_reward(item)
        await ctx.send(f"Removed {item.name.title()} from gift code '{code}'")
        task = asyncio.create_task(self.update_code_message())
        task.add_done_callback(self.task_error)

    def code_list_embed(
        self,
        codes: t.List[GiftCode],
        player: t.Optional[Player] = None,
        *,
        global_list: bool = False
    ) -> discord.Embed:
        member = None
        embed = discord.Embed(title="Active Gift Codes")
        for code in codes:
            emoji = ""
            if player:
                member = self.bot.guild.get_member(player.discord_id)
                emoji = "✓ " if code.is_redeemed(player.game_id) else ""
            embed.add_field(name=f"{emoji}{code.code}", value=code.rewards_formatted(self.bot, verbose=global_list), inline=False)
        for_str = f" for {member.display_name} ({player.game_id})" if player else ""
        if global_list:
            embed.set_footer(text="Click reaction to redeem.")
        else:
            embed.set_footer(text=f"Code List{for_str}")
        return embed

    @code.command(name="list")
    async def code_list(self, ctx, member: discord.Member = None):
        """Show all active codes."""
        codes = GiftCode.get_all()
        if not codes:
            await ctx.send("No active codes.")
            return

        member = member or ctx.author
        players = Player.get_by_discord_id(member.id)
        if len(players) > 1:
            player = Player.get_main(ctx.author.id)
            if not player:
                player = players[0]
        else:
            player = players[0]

        await ctx.send(embed=self.code_list_embed(codes, player))

    @code.command(name="noexpiry")
    async def code_no_expiry(self, ctx):
        """Show all codes that are missing an expiry."""
        codes = [c for c in GiftCode.get_all() if not c.expiry]
        embed = discord.Embed(title="Active Gift Codes")
        for code in codes:
            embed.add_field(name=f"{code.code}", value=code.rewards_formatted(self.bot), inline=False)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def redeem(self, ctx, new_code: str = None):
        """Redeem gift codes."""
        if new_code and not GiftCode.get(new_code):
            GiftCode(new_code).save()

        codes = GiftCode.get_all()
        if not codes:
            await ctx.send("No active codes.")

        players = Player.get_by_discord_id(ctx.author.id)
        if not players:
            log.info(f"Requesting Game ID from {ctx.author}")

            def check(m: discord.Message):
                if not isinstance(m.channel, discord.DMChannel):
                    return False
                if m.channel.recipient != m.author:
                    return False
                if m.author != ctx.author:
                    return False
                return True

            try:
                message = await ctx.bot.wait_for('message', check=check, timeout=600)
                log.info(f"Received response of {message.content}")
            except asyncio.TimeoutError:
                await ctx.author.send("Prompt has timed out. Please try setting an id instead with `!id set <game_id>`.")
                log.info(f"Game ID prompt has timed out for {ctx.author}")
                return

            try:
                game_id = int(message.content)
            except ValueError:
                await ctx.author.send(
                    "The response you gave doesn't appear to be correct. "
                    "Please try setting an id instead with `!id set <game_id>`."
                )
                log.info(f"Game ID prompt for {ctx.author} failed.")
                return

            player = Player(game_id, ctx.author.id)
            player.save()
            players = [player]

        if len(players) > 1:
            player = Player.get_main(ctx.author.id)
            if not player:
                player = players[0]
        else:
            player = players[0]

        game_id = player.game_id
        session = RedeemSession.get(game_id)
        if session.in_active_session(ctx.author.id):
            await ctx.send("You are already in the middle of verifying.")
            return
        force = hasattr(ctx, 'ignore_expiry')
        try:
            results = await session.redeem_codes(*codes, ignore_expiry=force)
        except SessionExpired:
            if hasattr(ctx, 'dont_verify'):
                await ctx.send("Session isn't verified, stopping.")
                return
            async with ctx.typing():
                await session.send_mail()
                try:
                    await session.request_verification_code(ctx.bot, ctx.channel, ctx.author)
                except discord.Forbidden:
                    await ctx.send(
                        "I need to verify your account, but I'm unable to send a DM. "
                        "Please adjust your privacy settings and try again."
                    )
                    return
            results = await session.redeem_codes(*codes, ignore_expiry=force)

        successful_codes = set()
        for player, code_list in results.items():
            codes.extend(code_list)

        success_count = len(successful_codes)
        if success_count:
            s = "s" if success_count > 1 else ""
            embed = discord.Embed(title=f"{success_count} Code{s} Redeemed", colour=discord.Colour.green())
            for code in results["success"]:
                embed.add_field(name=f"{code.code}", value=code.rewards_formatted(self.bot))
        else:
            embed = discord.Embed(title=f"No Codes Redeemed.", colour=discord.Colour.red(), description="You're up to date!")

        embed.set_footer(text=f"Redemptions for {ctx.author.display_name} ({game_id})")
        await ctx.send(embed=embed)

    @checks.is_deputy()
    @redeem.command(name="other")
    async def redeem_other(self, ctx, member: discord.Member):
        """Invoke redeem for another member."""
        self.redeem: commands.Command
        ctx.author = member
        ctx.dont_verify = True
        await self.redeem.invoke(ctx)

    @checks.is_deputy()
    @redeem.command(name="force")
    async def redeem_forced(self, ctx):
        self.redeem: commands.Command
        ctx.ignore_expiry = True
        await self.redeem.invoke(ctx)

    async def cog_command_error(self, ctx, error):
        await ctx.send(f"Error: {error}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != constants.AFK_CODE_FEED_CHANNEL:
            return

        if message.author.id == self.bot.user.id:
            return

        content = message.clean_content
        match = AFK_FEED_CODE_PATTERN.search(content)
        if not match:
            await message.add_reaction("\u274e")  # CROSS MARK
            return

        code = match.group(1).strip()

        match = AFK_FEED_DATETIME_PATTERN.search(content)
        date = pendulum.parse(match.group(1).strip()) if match else None

        await message.add_reaction("\u2705")  # CHECK MARK

        timestamp = date.int_timestamp if date else None
        existing_code = GiftCode.get(code)
        if existing_code and date:
            if existing_code.expiry == date:
                await message.channel.send(f"Detected existing code '{code}'.")
                return
            else:
                await message.channel.send(f"Detected existing code '{code}'. Updated expiry to {date.to_formatted_date_string()}.")
                existing_code.expiry = timestamp
                existing_code.save()
                return

        code = GiftCode(code, timestamp)
        code.save()

        for session in redeem_session.SESSIONS.values():
            if await session.is_verified():
                await session.redeem_codes(code)

        # await message.channel.send(f"New code '{code}' was found with expiry {date.to_formatted_date_string()})")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Detect gift reaction on codes message to start redemptions."""
        if payload.message_id != self.code_message_id:
            return
        if payload.emoji.name != self._gift_emoji:
            return
        if payload.user_id == self.bot.user.id:
            return

        log.info(f"{payload.member} used gift redemption reaction.")
        log_channel = self.bot.guild.get_channel(constants.CODE_LOGS_CHANNEL)

        await self.bot.http.remove_reaction(constants.CODE_CHANNEL, self.code_message_id, payload.emoji.name, payload.user_id)

        try:
            codes = GiftCode.get_all()
            if not codes:
                await payload.member.send("No active codes.")
                return

            players = Player.get_by_discord_id(payload.user_id)
            if not players:
                await payload.member.send("You haven't registered an ID. You can add one with `!id set <game_id>`.")
                return

            if len(players) > 1:
                player = Player.get_main(payload.user_id)
                if not player:
                    player = players[0]
            else:
                player = players[0]

            game_id = player.game_id
            session = RedeemSession.get(game_id)
            if session.in_active_session(payload.user_id):
                return

            log_msg = None
            if log_channel:
                log_msg = await log_channel.send(f"{payload.member} is redeeming giftcodes.")

            try:
                results = await session.redeem_codes(*codes)
            except SessionExpired:
                await session.send_mail()
                await session.request_verification_code(self.bot, payload.member, payload.member)
                results = await session.redeem_codes(*codes)

            await self.update_code_message()

            success_count = sum(len(good_codes) for good_codes in results.values())
            if success_count:
                s = "s" if success_count > 1 else ""
                embed = discord.Embed(title=f"{success_count} Code{s} Redeemed", colour=discord.Colour.green())
                log.info(f"{success_count} codes redeemed for {payload.member}: {results}")
                result_output = ""
                for player, good_codes in results.items():
                    player_result = ""
                    if not good_codes:
                        continue
                    player_result += ", ".join(c.code for c in good_codes)
                    result_output += f"\n**{player.name}**\n{player_result}"
                    embed.add_field(name=player.name, value=player_result)
                if log_msg:
                    await log_msg.edit(content=f"{payload.member} redeemed {success_count} giftcode{s}. \n{result_output}")
            else:
                log.info(f"No codes to redeem for {payload.member}")
                embed = discord.Embed(
                    title=f"No Codes Redeemed.",
                    colour=discord.Colour.red(),
                    description="You're up to date!"
                )
                if log_msg:
                    asyncio.create_task(log_msg.edit(content=f"{payload.member} redeemed 0 giftcodes, as they were up to date."))

            embed.set_footer(text=f"Redemptions for {payload.member.display_name} ({game_id})")
            await payload.member.send(embed=embed)

        except discord.Forbidden:
            log.info("Redemption failed due to DMs not being enabled.")
            await self.bot.get_channel(constants.BOT_SPAM_CHANNEL).send(
                f"{payload.member.mention}\n"
                "I need to verify your account, but I'm unable to send a DM. "
                "Please adjust your privacy settings and try again."
            )

    @commands.command()
    async def match(self, ctx, *, text):
        match = AFK_FEED_CODE_PATTERN.match(text)
        await ctx.send(f"{match}")

    @staticmethod
    def task_error(task: asyncio.Task):
        if task.exception():
            task.result()
