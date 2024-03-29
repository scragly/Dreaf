from __future__ import annotations

import io
import logging
import random
import shutil
import typing as t
from collections import Counter
from pathlib import Path

import discord
from discord.ext import commands
from discord.ext.commands import MissingRequiredArgument, converter
from PIL import Image
from discord.ext import commands

from dreaf import checks
from dreaf.game.heroes import Ascension, Hero, HeroTier, Faction

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot


log = logging.getLogger(__name__)


class UnknownFaction:
    name = "unknown"
    emblem_cap = None
    aliases = ["unknown", "unk", "?", "blank", "placeholder", "any"]

    @property
    def frame_icon_img(self):
        return "faction_unknown.png"

    @classmethod
    def convert(cls, _ctx, arg: str):
        if arg in cls.aliases:
            return cls()


class HeroImg(commands.Cog, name="Hero Image"):
    """Commands relating to Image generation of Heroes."""

    def __init__(self, bot: DreafBot):
        self.bot = bot
        self._frames = Path("images/frames/")
        self._heroes = Path("images/heroes/")
        self._factions = Path("images/factions/")
        self._mask = Path("images/mask.png")
        self.bot.all_commands['heroes'] = self.hero_comp
        self.pull_counter = Counter()

    @staticmethod
    def img_to_file(img_data, *, name="image") -> discord.File:
        data = io.BytesIO()
        img_data.save(data, format="PNG")
        data.seek(0)
        file = discord.File(data, f"{name}.png")
        return file

    @commands.group(invoke_without_command=True)
    async def hero(self, ctx: commands.Context, hero: Hero, ascension: Ascension = None):
        await ctx.send(file=self.img_to_file(hero.img_tile(ascension), name="hero.png"))

    @hero.group(name="composition", aliases=["comp", "team"], invoke_without_command=True)
    async def hero_comp(self, ctx: commands.Context, *heroes: Hero):
        if not heroes:
            return

        if len(heroes) > 5:
            await ctx.send("Teams can only have a maximum of 5 heroes.")
            return

        images = [hero.img_tile() for hero in heroes if hero]
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths) + ((len(images) - 1) * 10)
        max_height = max(heights)
        img = Image.new('RGBA', (total_width, max_height))
        x_offset = 0
        for im in images:
            img.paste(im, (x_offset, 0))
            x_offset += im.size[0] + 10
        await ctx.send(file=self.img_to_file(img, name="comp"))

    @hero_comp.command(name="noasc")
    async def hero_nonecomp(self, ctx: commands.Context, *heroes: Hero):
        if not heroes:
            return

        if len(heroes) > 5:
            await ctx.send("Teams can only have a maximum of 5 heroes.")
            return

        images = [hero.copy(Ascension.none()).img_tile() for hero in heroes if hero]
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths) + ((len(images) - 1) * 10)
        max_height = max(heights)
        img = Image.new('RGBA', (total_width, max_height))
        x_offset = 0
        for im in images:
            img.paste(im, (x_offset, 0))
            x_offset += im.size[0] + 10
        await ctx.send(file=self.img_to_file(img, name="comp"))

    @hero_comp.error
    async def comp_error(self, ctx, error):
        raise error

    @hero.command(name="info")
    async def hero_info(self, ctx: commands.Context, hero: Hero):
        info = [f"Tier: {hero.tier.name}", f"Type: {hero.type.name}"]
        if hero.hero_class:
            info.append(f"Class: {hero.hero_class.name}")
        info.append(f"Primary Role: {hero.primary_role.name}")
        if hero.secondary_role:
            info.append(f"Secondary Role: {hero.secondary_role.name}")

        embed = discord.Embed(description="\n".join(info), colour=discord.Colour.blue())
        hero_img = self.img_to_file(hero.img_portrait(), name=hero.name)
        faction_img = self.img_to_file(hero.faction.img_icon(), name=hero.faction.name)
        embed.set_thumbnail(url=f"attachment://{hero_img.filename}")
        embed.set_author(name=hero.name, icon_url=f"attachment://{faction_img.filename}")
        await ctx.send(embed=embed, files=[hero_img, faction_img])

    def pull_hero(self, user_id: int) -> Hero:
        self.pull_counter[user_id] += 1
        is_celepogean = random.choices([True, False], weights=[1, 500], k=1)[0]
        if is_celepogean:
            factions = Faction.celepogeans()
            hero = random.choice([*Hero.get_faction_heroes(*factions)])
        else:
            if self.pull_counter[user_id] >= 30:
                tier = HeroTier.get("Ascended")
            else:
                tier = random.choices(
                    [
                        HeroTier.get("common"),
                        HeroTier.get("legendary"),
                        HeroTier.get("ascended")
                    ],
                    weights=[5169, 4370, 461],
                )[0]
            hero = random.choice([*Hero.get_faction_heroes(*Faction.four_factions(), tier=tier)])

        if hero.tier.name.casefold() == "ascended":
            self.pull_counter[user_id] = 0

        return hero

    @hero.command(name="pull")
    async def hero_pull(self, ctx: commands.Context, number: int = 10):
        if number > 10:
            await ctx.send("Sorry, can't pull that many heroes at once! Try 10 or less.")
            return

        await ctx.trigger_typing()

        heroes = []
        for _ in range(number):
            heroes.append(self.pull_hero(ctx.author.id))

        images = [hero.img_tile() for hero in heroes]
        widths, heights = zip(*(i.size for i in images))
        if len(images) > 5:
            total_height = (max(heights) * 2) + 10
            total_width = 790
        else:
            total_height = max(heights)
            total_width = sum(widths) + ((len(images) - 1) * 10)
        img = Image.new('RGBA', (total_width, total_height))
        x_offset = 0
        for i, im in enumerate(images):
            if i == 5:
                x_offset = 0
            if i >= 5:
                y_offset = max(heights) + 10
            else:
                y_offset = 0
            img.paste(im, (x_offset, y_offset))
            x_offset += im.size[0] + 10

        file = self.img_to_file(img)
        await ctx.send(file=file)

    @checks.is_owner()
    @hero.command(name="purge")
    async def hero_purge(self, ctx):
        """Purges all pre-rendered frames of heroes."""
        save_dir = Path(f"images/frames/rendered/")
        shutil.rmtree(save_dir)
        save_dir.mkdir(exist_ok=True)
        await ctx.send("All pre-rendered hero frames have been removed.")


def setup(bot):
    bot.add_cog(HeroImg(bot))
