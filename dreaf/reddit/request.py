from __future__ import annotations

import typing as t
from enum import Enum
from html import unescape
from urllib.parse import urlparse
import logging

import aiohttp
import discord
import pendulum


log = logging.getLogger(__name__)


class Sort(Enum):
    hot = "hot"
    new = "new"
    top = "top"


class SortTime(Enum):
    day = "day"
    week = "week"
    month = "month"
    year = "year"
    all = "all"


class Post:
    def __init__(self, **data):
        self._raw_data = data["data"]
        self.created = pendulum.from_timestamp(data['data']['created_utc'])
        title = unescape(data['data']['title'])
        if len(title) > 250:
            title = f"{title[:250]}..."
        self.title = title
        self.url = data['data'].get('url')
        self.author = data['data']['author']
        self.subreddit = data['data']['subreddit']
        self.permalink = f"https://reddit.com{data['data']['permalink']}"
        text = data['data'].get('selftext', '')
        self.text = f"{text[:240]}.." if len(text) > 242 else text
        self.images = self.gallery_images()

    @property
    def is_image(self) -> bool:
        """Returns True if the post links to an image file."""
        if not self.url:
            return False
        return urlparse(self.url).path.endswith(('png', 'jpg', 'jpeg', 'webp'))

    @property
    def is_gallery(self) -> bool:
        """Returns True if the post links to a reddit image gallery."""
        return "is_gallery" in self._raw_data

    def gallery_images(self) -> t.List[str]:
        """Return a list of image URLs for a gallery post."""
        if not self.is_gallery:
            return []
        gallery_items = [i["media_id"] for i in self._raw_data["gallery_data"]["items"]]
        image_urls = dict()
        for img_id, data in self._raw_data["media_metadata"].items():
            if data["status"] == "valid":
                try:
                    image_urls[img_id] = unescape(data["s"]["u"])
                except KeyError:
                    log.warning("Reddit post encountered bad keys.")
                    log.info(str(self._raw_data))
                    return []
        return [image_urls[i] for i in gallery_items if i in image_urls]

    def embed(self):
        embed = discord.Embed(title=self.title, url=self.permalink, timestamp=self.created)
        embed.set_footer(text=f"Posted by {self.author} on r/{self.subreddit}")
        if self.is_image:
            log.info("is image post")
            embed.set_image(url=self.url)
        elif self.is_gallery:
            log.info(f"is gallery post: {self.url}")
            embed.set_image(url=self.images[0])
            img_links = ", ".join([f"[{i}]({url})" for i, url in enumerate(self.images, start=1)])
            embed.description = f"**[Image Gallery]({self.url})**\n{img_links}"
        elif self.text:
            log.info("is text post")
            embed.description = self.text
        log.info(str(embed.to_dict()))
        return embed

    async def send(self, channel: discord.TextChannel):
        await channel.send(embed=self.embed())

    @classmethod
    async def get_posts(
        cls,
        session: aiohttp.ClientSession,
        subreddit: str,
        *,
        sort: Sort = Sort.new,
        time: SortTime = None,
        limit: int = 25,
    ):
        """Request posts from a subreddit."""
        params = {}
        if time:
            params['t'] = time.value
        if limit:
            params['limit'] = limit

        url = f"https://reddit.com/r/{subreddit}/{sort.value}.json"
        async with session.get(url, params=params) as resp:
            data = await resp.json()

        return [cls(**p) for p in data['data']['children']]

    @classmethod
    async def get_post(cls, session: aiohttp.ClientSession, url):
        """Get a single post from reddit."""
        async with session.get(f"{url}.json") as resp:
            data = await resp.json()

        for item in data[0]["data"]["children"]:
            if item["kind"] != "t3":
                continue
            return cls(**item)


async def get_posts(
    session: aiohttp.ClientSession,
    subreddit: str,
    *,
    sort: Sort = Sort.new,
    time: SortTime = None,
    limit: int = 25,
    cls=Post
):
    """Request posts from a subreddit."""
    params = {}
    if time:
        params['t'] = time.value
    if limit:
        params['limit'] = limit

    url = f"https://reddit.com/r/{subreddit}/{sort.value}.json"
    async with session.get(url, params=params) as resp:
        data = await resp.json()

    return [cls(**p) for p in data['data']['children']]
