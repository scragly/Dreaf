from __future__ import annotations

import asyncio
import logging
import typing as t
from collections import namedtuple
from datetime import datetime, timedelta

import aiohttp

log = logging.getLogger(__name__)

AccessToken = namedtuple("AccessToken", ["token", "expires_at"])


class RedditAPI:
    URL = "https://www.reddit.com"
    OAUTH_URL = "https://oauth.reddit.com"
    MAX_RETRIES = 1
    HEADERS = {"User-Agent": "python3:scragly/dreaf (by /u/scragly91)"}

    def __init__(self, bot):
        self.bot = bot
        self.session: aiohttp.ClientSession = bot.http_session
        self.access_token = None
        self.auth = aiohttp.BasicAuth("6QIpdSC6DuCTXJO8oKx8tw", "UI7r3-3r2xVbf152cFrRo8qf0pbIwQ")
        print("reddit api client setup.")

    async def get_access_token(self) -> None:
        """
        Get a Reddit API OAuth2 access token and assign it to self.access_token.
        A token is valid for 1 hour. There will be MAX_RETRIES to get a token, after which the cog
        will be unloaded and a ClientError raised if retrieval was still unsuccessful.
        """
        for i in range(1, self.MAX_RETRIES + 1):
            response = await self.session.post(
                url=f"{self.URL}/api/v1/access_token",
                headers=self.HEADERS,
                auth=self.auth,
                data={
                    "grant_type": "client_credentials",
                    "duration": "temporary"
                }
            )

            if response.status == 200 and response.content_type == "application/json":
                content = await response.json()
                expiration = int(content["expires_in"]) - 60  # Subtract 1 minute for leeway.
                self.access_token = AccessToken(
                    token=content["access_token"],
                    expires_at=datetime.utcnow() + timedelta(seconds=expiration)
                )

                log.debug(f"New token acquired; expires on {self.access_token.expires_at}")
                return
            else:
                log.debug(
                    f"Failed to get an access token: "
                    f"status {response.status} & content type {response.content_type}; "
                    f"retrying ({i}/{self.MAX_RETRIES})"
                )

            await asyncio.sleep(3)

        raise Exception("Authentication with the Reddit API failed.")

    async def revoke_access_token(self) -> None:
        """
        Revoke the OAuth2 access token for the Reddit API.
        For security reasons, it's good practice to revoke the token when it's no longer being used.
        """
        response = await self.session.post(
            url=f"{self.URL}/api/v1/revoke_token",
            headers=self.HEADERS,
            auth=self.auth,
            data={
                "token": self.access_token.token,
                "token_type_hint": "access_token"
            }
        )

        if response.status == 204 and response.content_type == "application/json":
            self.access_token = None
        else:
            log.warning(f"Unable to revoke access token: status {response.status}.")

    async def fetch_posts(self, route: str, *, amount: int = 25, params: dict = None) -> list[dict]:
        """A helper method to fetch a certain amount of Reddit posts at a given route."""
        # Reddit's JSON responses only provide 25 posts at most.
        if not 25 >= amount > 0:
            raise ValueError("Invalid amount of subreddit posts requested.")

        # Renew the token if necessary.
        if not self.access_token or self.access_token.expires_at < datetime.utcnow():
            await self.get_access_token()

        print(f"Access token: {self.access_token}")

        error = None
        url = f"{self.OAUTH_URL}/{route}"
        for _ in range(self.MAX_RETRIES):
            response = await self.session.get(
                url=url,
                headers={**self.HEADERS, "Authorization": f"bearer {self.access_token.token}"},
                params=params
            )
            if response.status == 200 and response.content_type == 'application/json':
                # Got appropriate response - process and return.
                content = await response.json()
                posts = content["data"]["children"]

                filtered_posts = [post for post in posts if not post["data"]["over_18"]]

                return filtered_posts[:amount]

            else:
                print(await response.text())
                print(response.headers)
                error = f"Invalid response from: {url} - status code {response.status}, mimetype {response.content_type}"
                print(error)

            await asyncio.sleep(3)

        if error:
            log.debug(error)

        return list()  # Failed to get appropriate response within allowed number of retries.
