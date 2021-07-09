from __future__ import annotations

import logging
import typing as t

import discord
from discord.ext import commands

from dreaf import checks, constants
from dreaf.google_forms.gform_prefill import AFKPlayerSurveyForm

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)

AFK_AVATAR = "https://cdn.discordapp.com/icons/441477431501783060/08e30e9cc3a745ce2051af8701ac0b6b.webp?size=256"


class EventCommands(commands.Cog, name="Events"):
    """Commands relating to AFK Arena events."""

    def __init__(self, bot: DreafBot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def survey(self, ctx):
        """Generate a prefilled AFK Player Survey link."""
        form = AFKPlayerSurveyForm(ctx.author)
        embed = discord.Embed()
        embed.set_author(name="AFK Arena Player Survey", url=form.url, icon_url=AFK_AVATAR)
        embed.set_footer(text=f"Prefilled form link for {ctx.author}")
        await ctx.send(embed=embed)

    @checks.is_exemplar()
    @survey.command(name="for")
    async def survey_for_member(self, ctx, member: discord.Member):
        """Generate a prefilled AFK Player Survey link for a given member."""
        form = AFKPlayerSurveyForm(member)
        embed = discord.Embed()
        embed.set_author(name="AFK Arena Player Survey", url=form.url, icon_url=AFK_AVATAR)
        embed.set_footer(text=f"Prefilled form link for {member}")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Detect envelope reaction on survey announcement message."""
        if payload.message_id == 817584118942138400 and payload.emoji.name == "\U0001f4e8":
            form = AFKPlayerSurveyForm(payload.member)
            embed = discord.Embed()
            embed.set_author(name="AFK Arena Player Survey", url=form.url, icon_url=AFK_AVATAR)
            embed.set_footer(text=f"Prefilled form link for {payload.member}")
            try:
                await payload.member.send(embed=embed)
                log.info(f"{payload.member} was sent a survey link.")
            except discord.Forbidden:
                channel = self.bot.get_channel(constants.BOT_SPAM_CHANNEL)
                await channel.send(payload.member.mention, embed=embed)

    async def cog_command_error(self, ctx, error):
        await ctx.send(f"Error: {error}")
