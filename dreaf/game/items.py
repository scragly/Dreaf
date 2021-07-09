import discord
from discord.ext import commands

from dreaf import db


class Item(db.Table):
    def __init__(self, name: str, description: str, emoji_id: int = None):
        self.name = name
        self.description = description
        self.emoji_id = emoji_id

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Item '{self.name}'>"

    @classmethod
    async def convert(cls, ctx, arg: str):
        item = cls.get(arg)
        if not item:
            try:
                emoji = await commands.EmojiConverter().convert(ctx, arg)
            except commands.EmojiNotFound:
                raise commands.BadArgument("Couldn't find item.")
            item = cls.get_by_emoji(emoji)
            if not item:
                raise commands.BadArgument("Couldn't find item.")
        return item

    @classmethod
    def get(cls, name: str):
        try:
            name, description, emoji = cls._select(name.casefold())
        except TypeError:
            return None
        return cls(name, description, emoji)

    @classmethod
    def get_all(cls, query: str = None):
        items = [cls(n, d, e) for (n, d, e) in cls._select_all(query)]
        return items

    @classmethod
    def get_by_emoji(cls, emoji: discord.Emoji):
        try:
            name, description, emoji = cls._select_by_emoji_id(emoji.id)
        except TypeError:
            return None
        return cls(name, description, emoji)

    def save(self):
        self._insert(self.name.casefold(), self.description, self.emoji_id)

    def delete(self):
        self._delete(self.name)

    def exists(self) -> bool:
        return bool(self.get(self.name))

    def is_dirty(self):
        item = self.get(self.name)
        if not item:
            return None
        return not (
            item.name.casefold() == self.name.casefold()
            and item.description.casefold() == self.description.casefold()
            and item.emoji_id == self.emoji_id
        )

    # region: SQL methods

    @staticmethod
    def _select(name):
        cursor = db.conn.execute(
            """
            SELECT name, description, emoji_id
            FROM items
            WHERE name = ?;
            """,
            [name]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_by_emoji_id(emoji_id):
        cursor = db.conn.execute(
            """
            SELECT name, description, emoji_id
            FROM items
            WHERE emoji_id = ?;
            """,
            [emoji_id]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    @staticmethod
    def _select_all(match_name: str):
        if match_name:
            cursor = db.conn.execute(
                """
                SELECT name, description, emoji_id
                FROM items
                WHERE name LIKE ?
                ORDER BY name;
                """,
                [f"%{match_name.casefold()}%"]
            )
        else:
            cursor = db.conn.execute("SELECT name, description, emoji_id FROM items ORDER BY name;")

        data = cursor.fetchall()
        cursor.close()
        return data

    @staticmethod
    def _insert(name, description, emoji_id):
        cursor = db.conn.execute(
            """
            INSERT INTO items(name, description, emoji_id) VALUES (?, ?, ?)
            ON CONFLICT(name)
            DO UPDATE SET
              description=excluded.description,
              emoji_id=excluded.emoji_id;
            """,
            [name, description, emoji_id]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _delete(name):
        cursor = db.conn.execute(
            """
            DELETE FROM items
            WHERE name = ?
            """,
            [name]
        )
        db.conn.commit()
        cursor.close()

    @staticmethod
    def _create_table():
        cursor = db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
              name TEXT PRIMARY KEY,
              description TEXT NULL,
              emoji_id INT NULL
            );
            """
        )
        cursor.close()

    # endregion
