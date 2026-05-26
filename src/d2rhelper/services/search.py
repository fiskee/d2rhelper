from __future__ import annotations

from typing import Any

from d2rhelper.models import D2Character, ItemQuality, SharedStashTab


class SearchService:
    def __init__(self) -> None:
        self._autocomplete_cache: list[str] | None = None

    def get_autocomplete_items(self, gd: Any) -> list[str]:
        if self._autocomplete_cache is None:
            self._autocomplete_cache = build_autocomplete_items(gd)
        return self._autocomplete_cache


def build_autocomplete_items(gd: Any) -> list[str]:
    names: set[str] = set()

    for table in ("weapons", "armor", "misc"):
        rows = gd.conn.execute(f'SELECT "name" FROM "{table}" WHERE "name" != \'\'').fetchall()
        for row in rows:
            name = str(row["name"])
            if name:
                names.add(name)

    for row in gd.conn.execute('SELECT "index" FROM uniqueitems WHERE "spawnable" = \'1\'').fetchall():
        name = str(row["index"])
        if name:
            names.add(name)

    for row in gd.conn.execute('SELECT "index" FROM setitems').fetchall():
        name = str(row["index"])
        if name:
            names.add(name)

    for row in gd.conn.execute('SELECT "x_rune_name" FROM runes WHERE "complete" = \'1\'').fetchall():
        name = str(row["x_rune_name"])
        if name:
            names.add(name)

    return sorted(names)


def autocomplete_matches(items: list[str], query: str) -> list[str]:
    ql = query.lower()
    matches = [name for name in items if ql in name.lower()]
    matches.sort(key=lambda n: (0 if n.lower().startswith(ql) else 1, n.lower()))
    return matches[:10]


def search_items(query: str, parsed: dict[str, Any]) -> list[dict[str, Any]]:
    q = query.lower()
    results: list[dict[str, Any]] = []

    char = D2Character.model_validate(parsed["character"])
    tabs = [SharedStashTab.model_validate(t) for t in parsed["stash_tabs"]]

    quality_names = {v.value: v.name for v in ItemQuality}

    all_sources: list[tuple[Any, str, int | None]] = []
    all_sources.append((char.items, "character", None))
    all_sources.append((char.mercenary.items, "mercenary", None))
    for i, tab in enumerate(tabs):
        all_sources.append((tab.items, f"stash_tab_{i + 1}", i))

    for items, source, tab_idx in all_sources:
        for item in items:
            score = 0
            name = (item.display_name or item.item_name or "").lower()
            item_name = (item.item_name or "").lower()
            set_name = (item.set_name or "").lower()
            rw_name = (item.runeword_name or "").lower()
            uniq_name = (item.unique_name or "").lower()
            code = (item.code or "").lower()
            quality_str = quality_names.get(item.quality, "").lower()

            if name == q:
                score += 100
            elif name.startswith(q):
                score += 50
            elif q in name:
                score += 20

            if q in item_name:
                score += 15
            if q in set_name:
                score += 40
            if q in rw_name:
                score += 40
            if q in uniq_name:
                score += 40
            if q in code:
                score += 5
            if q in quality_str:
                score += 5

            for prop in item.properties:
                if (prop.display_text or "").lower().find(q) >= 0:
                    score += 30
                    break

            if score > 0:
                results.append({
                    "item": item.model_dump(mode="json"),
                    "source": source,
                    "tab_index": tab_idx,
                    "score": score,
                })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:50]


_search_service = SearchService()


def get_search_service() -> SearchService:
    return _search_service


__all__ = [
    "SearchService",
    "autocomplete_matches",
    "build_autocomplete_items",
    "get_search_service",
    "search_items",
]
