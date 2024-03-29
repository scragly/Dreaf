from __future__ import annotations

import asyncio
import logging
import pathlib
import typing as t
from contextlib import suppress

import aiohttp
import pendulum
from aiohttp import ContentTypeError

import discord

from dreaf.giftcodes import GiftCode
from dreaf.players import Player

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot

log = logging.getLogger(__name__)

HEADERS = {"Content-Type": "application/json", "charset": "UTF-8"}
COOKIE_PATH = pathlib.Path("sessions")
if not COOKIE_PATH.exists():
    COOKIE_PATH.mkdir()

SESSIONS: t.Dict[int, RedeemSession] = dict()


class CodeException(Exception):
    pass


class CodeUsed(CodeException):
    pass


class CodeExpired(CodeException):
    pass


class InvalidCode(CodeException):
    pass


class VerifyFailed(Exception):
    pass


class SessionExpired(VerifyFailed):
    pass


class VerifyRateLimited(VerifyFailed):
    pass


class ExistingRequest(VerifyFailed):
    pass


class RedeemSession:
    _active = set()

    def __init__(self, game_id: int, *, cookie_jar: aiohttp.CookieJar = None):
        self.game_id = game_id
        if cookie_jar:
            self.http_session = aiohttp.ClientSession(cookie_jar=cookie_jar, headers=HEADERS)
        else:
            self.http_session = aiohttp.ClientSession(headers=HEADERS)

        SESSIONS[game_id] = self

    async def send_mail(self):
        payload = {
            "game": "afk",
            "sender": "sender",
            "title": "Verification Code",
            "uid": self.game_id
        }
        async with self.http_session.post("https://cdkey.lilith.com/api/send-mail", json=payload) as resp:
            try:
                data = await resp.json()
                if data.get("info") == "err_send_mail_too_often":
                    raise VerifyRateLimited
            except ContentTypeError:
                raise VerifyFailed("Verification mail was unable to be sent, server error encountered.")

    async def request_verification_code(
        self,
        bot: DreafBot,
        channel: discord.TextChannel,
        member: discord.Member,
        *,
        is_retry: int = 0,
        max_retries: int = 3
    ):

        if is_retry == 0:
            if member.id in self._active:
                raise ExistingRequest
            else:
                self._active.add(member.id)

            try:
                await member.send(
                    "A verification mail has been sent to you in-game. "
                    "Please reply here with the verification code within 10 minutes."
                )
                log.info("Verification DM is sent.")
            except discord.HTTPException:
                self._active.remove(member.id)
                raise
        else:
            await member.send(f"Wrong code, please try again. ({is_retry}/{max_retries} attempts used)")

        def check(m: discord.Message):
            if not isinstance(m.channel, discord.DMChannel):
                return False
            if m.channel.recipient != m.author:
                return False
            if m.author != member:
                return False
            return True

        try:
            message = await bot.wait_for('message', check=check, timeout=600)
            log.info(f"Received response of {message.content}")
        except asyncio.TimeoutError:
            await member.send("Verification timed out. Please try again.")
            log.info(f"Verification timed out for {member}")
            self._active.remove(member.id)
            return

        try:
            await self.verify_code(message.content)
        except VerifyFailed:
            if is_retry == max_retries:
                self._active.remove(member.id)
                raise VerifyFailed
            else:
                await self.request_verification_code(bot, channel, member, is_retry=is_retry+1)

        self._active.remove(member.id)

    async def verify_afk_code(self, verification_code: str):
        """New endpoint to verify in one request, no need to send-mail."""
        payload = {
            "game": "afk",
            "uid": self.game_id,
            "code": verification_code
        }
        async with self.http_session.post("https://cdkey.lilith.com/api/verify-afk-code", json=payload) as resp:
            data = await resp.json()
            if data["info"] == "err_wrong_code":
                raise VerifyFailed
            self.save()
            return data

    async def verify_code(self, verification_code: str):
        payload = {
            "game": "afk",
            "uid": self.game_id,
            "code": verification_code
        }
        async with self.http_session.post("https://cdkey.lilith.com/api/verify-code", json=payload) as resp:
            data = await resp.json()
            if data["info"] == "err_wrong_code":
                raise VerifyFailed
            self.save()
            return data

    async def _redeem_code(self, code: GiftCode, specific_id=None, force=False):
        if not force and code.is_redeemed(self.game_id):
            raise CodeUsed

        payload = {
            "type": "cdkey_web",
            "game": "afk",
            "uid": specific_id or self.game_id,
            "cdkey": code.code
        }
        async with self.http_session.post("https://cdkey.lilith.com/api/cd-key/consume", json=payload) as resp:
            data = await resp.json()
            if data["info"] == "err_cdkey_batch_error":
                raise CodeUsed
            elif data["info"] == "err_cdkey_expired":
                raise CodeExpired
            elif data["info"] == "err_cdkey_record_not_found":
                raise InvalidCode
            elif data["info"] == "err_login_state_out_of_date":
                raise SessionExpired

    async def get_users(self):
        payload = {
            "game": "afk",
            "uid": self.game_id,
        }
        async with self.http_session.post("https://cdkey.lilith.com/api/users", json=payload) as resp:
            data = await resp.json()
            if data["info"] == "err_login_state_out_of_date":
                raise SessionExpired
        current = Player.get(self.game_id)
        players = []
        for user in data["data"]["users"]:
            player = Player(user["uid"], current.discord_id, user["is_main"], user["name"], user["svr_id"], user["level"])
            player.save()
            players.append(player)
        return players

    async def is_verified(self):
        try:
            with suppress(InvalidCode):
                await self._redeem_code(GiftCode("thisisaninvalidcode"), force=True)
            return True
        except SessionExpired:
            return False

    async def redeem_codes(self, *codes: GiftCode, ignore_expiry: bool = False) -> t.Dict[Player, t.List[GiftCode]]:
        if not await self.is_verified():
            raise SessionExpired

        players = await self.get_users()

        players_tasks = dict()
        all_tasks = []
        for player in players:
            players_tasks[player] = dict()
            for code in codes:
                task = asyncio.create_task(self._redeem_code(code, specific_id=player.game_id, force=ignore_expiry))
                players_tasks[player][code] = task
                all_tasks.append(task)

        await asyncio.gather(*all_tasks, return_exceptions=True)
        results = dict(success=[], used=[], expired=[], invalid=[])
        successful = dict()
        for player, player_tasks in players_tasks.items():
            successful[player] = []
            for code, task in player_tasks.items():
                exc = task.exception()
                if not exc:
                    results["success"].append(code)
                    code.mark_redeemed(self.game_id)
                    successful[player].append(code)
                elif isinstance(exc, CodeUsed):
                    results["used"].append(code)
                    code: GiftCode
                    code.mark_redeemed(self.game_id)
                elif isinstance(exc, CodeExpired):
                    results["expired"].append(code)
                    code.mark_expired()
                elif isinstance(exc, InvalidCode):
                    results["invalid"].append(code)
                    code.delete()
                else:
                    raise exc

        print(f"REDEEM RESULTS: {results}")
        print(f"REDEEMED: {successful}")
        return successful

    def purge_saves(self):
        for file in COOKIE_PATH.glob(f"{self.game_id}_*.session"):
            file.unlink(missing_ok=True)

    def save(self):
        self.purge_saves()
        timestamp = pendulum.now().int_timestamp
        self.http_session.cookie_jar.save(COOKIE_PATH/f"{self.game_id}_{timestamp}.session")

    @classmethod
    def in_active_session(cls, member_id: int):
        return member_id in cls._active

    @classmethod
    def get(cls, game_id: int):
        session = SESSIONS.get(game_id)
        if session:
            return session
        return RedeemSession(game_id)

    @classmethod
    async def all_verified(cls):
        return [s for s in SESSIONS.values() if await s.is_verified()]


def init_sessions():
    for file in COOKIE_PATH.iterdir():
        if file.suffix != ".session":
            continue

        game_id, timestamp = file.stem.split("_")
        timestamp = pendulum.from_timestamp(int(timestamp))
        game_id = int(game_id)

        if timestamp.add(days=14) < pendulum.now("UTC"):
            log.info(f"Cookie file {file.name} older than 14 days, removing.")
            file.unlink(missing_ok=True)
            continue

        cookie_jar = aiohttp.CookieJar()
        cookie_jar.load(file)
        RedeemSession(game_id, cookie_jar=cookie_jar)


init_sessions()
