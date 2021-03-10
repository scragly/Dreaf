from enum import Enum
from urllib.parse import urlparse

import aiohttp
import discord

import pendulum


class Post:
    def __init__(self, **data):
        self.created = pendulum.from_timestamp(data['data']['created_utc'])
        self.title = data['data']['title']
        self.url = data['data'].get('url')
        self.author = data['data']['author']
        self.subreddit = data['data']['subreddit']
        self.permalink = f"https://reddit.com{data['data']['permalink']}"
        text = data['data'].get('selftext', '')
        self.text = f"{text[:240]}.." if len(text) > 242 else text

    @property
    def is_image(self) -> bool:
        """Returns True if the post links to an image file."""
        if not self.url:
            return False
        return urlparse(self.url).path.endswith(('png', 'jpg', 'jpeg', 'webp'))

    def embed(self):
        embed = discord.Embed(title=self.title, url=self.permalink, timestamp=self.created)
        embed.set_footer(text=f"Posted by {self.author} on r/{self.subreddit}")
        if self.is_image:
            embed.set_image(url=self.url)
        elif self.text:
            embed.description = self.text
        return embed


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


async def get_posts(
    session: aiohttp.ClientSession,
    subreddit: str,
    *,
    sort: Sort = Sort.new,
    time: SortTime = None,
    limit: int = 25,
    cls: Post = Post
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
