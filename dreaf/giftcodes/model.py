from __future__ import annotations

import datetime
import logging
import typing as t

import pendulum
from discord.ext import commands

from dreaf import db
from dreaf.items.model import Item

log = logging.getLogger(__name__)


class GiftCode(db.Table):

    def __init__(self, code: str, expiry: t.Optional[int] = None):
        self.code = code.casefold()
        self._expiry = expiry
        self._rewards: t.Dict[Item, int] = dict()

    def __str__(self):
        return self.code

    def __repr__(self):
        return f"<GiftCode {self.code}>"

    @property
    def expiry(self) -> pendulum.DateTime:
        return pendulum.from_timestamp(self._expiry) if self._expiry else None

    @property
    def rewards(self) -> t.Dict[Item, int]:
        if self._rewards:
            return self._rewards

        data = self._select_rewards(self.code)
        return {Item.get(reward): qty for reward, qty in data}

    def rewards_formatted(self, bot, verbose=False):
        rewards = []
        for r, qty in self.rewards.items():
            qty = self.friendly_numbers(qty)
            emoji = bot.get_emoji(r.emoji_id) if r.emoji_id else ''
            if verbose:
                rewards.append(f"{emoji} {r.name.title()} x {qty}")
            else:
                rewards.append(f"{emoji} {qty}")
        join_str = "\n" if verbose else " "
        return join_str.join(rewards) if rewards else "\u200b"

    def is_posted(self):
        result = self._select(self.code)
        if not result:
            return False
        _code, _expiry, posted = result
        return bool(posted)

    def is_expired(self):
        expiry = self.expiry
        if not expiry:
            return None

        return expiry < pendulum.now("UTC")

    def exists(self) -> bool:
        return bool(self.get(self.code))

    def is_redeemed(self, user_id: int) -> bool:
        redeemed = self._select_redeemed(user_id, self.code)
        return bool(redeemed)

    def mark_redeemed(self, user_id: int):
        self._insert_redeemed(user_id, self.code)

    def add_reward(self, item: Item, qty: int):
        self._rewards[item] = qty
        self._insert_reward(self.code, item.name, qty)

    def remove_reward(self, item: Item):
        if item in self._rewards:
            del self._rewards[item]
        self._delete_reward(self.code, item.name)

    def set_posted(self):
        self._insert(self.code, self._expiry, True)

    def set_expiry(self, expiry: t.Optional[datetime.datetime]):
        self._expiry = int(expiry.timestamp())
        self._insert(self.code, self._expiry)

    def mark_expired(self):
        if not self.expiry:
            self.set_expiry(pendulum.now())

    @classmethod
    async def convert(cls, _ctx, arg):
        code = cls.get(arg)
        if not code:
            raise commands.BadArgument("Code not found.")
        return code

    @classmethod
    def get(cls, code: str):
        try:
            code, expiry, posted = cls._select(code.casefold())
        except TypeError:
            return None
        return cls(code, expiry)

    def save(self):
        self._insert(self.code, self._expiry)

    def delete(self):
        self._delete(self.code)

    @classmethod
    def get_all(cls, include_expired: bool = False) -> t.List[GiftCode]:
        codes = cls._select_all(include_expired)
        return [cls(c, e) for c, e, _ in codes]

    @staticmethod
    def friendly_numbers(number: int) -> str:
        unit = ""
        if 999 < number < 999999:
            number = int(number/1000)
            unit = "K"
        elif 999999 < number:
            number = int(number/1000000)
            unit = "M"
        return f"{number:,}{unit}"

    # region: SQL methods

    @staticmethod
    def _select(code):
        cursor = db.conn.execute(
            """
            SELECT code, expiry, posted
            FROM codes
            WHERE code = ?;
            """,
            [code.casefold()]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_all(include_expired=False):
        if include_expired:
            cursor = db.conn.execute("SELECT code, expiry, posted FROM codes")
        else:
            cursor = db.conn.execute(
                """
                SELECT code, expiry, posted
                FROM codes
                WHERE expiry > ? OR expiry IS NULL;
                """,
                [int(pendulum.now().timestamp())]
            )
        data = cursor.fetchall()
        cursor.close()
        return data

    @staticmethod
    def _select_rewards(code: str):
        cursor = db.conn.execute(
            """
            SELECT reward, qty
            FROM code_rewards
            WHERE code = ?;
            """,
            [code.casefold()]
        )
        data = cursor.fetchall()
        cursor.close()
        return data

    @staticmethod
    def _select_redeemed(player_id: int, code: str):
        cursor = db.conn.execute(
            """
            SELECT code
            FROM redeemed_codes
            WHERE player_id = ? AND code = ?;
            """,
            [player_id, code.casefold()]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _insert(code: str, expiry: int, posted: bool = False):
        cursor = db.conn.execute(
            """
            INSERT INTO codes(code, expiry, posted) VALUES (?, ?, ?)
            ON CONFLICT(code)
            DO UPDATE SET
              expiry=excluded.expiry,
              posted=excluded.posted
            """,
            [code.casefold(), expiry, posted]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _delete(code: str):
        cursor = db.conn.execute("DELETE FROM codes WHERE code = ?;", [code.casefold()])
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _insert_reward(code: str, reward: str, qty: int):
        cursor = db.conn.execute(
            """
            INSERT INTO code_rewards(code, reward, qty) VALUES (?, ?, ?)
            ON CONFLICT(code, reward)
            DO UPDATE SET
              qty=excluded.qty
            """,
            [code.casefold(), reward, qty]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _delete_reward(code: str, reward: str):
        cursor = db.conn.execute("DELETE FROM code_rewards WHERE code = ? AND reward = ?;", [code.casefold(), reward])
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _insert_redeemed(player_id: int, code: str):
        cursor = db.conn.execute(
            """
            INSERT INTO redeemed_codes(player_id, code) VALUES (?, ?)
            ON CONFLICT(player_id, code)
            DO NOTHING;
            """,
            [player_id, code.casefold()]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _create_table():
        log.info("Ensuring table exists: codes")
        cursor = db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS codes (
              code TEXT PRIMARY KEY,
              expiry INT NULL,
              posted BOOLEAN default FALSE
            );
            """
        )
        log.info("Ensuring table exists: code_rewards")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS code_rewards (
              code TEXT NOT NULL,
              reward TEXT NOT NULL,
              qty INT NOT NULL,
              PRIMARY KEY (code, reward)
            );
            """
        )
        log.info("Ensuring table exists: redeemed_codes")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS redeemed_codes (
              player_id INT NOT NULL,
              code TEXT NOT NULL,
              PRIMARY KEY (player_id, code)
            );
            """
        )
        cursor.close()

    # endregion
