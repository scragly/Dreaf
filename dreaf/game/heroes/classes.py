import csv
import logging
import sqlite3
from pathlib import Path

from dreaf import db

log = logging.getLogger(__name__)

data_path = Path("data/")


class HeroClass(db.Table):
    default_data = data_path / "hero_classes.csv"
    cache = dict()

    def __init__(self, name: str, blessing: str):
        self.name = name
        self.blessing = blessing

    @classmethod
    async def convert(cls, _ctx, arg: str):
        return cls.get(arg)

    @classmethod
    def get(cls, name: str):
        if not cls.cache:
            for data in cls._select_all():
                hc = cls(**data)
                cls.cache[hc.name.casefold()] = hc
                cls.cache[hc.blessing.casefold()] = hc
        return cls.cache.get(name.casefold())

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name, blessing
            FROM hero_classes
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
            SELECT name, blessing
            FROM hero_classes
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
        log.info(f"HeroClass '{name}' deleted from table.")

    @staticmethod
    def _insert(name, blessing):
        cursor = db.conn.execute(
            """
            INSERT INTO hero_classes(name, blessing)
              VALUES (?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
              blessing=excluded.blessing;
            """,
            [name, blessing]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroClass '{name}' inserted to table.")

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
                CREATE TABLE hero_classes (
                  name TEXT PRIMARY KEY COLLATE nocase,
                  blessing TEXT UNIQUE NOT NULL
                );
                """
            )
            cursor.close()
            log.info(f"'hero_classes' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'hero_classes' table default data loaded.")
        except sqlite3.OperationalError:
            return

