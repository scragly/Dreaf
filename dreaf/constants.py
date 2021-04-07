import logging
import os
import sys

from everstone import db

from dreaf import db as sqlite_db

_log = logging.getLogger(__name__)

GUILD_ID: int = 732785236273922069
PREFIX = '!'
TOKEN = ''
EMOJI_DELETE = 685111560930197534
EMOJI_PROMPT_TICK = '\u2705'
EMOJI_PROMPT_CROSS = '\u274e'
EXEMPLAR_ROLE = 732795761762238514
DEPUTY_ROLE = 732786956106334238
MASTER_ROLE = 732789199354200134
MEMBER_LOG_CHANNEL = 815347771052785714
LAB_PATH_CHANNEL = 815586417631428658
AFK_FEED_CHANNEL = 815603266652995605
AFK_CODE_FEED_CHANNEL = 814452504247009310
BOT_SPAM_CHANNEL = 809789367153328188
CODE_CHANNEL = 817608299842371654
DB_NAME = 'dreaf'
DB_USER = 'dreaf'
DB_PASSWORD = ''
DB_HOST = 'localhost'
DB_PORT = '5432'


class PersistentGlobals(sqlite_db.Table):

    def __init__(self):
        self._cache = dict()

    def get(self, key):
        data = self._select(key)
        return data[0] if data else None

    def set(self, key, value):
        self[key] = value

    def __getitem__(self, key):
        data = self._select(key)
        if data:
            return data[0]
        else:
            raise KeyError

    def __setitem__(self, key, value):
        self._insert(key, value)

    def _select(self, key):
        if key in self._cache:
            return tuple([self._cache[key]])

        cursor = sqlite_db.conn.execute(
            """
            SELECT value
            FROM persistent_globals
            WHERE key = ?;
            """,
            [key]
        )
        data = cursor.fetchone()
        cursor.close()
        return data

    def _insert(self, key, value):
        cursor = sqlite_db.conn.execute(
            """
            INSERT INTO persistent_globals(key, value) VALUES (?, ?)
            ON CONFLICT(key)
            DO UPDATE SET
              value=excluded.value;
            """,
            [key, value]
        )
        sqlite_db.conn.commit()
        cursor.close()
        self._cache[key] = value

    @staticmethod
    def _create_table():
        _log.info("Ensuring table exists: persistent_globals")
        cursor = sqlite_db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS persistent_globals (
              key TEXT PRIMARY KEY,
              value TEXT NULL
            );
            """
        )
        cursor.close()


persistent_globals = PersistentGlobals()


def load_envs():
    dreaf_envvars = {k.split("DREAF_", 1)[1]: v for k, v in os.environ.items() if k.startswith("DREAF_")}
    global DB_PASSWORD
    DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", '')
    for setting, value in dreaf_envvars.items():
        module = sys.modules[__name__]
        setting_type = type(getattr(module, setting))
        setattr(module, setting, setting_type(value))


load_envs()

# db.connect(DB_NAME, DB_USER, DB_PASSWORD, host=DB_HOST, port=DB_PORT)
