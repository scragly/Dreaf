from __future__ import annotations

import logging

from everstone import db, types, constraints
from everstone.model import Column

log = logging.getLogger(__name__)


class User(db.Model):
    _table = db.Table("users")
    _table.Column(db.type.Integer, constraint=db.)

    def __init__(self):
        id = Column(Integer, primary_key=True)
    role = Column(String)

    @property
    def api_session(self):
        return session.AFKSession.get(self.id)

    @property
    def players(self):
        return Player.select()

    @property
    def main_player(self) -> Player:

        return await self.players.query.where(User.id==self.id, main=True).gino.one_or_none()


class Character(db.Model):
    __tablename__ = 'players'

    id: Column(types.Integer)
    name: str = Column(types.)
    server = Column(Integer)
    level = Column(Integer)
    main = Column(Boolean)
    last_updated = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))

    @property
    def api_session(self):
        return self.user.api_session

    @classmethod
    async def from_data(cls, *, uid, name, svr_id, level, is_main, **kwargs):
        if kwargs:
            log.warning(f"Additional Player data encountered in payload.\n{kwargs}")

        return cls.create(
            id=uid,
            name=name,
            server=svr_id,
            level=level,
            main=is_main,
            last_updated=pendulum.now(),
        )
