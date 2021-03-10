import abc
import logging
import sqlite3

conn = sqlite3.connect("db.sqlite")

_all_tables = []


log = logging.getLogger(__name__)


class RecordNotFound(Exception):
    ...


class Table(abc.ABC):
    def __init_subclass__(cls, **kwargs):
        _all_tables.append(cls)
        cls._create_table()

    @staticmethod
    @abc.abstractmethod
    def _create_table():
        pass
