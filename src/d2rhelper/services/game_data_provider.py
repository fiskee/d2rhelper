from __future__ import annotations

from d2rhelper.game_data import GameData

_game_data: GameData | None = None


def get_game_data() -> GameData:
    global _game_data
    if _game_data is None:
        _game_data = GameData.get_instance()
    return _game_data


__all__ = ["get_game_data"]
