from __future__ import annotations

import asyncio
import logging
import typing as t

import discord
from discord.ext import commands

from .lab_path import LabPathPost
from .afkarena import AFKArenaPost
from dreaf import constants, checks

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)


class RedditCommands(commands.Cog, name="Reddit"):
    """Commands to do with Reddit data."""

    def __init__(self, bot: DreafBot):
        self.bot = bot
        self.labpath_task = None
        self.afk_feed_task = None
        self.setup_labpath_task()
        self.setup_afk_feed_task()

    @property
    def labpath_channel(self):
        return self.bot.get_channel(constants.LAB_PATH_CHANNEL)

    def setup_labpath_task(self):
        if self.labpath_task:
            self.labpath_task.cancel()
        self.labpath_task = self.bot.loop.create_task(self.update_labpaths())
        self.labpath_task.add_done_callback(self.task_error)

    async def update_labpaths(self):
        """Update the lab path feed channel every hour."""
        await self.bot.wait_until_ready()

        if not self.labpath_channel:
            log.warning("Labpath channel doesn't exist. Cancelling Lab Path task.")
            return

        while True:
            log.info("Labpath task starting.")
            posts: t.List[LabPathPost] = await LabPathPost.fetch()
            for post in posts:
                if post.posted:
                    continue
                log.info(f"New labpath being posted: {post.permalink}")
                await post.send(self.labpath_channel, mark_posted=True)
            log.info("Labpath task sleeping for 1 hr.")
            await asyncio.sleep(60*60)

    @property
    def afk_feed_channel(self):
        return self.bot.get_channel(constants.AFK_FEED_CHANNEL)

    def setup_afk_feed_task(self):
        if self.afk_feed_task:
            self.afk_feed_task.cancel()
        self.afk_feed_task = self.bot.loop.create_task(self.update_afk_feed())
        self.afk_feed_task.add_done_callback(self.task_error)

    async def update_afk_feed(self):
        """Update the lab path feed channel every hour."""
        await self.bot.wait_until_ready()

        if not self.afk_feed_channel:
            log.warning("AFK feed channel doesn't exist. Cancelling AFK feed task.")
            return

        while True:
            log.info("AFK feed task starting.")
            posts: t.List[AFKArenaPost] = await AFKArenaPost.fetch()
            for post in posts:
                if post.posted:
                    continue
                log.info(f"New AFK feed post: {post.permalink}")
                await post.send(self.afk_feed_channel, mark_posted=True)
            log.info("AFK feed task sleeping for 15 mins.")
            await asyncio.sleep(60*15)

    @checks.is_exemplar()
    @commands.group(invoke_without_command=True)
    async def reset(self, ctx):
        """Reset reddit feed background tasks."""
        self.setup_labpath_task()
        self.setup_afk_feed_task()
        await ctx.send("LabPath and AFK feed tasks have been reset.")

    @checks.is_exemplar()
    @reset.command(name="lab", aliases=["labpath"])
    async def reset_labpath(self, ctx):
        """Reset the LabPath reddit feed task."""
        self.setup_labpath_task()
        await ctx.send("LabPath feed task has been reset.")

    @checks.is_exemplar()
    @reset.command(name="afk", aliases=["afkfeed"])
    async def reset_labpath(self, ctx):
        """Reset the AfK reddit feed task."""
        self.setup_afk_feed_task()
        await ctx.send("AFK feed task has been reset.")

    async def cog_command_error(self, ctx, error):
        await ctx.send(f"Error: {error.original}")

    @staticmethod
    def task_error(task: asyncio.Task):
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            log.info(f"Task '{task.get_coro().__name__}' was cancelled.")
            return

        if exc:
            task.result()
