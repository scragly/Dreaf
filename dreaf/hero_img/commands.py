from __future__ import annotations

import io
import random
import typing as t
from collections import Counter
from pathlib import Path

import discord
from PIL import Image
from discord.ext import commands

from dreaf.heroes.model import Ascension, Faction, Hero, HeroTier

if t.TYPE_CHECKING:
    from dreaf.bot import DreafBot


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

    def hero_img(self, hero: Hero):
        return Image.open(self._frames / "heroes" / hero.hero_frame_img)

    def frame_img(self, faction: Faction, ascension: Ascension = None):
        faction_icon = Image.open(self._frames.joinpath(faction.frame_icon_img))
        ascension_frame = Image.open(self._frames.joinpath(ascension.frame_img))
        img = Image.alpha_composite(ascension_frame, faction_icon)
        if ascension.is_plus:
            frame_corners = Image.open(self._frames.joinpath(ascension.corner_img))
            img = Image.alpha_composite(img, frame_corners)
        return img

    def hero_frame(self, hero: Hero, ascension: Ascension = None):
        img = self.hero_img(hero)
        frame = self.frame_img(hero.faction, ascension)
        img = Image.alpha_composite(img, frame)
        return img

    @staticmethod
    def img_to_file(img_data, *, name="image"):
        data = io.BytesIO()
        img_data.save(data, format="PNG")
        data.seek(0)
        file = discord.File(data, f"{name}.png")
        return file

    @commands.group(invoke_without_command=True)
    async def hero(self, ctx: commands.Context, hero: Hero, ascension: Ascension = None):
        img = self.hero_frame(hero, ascension or hero.base_ascension)
        await ctx.send(file=self.img_to_file(img, name="hero.png"))

    @hero.command(name="test")
    async def test(self, ctx: commands.Context, hero: Hero):
        img = Image.open(self._heroes / f"{hero.name.casefold()}.png")
        mask = Image.open(self._mask)
        img.putalpha(mask)
        await ctx.send(file=self.img_to_file(img, name="hero"))

    @test.error
    async def test_error(self, ctx, error):
        await ctx.send(f"{error}")

    @hero.command(name="composition", aliases=["comp", "team"])
    async def hero_comp(self, ctx: commands.Context, *heroes: Hero):
        if not heroes:
            return

        if len(heroes) > 5:
            await ctx.send("Teams can only have a maximum of 5 heroes.")
            return

        images = [self.hero_frame(h, h.base_ascension) for h in heroes if h is not None]
        widths, heights = zip(*(i.size for i in images))
        total_width = sum(widths) + ((len(images) - 1) * 10)
        max_height = max(heights)
        img = Image.new('RGBA', (total_width, max_height))
        x_offset = 0
        for im in images:
            img.paste(im, (x_offset, 0))
            x_offset += im.size[0] + 10
        data = io.BytesIO()
        img.save(data, format="PNG")
        data.seek(0)
        file = discord.File(data, "hero.png")
        await ctx.send(file=file)

    @hero.command(name="info")
    async def hero_info(self, ctx: commands.Context, hero: Hero):
        info = [f"Tier: {hero.tier.name}", f"Type: {hero.type.name}"]
        if hero.hero_class:
            info.append(f"Class: {hero.hero_class.name}")
        info.append(f"Primary Role: {hero.primary_role.name}")
        if hero.secondary_role:
            info.append(f"Secondary Role: {hero.secondary_role.name}")

        embed = discord.Embed(description="\n".join(info), colour=discord.Colour.blue())
        hero_img = discord.File(self._heroes / f"{hero.name.casefold()}.png", "hero.png")
        faction_img = discord.File(self._factions / f"{hero.faction.name.casefold()}.png", "faction.png")
        embed.set_thumbnail(url="attachment://hero.png")
        embed.set_author(name=hero.name, icon_url="attachment://faction.png")

        await ctx.send(embed=embed, files=[hero_img, faction_img])

    def pull_hero(self, user_id: int) -> Hero:
        self.pull_counter[user_id] += 1
        if self.pull_counter[user_id] >= 30:
            tier = HeroTier.get("ascended")
        else:
            tier = random.choices(
                [HeroTier.get("common"), HeroTier.get("legendary"), HeroTier.get("ascended")],
                weights=[5169, 4370, 461],
            )[0]

        if tier.name == HeroTier.get("ascended").name:
            self.pull_counter[user_id] = 0
            is_celehypo = random.choices([True, False], weights=[20, 441])[0]
            if is_celehypo:
                heroes = Hero.get_by_tier(tier, cele=True, hypo=True, std=False)
            else:
                heroes = Hero.get_by_tier(tier)

        else:
            heroes = Hero.get_by_tier(tier)

        return random.choices(heroes)[0]

    @hero.command(name="pull")
    async def hero_pull(self, ctx: commands.Context, number: int = 10):
        if number > 10:
            await ctx.send("Sorry, can't pull that many heroes at once! Try 10 or less.")
            return

        await ctx.trigger_typing()

        heroes = []
        for _ in range(number):
            heroes.append(self.pull_hero(ctx.author.id))

        images = [self.hero_frame(h, h.base_ascension) for h in heroes]
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
        data = io.BytesIO()
        img.save(data, format="PNG")
        data.seek(0)
        file = discord.File(data, "pull.png")
        await ctx.send(file=file)
