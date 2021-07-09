import csv
import logging
import sqlite3
from pathlib import Path

from dreaf import db

log = logging.getLogger(__name__)

data_path = Path("data/")


class HeroType(db.Table):
    default_data = data_path / "hero_types.csv"
    cache = dict()

    def __init__(self, name: str):
        self.name = name

    @classmethod
    async def convert(cls, _ctx, arg: str):
        return cls.get(arg)

    @classmethod
    def get(cls, name: str):
        if not cls.cache:
            cls.cache = {data['name'].casefold(): cls(**data) for data in cls._select_all()}
        return cls.cache.get(name.casefold())

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name
            FROM hero_types
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
            SELECT name
            FROM hero_types
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
            DELETE FROM hero_types
            WHERE name = ?;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroType '{name}' deleted from table.")

    @staticmethod
    def _insert(name):
        cursor = db.conn.execute(
            """
            INSERT INTO hero_types(name) VALUES (?)
            ON CONFLICT(name)
            DO NOTHING;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroType '{name}' inserted to table.")

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
                CREATE TABLE hero_types (
                  name TEXT PRIMARY KEY COLLATE nocase
                );
                """
            )
            cursor.close()
            log.info(f"'hero_types' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'hero_types' table default data loaded.")
        except sqlite3.OperationalError:
            return
