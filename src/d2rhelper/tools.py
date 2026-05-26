from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ItemRecord:
    id: str
    data: dict[str, Any]
    location: str
    tab_index: int | None = None
    owner: str | None = None


@dataclass
class CharacterContextStore:
    character_overview: dict[str, Any] | None = None
    character_items: list[ItemRecord] = field(default_factory=list)
    stash_items: list[ItemRecord] = field(default_factory=list)
    include_all: bool = False

    _id_lookup: dict[str, ItemRecord] = field(default_factory=dict)

    def _add_items(self, items: list[dict], location: str, tab_index: int | None = None, owner: str | None = None) -> None:
        for item in items:
            rec = ItemRecord(
                id=str(item.get("id", "")),
                data=item,
                location=location,
                tab_index=tab_index,
                owner=owner,
            )
            self.character_items.append(rec)
            if rec.id:
                self._id_lookup[rec.id] = rec

    def _add_stash_items(self, items: list[dict], tab_index: int, owner: str | None = None) -> None:
        for item in items:
            rec = ItemRecord(
                id=str(item.get("id", "")),
                data=item,
                location=f"stash_tab_{tab_index}",
                tab_index=tab_index,
                owner=owner,
            )
            self.stash_items.append(rec)
            if rec.id:
                self._id_lookup[rec.id] = rec

    def lookup(self, item_id: str) -> ItemRecord | None:
        return self._id_lookup.get(item_id)

    @classmethod
    def from_json(cls, payload: str) -> CharacterContextStore:
        obj = json.loads(payload)
        store = cls()
        store.include_all = bool(obj.get("other_characters"))

        char_data = obj.get("character")
        char_map = [("main", char_data)]
        if store.include_all:
            for oc in obj.get("other_characters", []):
                char_map.append((oc.get("name", oc.get("path", "?")), oc))

        all_skills: list[dict] = []
        equipment_summary: dict[str, dict[str, Any]] = {}
        merc_summary: dict[str, Any] | None = None

        for owner_name, cd in char_map:
            if cd is None:
                continue
            equip = cd.get("equipment", {})
            if isinstance(equip, dict):
                for slot, item in equip.items():
                    if isinstance(item, dict):
                        if owner_name == "main":
                            equipment_summary[slot] = _make_item_summary(item)
                        store._add_items([item], f"equipped/{slot}", owner=owner_name if owner_name != "main" else None)
            for loc_key, loc_label in [("belt", "belt"), ("inventory", "inventory"), ("cube", "cube"), ("personal_stash", "personal_stash")]:
                items = cd.get(loc_key, [])
                if isinstance(items, list):
                    store._add_items(items, loc_label, owner=owner_name if owner_name != "main" else None)

            if owner_name == "main":
                for skill in cd.get("skills", []) or []:
                    if isinstance(skill, dict) and skill.get("level", 0) > 0:
                        all_skills.append(dict(skill))
                merc = cd.get("mercenary")
                if merc and isinstance(merc, dict) and merc.get("name"):
                    merc_eq: dict[str, dict[str, Any]] = {}
                    for me in merc.get("equipment", []) or []:
                        slot = me.get("slot", "?")
                        item = me.get("item", {})
                        if isinstance(item, dict):
                            merc_eq[slot] = _make_item_summary(item)
                            store._add_items([item], f"mercenary/{slot}")
                    merc_summary = {
                        "name": merc.get("name"),
                        "type": merc.get("subtype"),
                        "skills": merc.get("skills", []),
                        "experience": merc.get("experience"),
                        "equipment": merc_eq,
                    }

                charm_bases = {"Small Charm", "Large Charm", "Grand Charm"}
                charms = [
                    _make_item_summary(item)
                    for item in (cd.get("inventory", []) or [])
                    if isinstance(item, dict) and item.get("base") in charm_bases
                ]
                store.character_overview = {
                    "name": cd.get("name"),
                    "level": cd.get("level"),
                    "class": cd.get("character_type"),
                    "hardcore": (cd.get("status") or {}).get("hardcore", False) if isinstance(cd.get("status"), dict) else False,
                    "progression": _progression_text(cd.get("act_progression")),
                    "attributes": {k: cd["attributes"].get(k) for k in ("strength", "dexterity", "vitality", "energy", "life", "max_hp", "mana", "max_mana", "stat_points_left", "skill_points_left")} if isinstance(cd.get("attributes"), dict) else {},
                    "skills": all_skills,
                    "equipment": equipment_summary,
                    "charms": charms,
                    "mercenary": merc_summary,
                    "quests": _summarize_quests(cd.get("quest_data", []) or []),
                    "waypoints": _summarize_waypoints(cd.get("waypoints", []) or []),
                }

        for tab in obj.get("stash_tabs", []) or []:
            if isinstance(tab, dict):
                store._add_stash_items(tab.get("items", []) or [], tab.get("index", 0))

        if store.include_all:
            for owner_name, cd in char_map:
                if cd is None or owner_name == "main":
                    continue
                personal = cd.get("personal_stash", []) or []
                if isinstance(personal, list) and personal:
                    store._add_stash_items(personal, f"{owner_name}_personal", owner=owner_name)

        return store

    def get_all_items_for_search(self, scope: str) -> tuple[list[ItemRecord], str]:
        if scope == "character":
            return self.character_items, "character"
        else:
            return self.stash_items, "stash"


def _make_item_summary(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    summary: dict[str, Any] = {
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "quality": item.get("quality", ""),
    }
    for f in ("base", "damage", "ethereal"):
        if item.get(f):
            summary[f] = item[f]
    if item.get("req"):
        summary["req"] = item["req"]
    if item.get("sockets"):
        summary["sockets"] = item["sockets"]
    if item.get("socketed"):
        summary["socketed"] = item["socketed"]
    if item.get("properties"):
        summary["properties"] = item["properties"]
    return summary


def _progression_text(ap: Any) -> str:
    try:
        val = int(ap)
    except (TypeError, ValueError):
        return "Unknown"
    if val >= 15:
        return "Hell (Guardian)"
    if val == 14:
        return "Hell (Complete)"
    if val >= 10:
        return f"Hell Act {(val - 10) + 1}"
    if val == 9:
        return "Nightmare (Complete)"
    if val >= 5:
        return f"Nightmare Act {(val - 5) + 1}"
    if val == 4:
        return "Normal (Complete)"
    return f"Normal Act {val + 1}"


def _summarize_quests(quest_data: list[dict]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    try:
        for q in quest_data:
            diff = q.get("difficulty", "?")
            result[diff] = {
                "den_of_evil": q.get("den_of_evil", False),
                "radament": q.get("radament", False),
                "golden_bird": q.get("golden_bird", False),
                "socket_quest_available": q.get("socket_quest_available", False),
                "resistance_scroll": q.get("resistance_scroll", False),
            }
    except Exception:
        pass
    return result


def _summarize_waypoints(waypoints: list[dict]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    try:
        for w in waypoints:
            diff = w.get("difficulty", "?")
            result[diff] = w.get("waypoints", []) or []
    except Exception:
        pass
    return result


def _item_search_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("name", "base", "quality"):
        val = item.get(key)
        if val:
            parts.append(str(val).lower())
    for sub in item.get("socketed", []) or []:
        parts.append(str(sub).lower())
    for prop in item.get("properties", []) or []:
        parts.append(str(prop).lower())
    return " ".join(parts)


def _score_item(item: dict[str, Any], keywords: list[str]) -> int:
    score = 0
    name = str(item.get("name", "")).lower()
    base = str(item.get("base", "")).lower()
    props_lower = [str(p).lower() for p in (item.get("properties", []) or [])]
    socketed_lower = [str(s).lower() for s in (item.get("socketed", []) or [])]

    for kw in keywords:
        if kw == name:
            score += 100
        elif name.startswith(kw):
            score += 60
        elif kw in name:
            score += 30

        if kw == base:
            score += 50
        elif kw in base:
            score += 20

        for prop in props_lower:
            if kw == prop:
                score += 40
            elif kw in prop:
                score += 15
                break

        for sock in socketed_lower:
            if kw in sock:
                score += 10
                break

    return score


def search_items(query: str | list[str], store: CharacterContextStore, scope: str) -> dict[str, Any]:
    items, _ = store.get_all_items_for_search(scope)

    if isinstance(query, list):
        queries = [str(q).strip().lower() for q in query if str(q).strip()]
    elif isinstance(query, str):
        q = query.strip().lower()
        queries = [q] if q else []
    else:
        return {"matches": [], "total_found": 0, "shown": 0}

    if not queries:
        return {"matches": [], "total_found": 0, "shown": 0}

    if len(queries) == 1:
        keywords = [w for w in queries[0].split() if w]
        scored: list[tuple[int, ItemRecord]] = []
        for rec in items:
            search_text = _item_search_text(rec.data)
            if not any(kw in search_text for kw in keywords):
                continue
            score = _score_item(rec.data, keywords)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:25]
        matches = _format_matches(top)
        return {"matches": matches, "total_found": len(scored), "shown": len(matches)}

    per_query: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    total_items = 0

    for qtext in queries:
        keywords = [w for w in qtext.split() if w]
        scored: list[tuple[int, ItemRecord]] = []
        for rec in items:
            search_text = _item_search_text(rec.data)
            if not any(kw in search_text for kw in keywords):
                continue
            score = _score_item(rec.data, keywords)
            if score > 0:
                scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:10]
        total_items += len(scored)
        for _, rec in top:
            seen_ids.add(rec.id)
        per_query.append({
            "query": qtext,
            "matches": _format_matches(top),
            "total_found": len(scored),
            "shown": len(top),
        })

    return {"queries": per_query, "total_found": total_items, "unique_items": len(seen_ids)}


def _format_matches(scored: list[tuple[int, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for _, rec in scored:
        item_data = dict(rec.data)
        item_data["location"] = rec.location
        if rec.tab_index is not None:
            item_data["tab_index"] = rec.tab_index
        if rec.owner:
            item_data["owner"] = rec.owner
        matches.append(item_data)
    return matches


def get_item_details(item_id: str, store: CharacterContextStore) -> dict[str, Any]:
    rec = store.lookup(item_id)
    if rec is None:
        return {"found": False, "item_id": item_id}
    item_data = dict(rec.data)
    item_data["location"] = rec.location
    if rec.tab_index is not None:
        item_data["tab_index"] = rec.tab_index
    if rec.owner:
        item_data["owner"] = rec.owner
    return {"found": True, "item": item_data}


def get_character_overview(store: CharacterContextStore) -> dict[str, Any]:
    if store.character_overview is None:
        return {"error": "No character data available"}
    return store.character_overview


def get_mercenary_overview(store: CharacterContextStore) -> dict[str, Any]:
    overview = store.character_overview
    if overview is None:
        return {"found": False}
    merc = overview.get("mercenary")
    if merc is None:
        return {"found": False, "reason": "No mercenary hired"}
    return {"found": True, **merc}


def get_materials_summary(store: CharacterContextStore) -> dict[str, Any]:
    runes: dict[str, int] = {}
    gems: dict[str, int] = {}
    essences: dict[str, int] = {}
    keys: dict[str, int] = {}

    _GEM_QUALITIES = ("Chipped", "Flawed", "Flawless", "Perfect")
    _GEM_TYPES = ("Amethyst", "Diamond", "Emerald", "Ruby", "Sapphire", "Topaz", "Skull")
    _KNOWN_GEMS: set[str] = set()
    for g in _GEM_TYPES:
        _KNOWN_GEMS.add(g)
        for q in _GEM_QUALITIES:
            _KNOWN_GEMS.add(f"{q} {g}")
    _KNOWN_ESSENCES = {
        "Twisted Essence of Suffering",
        "Charged Essence of Hatred",
        "Burning Essence of Terror",
        "Festering Essence of Destruction",
    }
    _KNOWN_KEYS = {
        "Key of Terror",
        "Key of Hate",
        "Key of Destruction",
    }

    all_items = store.stash_items + [i for i in store.character_items if i.location == "personal_stash"]

    for rec in all_items:
        name = str(rec.data.get("name", ""))
        count = max(int(rec.data.get("stacks", 1) or 1), 1)
        name_lower = name.lower()

        if name_lower.endswith(" rune"):
            rune_name = name[:-5].strip()
            runes[rune_name] = runes.get(rune_name, 0) + count
            continue

        if name in _KNOWN_GEMS:
            gems[name] = gems.get(name, 0) + count
            continue

        if name in _KNOWN_ESSENCES:
            essences[name] = essences.get(name, 0) + count
            continue

        if name in _KNOWN_KEYS:
            keys[name] = keys.get(name, 0) + count
            continue

    result: dict[str, Any] = {}
    if runes:
        result["runes"] = {k: runes[k] for k in sorted(runes)}
    if gems:
        result["gems"] = {k: gems[k] for k in sorted(gems)}
    if essences:
        result["essences"] = {k: essences[k] for k in sorted(essences)}
    if keys:
        result["keys"] = {k: keys[k] for k in sorted(keys)}

    return result if result else {"note": "No materials found in stash"}


TOOL_DEFINITIONS = [
    {
        "name": "get_character_overview",
        "description": "Get the player's current character snapshot: name, level, class, attributes, skills (with levels), equipped items (each with id, name, quality, base, requirements, sockets, socketed runes/gems, and all properties), inventory charms (Small/Large/Grand), quest progress, unlocked waypoints, and mercenary summary.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_mercenary_overview",
        "description": "Get the mercenary's name, type, skills, experience, and equipped items (each with id, name, quality, base, requirements, sockets, and top properties). Call this when you need detailed mercenary information.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_materials_summary",
        "description": "Get a compact inventory of ALL crafting materials across personal and shared stashes: rune counts (by name without 'Rune' suffix), gem counts (by full name including quality prefix), essences, and keys. Returns counts not individual items — use this instead of search_stash for seeing what runes, gems, essences, and keys the player owns. Run this early when evaluating what the player can craft.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "search_character_items",
        "description": "Search the player's equipped items, inventory, belt, Horadric Cube, and personal stash for items matching queries. Accepts a single string or an array of strings — batch multiple searches in one call (e.g. ['Spirit', 'fire resist', 'Sol rune']). Uses keywords: item name, runeword name, unique name, base type, rune name, gem type, or property text. ALWAYS call this before making recommendations about gear, runewords, or item usage.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "anyOf": [
                        {"type": "string", "description": "A single keyword search"},
                        {"type": "array", "items": {"type": "string"}, "description": "Multiple keyword searches to batch"},
                    ],
                    "description": "One or more search queries to find items by name, type, or property",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_stash",
        "description": "Search all shared stash tabs (and other characters' personal stashes if 'All characters' mode is active) for items matching queries. Accepts a single string or an array of strings — batch multiple searches in one call (e.g. ['Sol rune', 'Crystal Sword', 'Ruby', 'Grand Charm']). Same keyword search as search_character_items. ALWAYS call this before suggesting runewords, crafting, or anything that requires materials.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "anyOf": [
                        {"type": "string", "description": "A single keyword search"},
                        {"type": "array", "items": {"type": "string"}, "description": "Multiple keyword searches to batch"},
                    ],
                    "description": "One or more search queries to find items by name, type, or property",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_item_details",
        "description": "Get complete stats for a specific item by its ID. Use the 'id' field from search_character_items or search_stash results. Call this when you need to verify specific properties of an item before making a recommendation.",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The item's ID from search results, e.g. 'i3'",
                }
            },
            "required": ["item_id"],
        },
    },
]


def execute_tool_call(name: str, args: dict[str, Any], store: CharacterContextStore) -> dict[str, Any]:
    if name == "get_character_overview":
        return get_character_overview(store)
    elif name == "get_mercenary_overview":
        return get_mercenary_overview(store)
    elif name == "get_materials_summary":
        return get_materials_summary(store)
    elif name == "search_character_items":
        return search_items(args.get("query", ""), store, "character")
    elif name == "search_stash":
        return search_items(args.get("query", ""), store, "stash")
    elif name == "get_item_details":
        return get_item_details(args.get("item_id", ""), store)
    else:
        return {"error": f"Unknown tool: {name}"}
