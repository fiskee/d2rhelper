from __future__ import annotations

from typing import Any


class SetsService:
    def __init__(self) -> None:
        self._sets_cache: list[dict[str, Any]] | None = None

    def get_sets(self, gd: Any) -> list[dict[str, Any]]:
        if self._sets_cache is not None:
            return self._sets_cache

        code_to_name: dict[str, str] = {}
        for table in ("weapons", "armor", "misc"):
            rows = gd.conn.execute(f'SELECT code, name FROM "{table}" WHERE name != \'\'').fetchall()
            for row in rows:
                code_to_name[row["code"]] = row["name"]

        rows = gd.conn.execute('SELECT "index", item, "set" FROM setitems WHERE "set" != \'\' ORDER BY "set", "index"').fetchall()

        sets: dict[str, dict[str, Any]] = {}
        for row in rows:
            set_name: str = row["set"]
            piece_name: str = row["index"]
            code: str = row["item"]
            base_name = code_to_name.get(code, code)

            if set_name not in sets:
                sets[set_name] = {
                    "name": set_name,
                    "items": [],
                }
            sets[set_name]["items"].append({
                "name": piece_name,
                "code": code,
                "base": base_name,
            })

        self._sets_cache = list(sets.values())
        return self._sets_cache


_sets_service = SetsService()


def get_sets_service() -> SetsService:
    return _sets_service


__all__ = ["SetsService", "get_sets_service"]
