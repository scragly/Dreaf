from __future__ import annotations

import datetime
import logging
import typing as t
from contextvars import ContextVar

import discord
from discord.ext import commands

from .types import MemberUser

log = logging.getLogger(__name__)


class DreafContext:
    def __init__(self):
        self._ctx_message: ContextVar[t.Optional[discord.PartialMessage]] = ContextVar("message", default=None)
        self._ctx_user: ContextVar[t.Optional[MemberUser]] = ContextVar("user", default=None)
        self._ctx_channel: ContextVar[t.Optional[discord.abc.Messageable]] = ContextVar("channel", default=None)
        self._ctx_guild: ContextVar[t.Optional[discord.Guild]] = ContextVar("guild", default=None)
        self._ctx_cmd: ContextVar[t.Optional[commands.Context]] = ContextVar("cmd_ctx", default=None)
        self._ctx_event: ContextVar[t.Optional[str]] = ContextVar("event", default=None)
        self._ctx_bot: ContextVar[t.Optional[discord.Client]] = ContextVar("bot", default=None)

    def __repr__(self):
        ctx_previews = []
        if self.event:
            ctx_previews.append(f"event='{self.event}'")
        if self.message:
            ctx_previews.append(f"message={self.message.id}")
        if self.user:
            ctx_previews.append(f"user='{self.user}'")
        if self.channel:
            ctx_previews.append(f"channel='{self.channel}'")
        if self.guild:
            ctx_previews.append(f"guild='{self.guild}'")
        if self.cmd_ctx:
            ctx_previews.append(f"command='{self.cmd_ctx.command}'")

        output = ", ".join(ctx_previews)
        return f"<DreafContext {output}>"

    @property
    def message(self) -> t.Optional[discord.PartialMessage]:
        return self._ctx_message.get()

    @property
    def user(self) -> t.Optional[MemberUser]:
        return self._ctx_user.get()

    @property
    def channel(self) -> t.Optional[discord.abc.Messageable]:
        return self._ctx_channel.get()

    @property
    def guild(self) -> t.Optional[discord.Guild]:
        return self._ctx_guild.get()

    @property
    def cmd_ctx(self) -> t.Optional[commands.Context]:
        return self._ctx_cmd.get()

    @property
    def event(self) -> t.Optional[str]:
        return self._ctx_event.get()

    @property
    def bot(self) -> t.Optional[discord.Client]:
        return self._ctx_bot.get()

    def set(self, *, message=None, user=None, channel=None, guild=None, cmd_ctx=None, event=None, bot=None):
        self._ctx_message.set(message)
        self._ctx_user.set(user)
        self._ctx_channel.set(channel)
        self._ctx_guild.set(guild)
        self._ctx_cmd.set(cmd_ctx)
        self._ctx_event.set(event)
        return self

    def set_client(self, client: discord.Client):
        self._ctx_bot.set(client)
        return self

    def _ensure_member(self, user, *, guild: discord.Guild = None, guild_id: int = None) -> t.Optional[MemberUser]:
        if isinstance(user, discord.Member):
            return user

        if guild_id:
            guild = self.bot.get_guild(guild_id)

        if guild:
            user_id = getattr(user, "id", user)
            return guild.get_member(user_id)

        if isinstance(user, int):
            user: discord.User = self.bot.get_user(user)

        if not user:
            return None

        member_instances = [guild.get_member(user.id) for guild in self.bot.guilds if guild.get_member(user.id)]
        if len(member_instances) == 1:
            return member_instances[0]

        return user

    # region: Event Hooks

    def event_hook(self, event_name: str, *args, **_kwargs):
        self.set(event=event_name)
        hook = getattr(self, f"{event_name}_hook", None)
        if hook:
            hook(*args)

    def message_hook(self, message: discord.Message, *_args):
        self.set(
            message=discord.PartialMessage(channel=message.channel, id=message.id),
            user=self._ensure_member(message.author),
            channel=message.channel,
            guild=message.guild,
        )

    message_delete_hook = message_hook
    message_edit_hook = message_hook

    def raw_message_delete_hook(self, payload: discord.RawMessageDeleteEvent):
        if payload.cached_message:
            channel = payload.cached_message.channel
            guild = payload.cached_message.guild
            user = self._ensure_member(payload.cached_message.author, guild=guild)
        else:
            channel = self.bot.get_channel(payload.channel_id)
            user = None
            guild = getattr(channel, "guild", None)

        self.set(
            message=discord.PartialMessage(channel=channel, id=payload.message_id),
            user=user,
            channel=channel,
            guild=guild
        )

    raw_message_edit_hook = raw_message_delete_hook

    def typing_hook(self, channel: discord.abc.Messageable, user: MemberUser, _when: datetime.datetime):
        self.set(
            channel=channel,
            user=self._ensure_member(user),
            guild=getattr(channel, "guild", None),
        )

    def reaction_add_hook(self, reaction: discord.Reaction, user: discord.User):
        self.set(
            message=discord.PartialMessage(channel=reaction.message.channel, id=reaction.message.id),
            user=self._ensure_member(user),
            channel=reaction.message.channel,
            guild=reaction.message.guild,
        )

    reaction_remove_hook = reaction_add_hook

    def raw_reaction_add_hook(self, payload: discord.RawReactionActionEvent):
        channel = self.bot.get_channel(payload.channel_id)
        self.set(
            message=discord.PartialMessage(channel=channel, id=payload.message_id),
            user=self._ensure_member(payload.user_id, guild_id=payload.guild_id),
            channel=channel,
            guild=self.bot.get_guild(payload.guild_id) if payload.guild_id else None,
        )

    raw_reaction_remove_hook = raw_reaction_add_hook

    def reaction_clear_hook(self, message: discord.Message, _reaction: discord.Reaction):
        self.set(
            message=discord.PartialMessage(channel=message.channel, id=message.id),
            channel=message.channel,
            guild=message.guild,
        )

    def raw_reaction_clear_hook(self, payload: discord.RawReactionClearEvent):
        channel = self.bot.get_channel(payload.channel_id)
        self.set(
            message=discord.PartialMessage(channel=channel, id=payload.message_id),
            channel=channel,
            guild=self.bot.get_guild(payload.guild_id) if payload.guild_id else None,
        )

    raw_reaction_clear_emoji_hook = raw_reaction_clear_hook

    def reaction_clear_emoji_hook(self, reaction: discord.Reaction):
        self.set(
            message=discord.PartialMessage(channel=reaction.message.channel, id=reaction.message.id),
            channel=reaction.message.channel,
            guild=reaction.message.guild,
        )

    def guild_channel_update_hook(self, channel: discord.abc.GuildChannel, *_args):
        self.set(channel=channel, guild=channel.guild)

    guild_channel_create_hook = guild_channel_update_hook
    guild_channel_delete_hook = guild_channel_update_hook
    guild_channel_pins_update_hook = guild_channel_update_hook
    webhooks_update_hook = guild_channel_update_hook

    def guild_update_hook(self, guild: discord.Guild, *_args):
        self.set(guild=guild)

    guild_join_hook = guild_update_hook
    guild_remove_hook = guild_update_hook
    guild_integrations_update_hook = guild_update_hook
    guild_emojis_update_hook = guild_update_hook
    guild_available_hook = guild_update_hook
    guild_unavailable_hook = guild_update_hook

    def member_update_hook(self, member: discord.Member, *_args):
        self.set(
            user=member,
            guild=member.guild,
        )

    member_join_hook = member_update_hook
    member_remove_hook = member_update_hook

    def guild_role_update_hook(self, role: discord.Role, *_args):
        self.set(guild=role.guild)

    guild_role_create_hook = guild_role_update_hook
    guild_role_delete_hook = guild_role_update_hook

    def member_ban_hook(self, guild: discord.Guild, user: MemberUser):
        self.set(user=user, guild=guild)

    member_unban_hook = member_ban_hook

    def command_hook(self, cmd_ctx: commands.Context):
        self.set(
            message=discord.PartialMessage(channel=cmd_ctx.channel, id=cmd_ctx.message.id),
            user=cmd_ctx.author,
            channel=cmd_ctx.channel,
            guild=cmd_ctx.guild,
            cmd_ctx=cmd_ctx,
        )

    # endregion


ctx = DreafContext()
