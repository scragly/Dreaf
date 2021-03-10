from __future__ import annotations

import logging
import typing as t

import aiohttp
import discord

from .request import Post, Sort, SortTime, get_posts
from dreaf import db


log = logging.getLogger(__name__)


SESSION = aiohttp.ClientSession(headers={"Content-Type": "application/json", "charset": "UTF-8"})

LAB_FLARE = ":Text: Arcane Labyrinth"
DISMAL_FLARE = ":Text: Dismal Maze"

MAZE_TYPES = {
    LAB_FLARE: {"colour": discord.Colour.blue()},
    DISMAL_FLARE: {"colour": discord.Colour.red()},
}


class LabPathPost(Post, db.Table):
    def __init__(self, **data):
        super().__init__(**data)
        self.maze = MAZE_TYPES.get(data['data']['link_flair_text'], {"colour": discord.Colour.lighter_grey()})
        self.subreddit_icon = "https://styles.redditmedia.com/t5_1owwk1/styles/communityIcon_oip3qnbqst961.jpg"
        self.posted = self.is_posted()

    def embed(self):
        embed = super().embed()
        embed.colour = self.maze['colour']
        embed._footer['icon_url'] = str(self.subreddit_icon)
        return embed

    async def send(self, channel: discord.TextChannel, *, mark_posted: bool = False):
        await channel.send(embed=self.embed())
        if mark_posted:
            self.set_posted()

    def save(self):
        self._insert(self.permalink, self.created.timestamp())

    def is_posted(self) -> bool:
        result = self._select(self.permalink)
        if not result:
            return False
        _permalink, _created, posted = result
        return bool(posted)

    def set_posted(self):
        self._insert(self.permalink, self.created.timestamp(), True)

    @classmethod
    async def fetch(cls, *, sort: Sort = Sort.new, time: SortTime = None, limit: int = 4) -> t.List[LabPathPost]:
        return await get_posts(SESSION, "Lab_path", sort=sort, time=time, limit=limit, cls=cls)

    @staticmethod
    def _select(permalink: str):
        cursor = db.conn.execute(
            """
            SELECT permalink, created, posted
            FROM labpath_posts
            WHERE permalink = ?
            """,
            [permalink]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _insert(permalink: str, created: int, posted: bool = None):
        if posted is not None:
            cursor = db.conn.execute(
                """
                INSERT INTO labpath_posts(permalink, created, posted) VALUES (?, ?, ?)
                ON CONFLICT(permalink)
                DO UPDATE SET
                  created=excluded.created,
                  posted=excluded.posted;
                """,
                [permalink, created, posted]
            )
        else:
            cursor = db.conn.execute(
                """
                INSERT INTO labpath_posts(permalink, created) VALUES (?, ?)
                ON CONFLICT(permalink)
                DO UPDATE SET
                  created=excluded.created;
                """,
                [permalink, created]
            )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _create_table():
        log.info("Ensuring table exists: labpath_posts")
        cursor = db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS labpath_posts (
              permalink TEXT PRIMARY KEY,
              created INTEGER NOT NULL,
              posted BOOLEAN default FALSE
            );
            """
        )
        db.conn.commit()
        cursor.close()
