from __future__ import annotations

import logging
import typing as t

from discord.ext import commands

from dreaf import db
from dreaf import ctx


log = logging.getLogger(__name__)


# class Guild(db.Table):
#     _instances: t.Dict[int, Guild] = dict()
#
#     def __init__(self, id: int):
#         self.id = id
#         self.settings = dict()
#
#     @property
#     def discord(self):
#         return ctx.
#
#     @staticmethod
#     def _create_table():
#         log.info("Ensuring table exists: guilds")
#         cursor = db.conn.execute(
#             """
#             CREATE TABLE IF NOT EXISTS guilds (
#               guild_id INT PRIMARY KEY,
#               name  INT NULL,
#               main BOOLEAN default TRUE,
#               name TEXT NULL
#             );
#             """
#         )
#         db.conn.commit()
#         cursor.close()
