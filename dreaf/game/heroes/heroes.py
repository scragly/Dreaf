import csv
import logging
import sqlite3
from pathlib import Path

from PIL import Image
from rapidfuzz import process

from dreaf import db
from .ascensions import Ascension
from .classes import HeroClass
from .factions import Faction
from .roles import HeroRole
from .tiers import HeroTier
from .types import HeroType

log = logging.getLogger(__name__)

data_path = Path("data/")


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
        self.ascension = self.base_ascension

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Hero '{self.name}'>"

    def img_masked_portrait(self):
        return Image.open(Path(f"images/frames/heroes/{self.name.casefold()}.png"))

    def img_portrait(self):
        return Image.open(Path(f"images/heroes/{self.name.casefold()}.png"))

    def img_tile(self, ascension: Ascension = None):
        ascension = ascension or self.ascension
        # faction = self.faction.img_frame_icon()
        faction = self.faction.img_icon()
        faction.thumbnail((41, 41))
        img = Image.alpha_composite(self.img_masked_portrait(), ascension.img_frame())
        img.paste(faction, (6, 6), faction.convert("RGBA"))
        # return Image.alpha_composite(img, faction)
        return img

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
