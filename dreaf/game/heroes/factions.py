import csv
import logging
import sqlite3
import typing as t
from pathlib import Path

from PIL import Image

from dreaf import db

log = logging.getLogger(__name__)

data_path = Path("data/")


class Faction(db.Table):
    default_data = data_path / "factions.csv"
    cache = dict()

    def __init__(self, name: str, emblem_cap: int, aliases: t.List[str]):
        self.name = name
        self.emblem_cap = emblem_cap
        self.aliases = aliases

    def img_frame_icon(self):
        return Image.open(Path(f"images/frames/faction_{self.name.casefold()}.png"))

    def img_icon(self):
        return Image.open(Path(f"images/factions/{self.name.casefold()}.png"))

    @classmethod
    async def convert(cls, _ctx, arg: str):
        if arg in ["unknown", "unk", "?", "any", "none"]:
            return cls.unknown()
        return cls.get(arg)

    @classmethod
    def get(cls, name: str):
        if not cls.cache:
            for data in cls._select_all():
                data = dict(data)
                data['aliases'] = data['aliases'].split(',')
                f = cls(**data)
                cls.cache[f.name.casefold()] = f
                for alias in f.aliases:
                    cls.cache[alias.casefold()] = f
        return cls.cache.get(name.casefold())

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name, emblem_cap, aliases
            FROM factions
            WHERE name = ?;
            """,
            [name]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_all():
        cursor = db.conn.execute(
            """
            SELECT name, emblem_cap, aliases
            FROM factions
            ORDER BY name;
            """
        )
        data = cursor.fetchall()
        cursor.close()
        return data

    @staticmethod
    def _delete(name):
        cursor = db.conn.execute(
            """
            DELETE FROM factions
            WHERE name = ?;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"Faction '{name}' deleted from table.")

    @staticmethod
    def _insert(name, emblem_cap, aliases):
        cursor = db.conn.execute(
            """
            INSERT INTO factions(name, emblem_cap, aliases)
              VALUES (?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
              emblem_cap=excluded.emblem_cap,
              aliases=excluded.aliases;
            """,
            [name, emblem_cap, aliases]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"Faction '{name}' inserted to table.")

    @classmethod
    def load_default_data(cls):
        with cls.default_data.open("r") as f:
            data = csv.DictReader(f)
            for entry in data:
                cls._insert(**entry)

    @classmethod
    def _create_table(cls):
        try:
            cursor = db.conn.execute(
                """
                CREATE TABLE factions (
                  name TEXT PRIMARY KEY COLLATE nocase,
                  emblem_cap INTEGER NOT NULL,
                  aliases TEXT
                );
                """
            )
            cursor.close()
            log.info(f"'factions' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'factions' table default data loaded.")
        except sqlite3.OperationalError:
            return

    @classmethod
    def unknown(cls):
        return cls("unknown", 0, [])
