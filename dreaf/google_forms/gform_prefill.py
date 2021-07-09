import abc
from yarl import URL

import discord

from dreaf.players import Player


class GoogleForm(abc.ABC):
    _base_url = "https://docs.google.com/forms/d/e/{id}/viewform"
    _entries = dict()
    id = ''

    @classmethod
    def add_entry(cls, entry_id, value):
        cls._entries[f"entry.{entry_id}"] = value

    @property
    def url(self):
        url = URL(self._base_url.format(id=self.id))
        return str(url.with_query(self.entries))

    @property
    @abc.abstractmethod
    def entries(self):
        pass


class AFKPlayerSurveyForm(GoogleForm):
    id = "1FAIpQLSey_aOfmmWkeulZ9tRt-XcQCLwYkU4msLzCIi4yErp50Gm5Aw"

    def __init__(self, member: discord.Member):
        self.discord_user = str(member)

        players = Player.get_by_discord_id(member.id)
        if not players:
            players = None
        if len(players) > 1:
            player = Player.get_main(member.id)
            if not player:
                player = players[0]
        else:
            player = players[0]

        self.game_id = player.game_id if player else None

    @property
    def entries(self):
        data = {
            "entry.725259971": "Discord",
            "entry.523287930": self.discord_user
        }
        if self.game_id:
            data["entry.1163618491"] = self.game_id

        return data
