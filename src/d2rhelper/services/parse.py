from __future__ import annotations

import os
from typing import Any

from d2rhelper.parser import CharacterParser
from d2rhelper.shared_stash_parser import SharedStashParser


class ParseService:
    def __init__(self) -> None:
        self._parse_cache: dict[str, dict[str, Any]] = {}
        self._parse_mtime: dict[str, float] = {}

    def parse_files(self, character_path: str, stash_path: str | None = None) -> dict[str, Any]:
        cache_key = f"{character_path}::{stash_path or ''}"

        try:
            char_mtime = os.path.getmtime(character_path)
        except OSError:
            char_mtime = 0

        if cache_key in self._parse_cache and self._parse_mtime.get(cache_key) == char_mtime:
            return self._parse_cache[cache_key]

        character = CharacterParser().parse_file(character_path)
        tabs = []
        if stash_path:
            try:
                tabs = SharedStashParser().parse_file(stash_path)
            except (FileNotFoundError, PermissionError, OSError, ValueError):
                tabs = []

        result = {
            "character": character.model_dump(mode="json"),
            "stash_tabs": [tab.model_dump(mode="json") for tab in tabs],
        }
        self._parse_cache[cache_key] = result
        self._parse_mtime[cache_key] = char_mtime
        return result


_parse_service = ParseService()


def get_parse_service() -> ParseService:
    return _parse_service


__all__ = ["ParseService", "get_parse_service"]
