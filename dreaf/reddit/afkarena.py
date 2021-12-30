from __future__ import annotations

import logging
import typing as t

import discord

from .request import Post, Sort, SortTime, get_posts
from dreaf import db


log = logging.getLogger(__name__)

POST_TYPES = {
    "": {
        "colour": discord.Colour.lighter_grey()
    },
    "Guide": {
        "colour": discord.Colour.gold()
    },
    "Info": {
        "colour": discord.Colour.blue()
    },
}


class AFKArenaPost(Post, db.Table):
    def __init__(self, **data):
        super().__init__(**data)
        self.type = data['data']['link_flair_text']
        self.colour = POST_TYPES.get(self.type, POST_TYPES[""])["colour"]
        self.subreddit_icon = "https://styles.redditmedia.com/t5_l00gg/styles/communityIcon_crs2klfox3n51.jpg"
        self.posted = self.is_posted()

    def embed(self):
        embed = super().embed()
        embed.colour = self.colour
        embed.set_footer(text=f"{self.type} by {self.author} on r/{self.subreddit}", icon_url=self.subreddit_icon)
        return embed

    @property
    def is_map_guide(self):
        return self.author == "datguywind" and self.type == "Guide"

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
    async def fetch(cls, *, sort: Sort = Sort.new, time: SortTime = None, limit: int = 25, filter_types=True) -> t.List[AFKArenaPost]:
        posts: t.List[AFKArenaPost] = await get_posts(SESSION, "afkarena", sort=sort, time=time, limit=limit, cls=cls)
        posts: t.List[AFKArenaPost] = await get_posts(SESSION, "afkarena", sort=sort, time=time, limit=limit, cls=cls)
        if filter_types:
            return [p for p in posts if p.type in ("Guide", "Info")]
        return posts

    @staticmethod
    def _select(permalink: str):
        cursor = db.conn.execute(
            """
            SELECT permalink, created, posted
            FROM afkarena_posts
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
                INSERT INTO afkarena_posts(permalink, created, posted) VALUES (?, ?, ?)
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
                INSERT INTO afkarena_posts(permalink, created) VALUES (?, ?)
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
        log.info("Ensuring table exists: afkarena_posts")
        cursor = db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS afkarena_posts (
              permalink TEXT PRIMARY KEY,
              created INTEGER NOT NULL,
              posted BOOLEAN default FALSE
            );
            """
        )
        db.conn.commit()
        cursor.close()
