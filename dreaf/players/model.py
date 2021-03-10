from __future__ import annotations

import logging
import typing as t

from discord.ext import commands

from dreaf import db


log = logging.getLogger(__name__)


class Player(db.Table):
    def __init__(self, game_id: int, discord_id: int, main: bool = None, name: str = None):
        self.game_id = game_id
        self.discord_id = discord_id

        if main is not None:
            self.main = main
        else:
            existing_player = Player._select(game_id)
            if existing_player:
                self.main = existing_player.main
            else:
                self.main = False

        if name:
            self.name = name
        else:
            result = Player._select(game_id)
            if result:
                self.name = result[3]
            else:
                self.name = None

    @classmethod
    async def convert(cls, _ctx: commands.Context, arg: str):
        matched_players = cls.get_by_discord_id(arg)
        if not matched_players:
            raise commands.BadArgument("Couldn't find players.")
        return matched_players

    @classmethod
    def get(cls, game_id: int) -> t.Optional[Player]:
        results = cls._select(game_id)
        if results:
            game_id, discord_id, main, name = results
            return cls(game_id, discord_id, main, name)
        return None

    @classmethod
    def get_by_discord_id(cls, discord_id) -> t.List[Player]:
        results = cls._select_all(discord_id=discord_id)
        players = [cls(gid, did, main, name) for (gid, did, main, name) in results]
        return players

    @classmethod
    def get_main(cls, discord_id: int):
        try:
            game_id, discord_id, main, name = cls._select_main(discord_id)
        except TypeError:
            return None
        return cls(game_id, discord_id, main, name)

    def save(self):
        self._insert(self.game_id, self.discord_id, self.main)
        if self.name:
            self.set_name(self.name)

    def set_name(self, name):
        self._insert_name(self.game_id, name)

    def delete(self):
        self._delete(self.game_id)

    # region: SQL methods

    @staticmethod
    def _select(game_id=None):
        cursor = db.conn.execute("SELECT game_id, discord_id, main, name FROM players WHERE game_id = ?", [game_id])
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_main(discord_id: int):
        cursor = db.conn.execute(
            """
            SELECT game_id, discord_id, main, name
            FROM players
            WHERE discord_id = ? AND main = TRUE;
            """,
            [discord_id]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_all(game_id=None, discord_id=None):
        select = "SELECT game_id, discord_id, main, name FROM players WHERE "
        where = []
        query_items = []
        if game_id:
            where.append("game_id = ?")
            query_items.append(game_id)
        if discord_id:
            where.append("discord_id = ?")
            query_items.append(discord_id)

        if not where:
            raise ValueError("Empty query when selecting data from player table.")

        where = ", ".join(where)
        cursor = db.conn.execute(f"{select}{where};", query_items)
        data = cursor.fetchall()
        cursor.close()
        return data

    @staticmethod
    def _insert(game_id: int, discord_id: int, main=False):
        cursor = db.conn.execute(
            """
            INSERT INTO players(game_id, discord_id, main) VALUES (?, ?, ?)
            ON CONFLICT(game_id)
            DO UPDATE SET
              discord_id=excluded.discord_id,
              main=excluded.main;
            """,
            [game_id, discord_id, main]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _insert_name(game_id: int, name: str):
        cursor = db.conn.execute(
            """
            INSERT INTO players(game_id, name) VALUES (?, ?)
            ON CONFLICT(game_id)
            DO UPDATE SET
              name=excluded.name;
            """,
            [game_id, name]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _delete(game_id):
        cursor = db.conn.execute("DELETE FROM players WHERE game_id = ?", [game_id])
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _create_table():
        log.info("Ensuring table exists: players")
        cursor = db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
              game_id INT PRIMARY KEY,
              discord_id INT NULL,
              main BOOLEAN default TRUE,
              name TEXT NULL
            );
            """
        )
        db.conn.commit()
        cursor.close()

    # endregion
