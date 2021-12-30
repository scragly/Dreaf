import csv
import logging
import sqlite3
import typing as t
from pathlib import Path

from PIL import Image

from dreaf import db

log = logging.getLogger(__name__)

data_path = Path("data/")


class Ascension(db.Table):
    default_data = data_path / "ascensions.csv"
    cache = dict()

    def __init__(self, name: str, level_cap: int, aliases: t.List[str]):
        self.name = name
        self.level_cap = level_cap
        self.aliases = aliases

    def img_frame(self) -> Image:
        img = Image.open(Path(f"images/frames/frame_{self.name.casefold().strip('+')}.png"))
        if self.is_plus:
            corners = Image.open(Path(f"images/frames/corners_{self.name.casefold().strip('+')}.png"))
            img = Image.alpha_composite(img, corners)
        return img

    @property
    def is_plus(self):
        return self.name.endswith("+")

    @classmethod
    async def convert(cls, _ctx, arg: str):
        return cls.get(arg)

    @classmethod
    def get(cls, name: str):
        if not cls.cache:
            for data in cls._select_all():
                data = dict(data)
                data['aliases'] = data['aliases'].split(',')
                asc = cls(**data)
                cls.cache[asc.name.casefold()] = asc
                for alias in asc.aliases:
                    cls.cache[alias.casefold()] = asc
            for n in ["none", "n", "unknown", "unk", "?"]:
                cls.cache[n] = cls.none()
        return cls.cache.get(name.casefold())

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name, level_cap, aliases
            FROM ascensions
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
            SELECT name, level_cap, aliases
            FROM ascensions
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
            DELETE FROM ascensions
            WHERE name = ?;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"Ascension '{name}' deleted from table.")

    @staticmethod
    def _insert(name, level_cap, aliases):
        cursor = db.conn.execute(
            """
            INSERT INTO ascensions(name, level_cap, aliases)
              VALUES (?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
              level_cap=excluded.level_cap,
              aliases=excluded.aliases;
            """,
            [name, level_cap, aliases]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"Ascension '{name}' inserted to table.")

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
                CREATE TABLE ascensions (
                  name TEXT PRIMARY KEY COLLATE nocase,
                  level_cap INTEGER NOT NULL,
                  aliases TEXT
                );
                """
            )
            cursor.close()
            log.info(f"'ascensions' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'ascensions' table default data loaded.")
        except sqlite3.OperationalError:
            return

    @classmethod
    def none(cls):
        return cls("none", 0, [])
