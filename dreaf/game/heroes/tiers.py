import csv
import logging
import sqlite3
from pathlib import Path

from dreaf import db
from .heroes import Ascension

log = logging.getLogger(__name__)

data_path = Path("data/")


class HeroTier(db.Table):
    default_data = data_path / "hero_tiers.csv"
    cache = dict()

    def __init__(self, name, min_ascension: Ascension, max_ascension: Ascension):
        self.name = name
        self.min_ascension = min_ascension
        self.max_ascension = max_ascension

    @classmethod
    async def convert(cls, _ctx, arg: str):
        return cls.get(arg)

    @classmethod
    def get(cls, name: str):
        if not cls.cache:
            for data in cls._select_all():
                data = dict(data)
                data['min_ascension'] = Ascension.get(data['min_ascension'])
                data['max_ascension'] = Ascension.get(data['max_ascension'])
                cls.cache[data['name'].casefold()] = cls(**data)
        return cls.cache.get(name.casefold())

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name, min_ascension, max_ascension
            FROM hero_tiers
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
            SELECT name, min_ascension, max_ascension
            FROM hero_tiers
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
            DELETE FROM hero_tiers
            WHERE name = ?;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroTier '{name}' deleted from table.")

    @staticmethod
    def _insert(name, min_ascension, max_ascension):
        cursor = db.conn.execute(
            """
            INSERT INTO hero_tiers(name, min_ascension, max_ascension)
              VALUES (?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
              min_ascension=excluded.min_ascension,
              max_ascension=excluded.max_ascension;
            """,
            [name, min_ascension, max_ascension]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroTier '{name}' inserted to table.")

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
                CREATE TABLE hero_tiers (
                  name TEXT PRIMARY KEY COLLATE nocase,
                  min_ascension TEXT NOT NULL,
                  max_ascension TEXT NOT NULL
                );
                """
            )
            cursor.close()
            log.info(f"'hero_tiers' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'hero_tiers' table default data loaded.")
        except sqlite3.OperationalError:
            return
