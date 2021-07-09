import csv
import sqlite3
import logging
import typing as t
from pathlib import Path

from rapidfuzz import fuzz, process

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

    @property
    def frame_icon_img(self):
        return f"faction_{self.name.casefold()}.png"

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


class HeroRole(db.Table):
    default_data = data_path / "hero_roles.csv"
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
            FROM hero_roles
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
            FROM hero_roles
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
            DELETE FROM hero_roles
            WHERE name = ?;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroRole '{name}' deleted from table.")

    @staticmethod
    def _insert(name):
        cursor = db.conn.execute(
            """
            INSERT INTO hero_roles(name) VALUES (?)
            ON CONFLICT(name)
            DO NOTHING;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"HeroRole '{name}' inserted to table.")

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
                CREATE TABLE hero_roles (
                  name TEXT PRIMARY KEY COLLATE nocase
                );
                """
            )
            cursor.close()
            log.info(f"'hero_roles' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'hero_roles' table default data loaded.")
        except sqlite3.OperationalError:
            return


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


class Ascension(db.Table):
    default_data = data_path / "ascensions.csv"
    cache = dict()

    def __init__(self, name: str, level_cap: int, aliases: t.List[str]):
        self.name = name
        self.level_cap = level_cap
        self.aliases = aliases

    @property
    def frame_img(self):
        return f"frame_{self.name.casefold().strip('+')}.png"

    @property
    def corner_img(self):
        if self.is_plus:
            return f"corners_{self.name.casefold().strip('+')}.png"
        return None

    @property
    def is_plus(self):
        return self.name.endswith("+")

    @classmethod
    async def convert(cls, _ctx, arg: str):
        if arg in ["none", "n", "unknown", "unk", "?"]:
            return cls.none()
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


class Hero(db.Table):
    default_data = data_path / "heroes.csv"
    cache = dict()

    def __init__(
        self,
        name: str,
        faction: Faction,
        tier: HeroTier,
        type: HeroType,
        hero_class: HeroClass,
        primary_role: HeroRole,
        secondary_role: HeroRole
    ):
        self.name = name
        self.faction = faction
        self.tier = tier
        self.type = type
        self.hero_class = hero_class
        self.primary_role = primary_role
        self.secondary_role = secondary_role
        self.ascension = Ascension.none()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Hero '{self.name}'>"

    @property
    def hero_frame_img(self):
        return f"{self.name.casefold()}.png"

    @property
    def base_ascension(self):
        return self.tier.min_ascension

    @classmethod
    async def convert(cls, _ctx, arg: str):
        asc = Ascension.get(arg)
        if asc:
            return cls.unknown(ascension=asc)

        faction = Faction.get(arg)
        if faction:
            return cls.unknown(faction=faction)

        if arg in {"none", "n", "unknown", "unk", "?"}:
            return cls.unknown()

        hero = cls.match(arg)
        if hero:
            return hero

        return None

    @classmethod
    def from_data(cls, data):
        data = dict(**data)
        data['faction'] = Faction.get(data['faction'])
        data['tier'] = HeroTier.get(data['tier'])
        data['type'] = HeroType.get(data['type'])
        data['hero_class'] = HeroClass.get(data['class']) if data['class'] else None
        del data['class']
        data['primary_role'] = HeroRole.get(data['primary_role'])
        if data['secondary_role']:
            data['secondary_role'] = HeroRole.get(data['secondary_role'])
        return cls(**data)

    @classmethod
    def get(cls, name: str = None):
        if not cls.cache:
            for data in cls._select_all():
                cls.cache[data['name'].casefold()] = cls.from_data(data)

        if name:
            return cls.cache.get(name.casefold())

    @classmethod
    def get_all(cls):
        if not cls.cache:
            cls.get()
        return [h for h in cls.cache.values()]

    @classmethod
    def get_by_tier(cls, tier: HeroTier, *, cele=False, hypo=False, dim=False, std=True):
        if not cls.cache:
            cls.get()
        return [cls.from_data(h) for h in cls._select_tier(tier.name.casefold(), cele, hypo, dim, std)]

    @classmethod
    def load_default_data(cls):
        with cls.default_data.open("r") as f:
            data = csv.DictReader(f)
            for entry in data:
                cls._insert(**entry)

    # region: SQL methods

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name, faction, tier, type, class, primary_role, secondary_role
            FROM heroes
            WHERE name = ?;
            """,
            [name]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_tier(tier: str, cele=False, hypo=False, dim=False, std=True):
        factions = []
        if cele:
            factions.append("'Celestial'")
        if hypo:
            factions.append("'Hypogean'")
        if dim:
            factions.append("'Dimensional'")
        if std:
            factions.append("'Lightbearer', 'Wilder', 'Mauler', 'Graveborn'")

        if not factions:
            return []

        cursor = db.conn.execute(
            f"""
            SELECT name, faction, tier, type, class, primary_role, secondary_role
            FROM heroes
            WHERE tier = ?
            AND faction IN ({', '.join(factions)})
            ;
            """,
            [tier]
        )
        data = cursor.fetchall()

        cursor.close()
        return data

    @staticmethod
    def _select_all():
        cursor = db.conn.execute(
            """
            SELECT name, faction, tier, type, class, primary_role, secondary_role
            FROM heroes
            ORDER BY name;
            """
        )
        data = cursor.fetchall()
        cursor.close()
        return data

    @staticmethod
    def _insert(name, faction, tier, hero_type, hero_class, primary_role, secondary_role):
        cursor = db.conn.execute(
            """
            INSERT INTO heroes(name, faction, tier, type, class, primary_role, secondary_role)
              VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
              faction=excluded.faction,
              tier=excluded.tier,
              type=excluded.type,
              class=excluded.class,
              primary_role=excluded.primary_role,
              secondary_role=excluded.secondary_role;
            """,
            [name, faction, tier, hero_type, hero_class, primary_role, secondary_role]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"Hero '{name}' inserted to table.")

    @staticmethod
    def _delete(name):
        cursor = db.conn.execute(
            """
            DELETE FROM heroes
            WHERE name = ?;
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()
        log.info(f"Hero '{name}' deleted from table.")

    @classmethod
    def _create_table(cls):
        try:
            cursor = db.conn.execute(
                """
                CREATE TABLE heroes (
                  name TEXT PRIMARY KEY COLLATE nocase,
                  faction TEXT NOT NULL COLLATE nocase,
                  tier TEXT NOT NULL COLLATE nocase,
                  type TEXT NOT NULL COLLATE nocase,
                  class TEXT COLLATE nocase,
                  primary_role TEXT NOT NULL COLLATE nocase,
                  secondary_role TEXT COLLATE nocase
                );
                """
            )
            cursor.close()
            log.info(f"'heroes' table created. Loading default data.")
            cls.load_default_data()
            log.info(f"'heroes' table default data loaded.")
        except sqlite3.OperationalError:
            return

    # endregion

    @classmethod
    def unknown(cls, *, faction: Faction = None, ascension: Ascension = None):
        return cls(
            ascension.name if ascension else "unknown",
            faction or Faction.unknown(),
            HeroTier("unknown", ascension or Ascension.none(), ascension or Ascension.none()),
            HeroType("unknown"),
            HeroClass("unknown", "unknown"),
            HeroRole("unknown"),
            HeroRole("unknown"),
        )

    @classmethod
    def match(cls, query):
        if not cls.cache:
            cls.get()
        result = process.extractOne(query, cls.cache.keys(), score_cutoff=90)
        if result:
            return cls.cache[result[0]]
