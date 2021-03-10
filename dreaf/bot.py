import typing as t

import discord
from discord.ext import commands
from . import db, constants
import logging

log = logging.getLogger(__name__)


class DreafBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.presences = False
        super().__init__("", intents=intents, case_insensitive=True)
        self.db = db.conn
        self._global_reaction_triggers: t.Dict[str, t.Callable] = {
            constants.EMOJI_DELETE: self._delete_trigger,
        }

    def run(self):
        super().run(constants.TOKEN)

    @property
    def guild(self) -> discord.Guild:
        return self.get_guild(constants.GUILD_ID)

    @property
    def master(self) -> discord.Role:
        return self.guild.get_role(constants.MASTER_ROLE)

    @property
    def deputy(self) -> discord.Role:
        return self.guild.get_role(constants.DEPUTY_ROLE)

    @property
    def exemplar(self) -> discord.Role:
        return self.guild.get_role(constants.EXEMPLAR_ROLE)

    def is_master(self, member: discord.Member) -> bool:
        return self.master in member.roles

    def is_deputy(self, member: discord.Member) -> bool:
        return self.is_master(member) or self.deputy in member.roles

    def is_exemplar(self, member: discord.Member):
        return self.is_deputy(member) or self.exemplar in member.roles

    async def get_prefix(self, message):
        return [constants.PREFIX, f"<@{self.user.id}> ", f"<@!{self.user.id}> "]

    async def _delete_trigger(self, payload: discord.RawReactionActionEvent):
        channel = self.guild.get_channel(payload.channel_id)
        try:
            msg = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return

        if msg.author.id == self.user.id:
            await msg.delete()

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.user.id:
            return

        handler = self._global_reaction_triggers.get(str(payload.emoji) if not payload.emoji.id else payload.emoji.id)
        if handler:
            await handler(payload)

    def add_cog(self, cog):
        """Adds a "cog" to the bot."""

        if not isinstance(cog, commands.Cog):
            if issubclass(cog, commands.Cog):
                raise TypeError("`cog` must be an instance, not a class.")
            raise TypeError("`cog` must derive from Cog")

        super().add_cog(cog)

    async def on_command_error(self, ctx, exception):
        if isinstance(exception, commands.MissingRequiredArgument):
            await ctx.send("Error: Missing argument.")
            await ctx.send_help(ctx.command)
            return
        if isinstance(exception, commands.BadArgument):
            await ctx.send("Error: Bad argument.")
            await ctx.send_help(ctx.command)
            return
        if isinstance(exception, (commands.CommandNotFound, commands.CheckFailure, commands.DisabledCommand, commands.NoPrivateMessage)):
            return
        log.exception(type(exception).__name__, exc_info=exception)

    async def on_member_join(self, member: discord.Member):
        if member.guild.id != constants.GUILD_ID:
            return

        log_channel: discord.TextChannel = self.guild.get_channel(constants.MEMBER_LOG_CHANNEL)
        if not log_channel:
            return

        await log_channel.send(f"`{member} ({member.id})` **joined** the server. {member.mention}")

    async def on_member_remove(self, member: discord.Member):
        if member.guild.id != constants.GUILD_ID:
            return

        log_channel: discord.TextChannel = self.guild.get_channel(constants.MEMBER_LOG_CHANNEL)
        if not log_channel:
            return

        await log_channel.send(f"`{member} ({member.id})` **left** the server.")
