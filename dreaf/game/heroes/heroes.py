from __future__ import annotations

import csv
import logging
import sqlite3
import typing as t
from pathlib import Path

from PIL import Image
from discord.ext import commands
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
    heroes = dict()

    def __init__(
        self,
        name: str,
        faction: Faction,
        tier: HeroTier,
        type: HeroType,
        hero_class: HeroClass,
        primary_role: HeroRole,
        secondary_role: HeroRole,
        ascension: t.Optional[Ascension] = None,
    ):
        self.name = name
        self.faction = faction
        self.tier = tier
        self.type = type
        self.hero_class = hero_class
        self.primary_role = primary_role
        self.secondary_role = secondary_role
        self.ascension = ascension or self.base_ascension

    def __str__(self):
        return f"{self.name}:{self.ascension.name}"

    def __repr__(self):
        if self.ascension == Ascension.none():
            return f"<Hero '{self.name.title()}'>"
        else:
            return f"<Hero '{self.ascension.name.title()} {self.name.title()}'>"

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return f"{self}" == f"{other}"

    def __hash__(self):
        return hash(f"{self}")

    def copy(self, ascension: t.Optional[Ascension] = None):
        return Hero(
            self.name,
            self.faction,
            self.tier,
            self.type,
            self.hero_class,
            self.primary_role,
            self.secondary_role,
            ascension or self.ascension
        )

    def img_masked_portrait(self, size: int = None):
        if size:
            img = Image.open(Path(f"images/frames/heroes/{self.name.casefold()}.png"))
            img.thumbnail((size, size))
            return img
        return Image.open(Path(f"images/frames/heroes/{self.name.casefold()}.png"))

    def img_portrait(self):
        return Image.open(Path(f"images/heroes/{self.name.casefold()}.png"))

    def img_tile(self, ascension: Ascension = None):
        save_dir = Path(f"images/frames/rendered/")
        if not save_dir.exists():
            save_dir.mkdir(exist_ok=True)
        try:
            log.debug(f"Pre-rendered frame served: {self}")
            return Image.open(save_dir / f"{self}.png".casefold())
        except FileNotFoundError:
            pass
        ascension = ascension or self.ascension
        base = Image.new("RGBA", (150, 150), (255, 0, 0, 0))
        faction = self.faction.img_icon(41)
        portrait = self.img_masked_portrait(134)
        base.paste(portrait, (8, 8))
        base = Image.alpha_composite(base, ascension.img_frame())
        base.alpha_composite(faction, (6, 6))
        base.save(Path(save_dir / f"{self}.png".casefold()))
        log.info(f"Saved newly rendered frame: {self}")
        return base

    @property
    def base_ascension(self):
        return self.tier.min_ascension

    @classmethod
    async def convert(cls, _ctx, arg: str):
        if ":" in arg:
            hero_arg, asc_arg = arg.split(":", maxsplit=1)
        elif "," in arg:
            hero_arg, asc_arg = arg.split(",", maxsplit=1)
        elif "." in arg:
            hero_arg, asc_arg = arg.split(".", maxsplit=1)
        else:
            asc = Ascension.get(arg)
            if asc:
                return cls.unknown(ascension=asc)

            hero_arg, asc_arg = arg, None

        if asc_arg:
            asc = Ascension.get(asc_arg)
            if not asc:
                raise commands.BadArgument
        else:
            asc = None

        faction = Faction.get(hero_arg)
        if faction:
            return cls.unknown(faction=faction, ascension=asc)

        if hero_arg in {"none", "n", "unknown", "unk", "?"}:
            return cls.unknown(ascension=asc)

        hero = cls.match(hero_arg)
        if not hero:
            raise commands.BadArgument

        if asc and hero.ascension.name != asc.name:
            return hero.copy(ascension=asc)
        return hero

    @classmethod
    def from_data(cls, data, ascension: t.Optional[Ascension] = None):
        data = dict(**data)
        name = data['name']
        faction: Faction = Faction.get(data['faction'])
        if not faction:
            raise ValueError(f"Faction not found for hero: {data}")
        tier: HeroTier = HeroTier.get(data['tier'])
        hero_type = HeroType.get(data['type'])
        hero_class = HeroClass.get(data['class']) if data['class'] else None
        primary = HeroRole.get(data['primary_role'])
        secondary = HeroRole.get(data['secondary_role']) if data['secondary_role'] else None

        hero: Hero = cls(name, faction, tier, hero_type, hero_class, primary, secondary, ascension)
        if hero.base_ascension == hero.ascension:
            base_hero = hero
        else:
            base_hero = hero.copy(ascension=hero.base_ascension)

        faction.heroes.add(base_hero)
        cls.cache[hero.name.casefold()] = base_hero
        cls.heroes[f"{hero}".casefold()] = hero
        return hero

    @classmethod
    def populate_cache(cls):
        for hero_data in cls._select_all():
            cls.from_data(hero_data)
        log.info("Hero cache has been populated.")

    @classmethod
    def get(cls, name: str, ascension: t.Optional[Ascension] = None) -> t.Optional[Hero]:
        if not cls.cache:
            cls.populate_cache()
        hero = cls.heroes.get(f"{name}:{ascension.name}".casefold())
        if not hero:
            base_hero = cls.cache.get(name.casefold())
            if not base_hero:
                return None
            hero = base_hero.copy(ascension=ascension or base_hero.base_ascension)

        return hero

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

    @classmethod
    def get_faction_heroes(cls, *factions: Faction, tier: HeroTier = None):
        if not cls.cache:
            cls.populate_cache()
        heroes = set()
        for faction in factions:
            for hero in faction.heroes:
                if not tier:
                    heroes.add(hero)
                elif hero.tier == tier:
                    heroes.add(hero)

        return heroes

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
            cls.populate_cache()
        result = process.extractOne(query.casefold(), cls.cache.keys(), score_cutoff=90)
        if result:
            return cls.cache[result[0]]
