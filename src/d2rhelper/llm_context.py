from __future__ import annotations

import json
import sys
from pathlib import Path

from d2rhelper.models import D2Character, ParsedItem, SharedStashTab


def build_llm_context(
    character: D2Character,
    shared_stash_tabs: list[SharedStashTab] | None = None,
) -> dict:
    attr = character.attributes
    shared_stash_tabs = shared_stash_tabs or []

    equipped = [it for it in character.items if it.location == 1]
    belt = [it for it in character.items if it.location == 2]
    inventory = [it for it in character.items if it.location == 0 and it.container == 1]
    personal_stash = [it for it in character.items if it.location == 0 and it.container == 5]

    return {
        "character": {
            "name": character.name,
            "class": character.character_type,
            "level": character.level,
            "act_progression": character.act_progression,
            "hardcore": character.status.hardcore,
            "expansion": "Reign of the Warlock" if character.status.reign_of_the_warlock else "Lord of Destruction" if character.status.lord_of_destruction else "Classic",
            "stats": {
                "strength": attr.strength,
                "dexterity": attr.dexterity,
                "vitality": attr.vitality,
                "energy": attr.energy,
                "hp_current": attr.hp,
                "hp_max": attr.max_hp,
                "mana_current": attr.mana,
                "mana_max": attr.max_mana,
                "stat_points_available": attr.stat_points_left,
                "skill_points_available": attr.skill_points_left,
                "gold": attr.gold,
                "gold_in_stash": attr.gold_in_stash,
            },
            "skills": {s.name: s.level for s in character.skills if s.level > 0},
            "waypoints": {w.difficulty: w.waypoints for w in character.waypoints},
            "quests": [q.model_dump(mode="json") for q in character.quest_data],
        },
        "equipped": [_compact_item(it) for it in equipped],
        "belt": [_compact_item(it) for it in belt],
        "inventory": [_compact_item(it) for it in inventory],
        "personal_stash": [_compact_item(it) for it in personal_stash],
        "mercenary": {
            "type_id": character.mercenary.type_id,
            "alive": bool(character.mercenary.alive_flag),
            "equipment": [_compact_item(it) for it in character.mercenary.items],
        },
        "shared_stash": [
            {"tab": tab.index + 1, "gold": tab.gold, "items": [_compact_item(it) for it in tab.items]}
            for tab in shared_stash_tabs
        ],
    }


def _compact_item(item: ParsedItem) -> dict:
    socketed_names = [si.item_name or si.code or "?" for si in item.socketed_items]

    props = []
    for p in item.properties:
        if p.display_text:
            props.append(p.display_text)

    result: dict = {
        "name": item.item_name,
        "code": item.code,
        "quality": item.quality.name if item.quality.name != "UNKNOWN" else None,
        "identified": item.identified,
        "ethereal": item.ethereal,
        "level": item.level,
    }
    if item.stacks is not None:
        result["quantity"] = item.stacks
    if item.runeword_name:
        result["runeword"] = item.runeword_name
    if item.unique_name:
        result["unique"] = item.unique_name
    if item.set_name:
        result["set"] = item.set_name
    if socketed_names:
        result["socketed"] = socketed_names
    if item.cnt_sockets is not None and item.cnt_sockets > 0:
        result["sockets_total"] = item.cnt_sockets
        result["sockets_filled"] = item.cnt_filled_sockets or 0
        result["sockets_free"] = (item.cnt_sockets) - (item.cnt_filled_sockets or 0)
    if item.weapon_damage:
        result["weapon_damage"] = item.weapon_damage
    if item.req_str or item.req_dex or item.req_level:
        req: dict = {}
        if item.req_level is not None:
            req["level"] = item.req_level
        if item.req_str is not None:
            req["strength"] = item.req_str
        if item.req_dex is not None:
            req["dexterity"] = item.req_dex
        result["requirements"] = req
    if props:
        result["properties"] = props
    if item.position >= 1:
        from d2rhelper.ui import ITEM_SLOT_NAMES
        result["slot"] = ITEM_SLOT_NAMES.get(item.position)
    # Remove None values
    return {k: v for k, v in result.items() if v is not None}


def generate_llm_json(
    character_file: str | Path,
    stash_file: str | Path | None = None,
    output: str | Path | None = None,
) -> str:
    from d2rhelper.parser import CharacterParser
    from d2rhelper.shared_stash_parser import SharedStashParser

    char = CharacterParser().parse_file(str(character_file))
    tabs = []
    if stash_file:
        try:
            tabs = SharedStashParser().parse_file(str(stash_file))
        except Exception as exc:
            print(
                f"Warning: failed to parse shared stash '{stash_file}': {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

    context = build_llm_context(char, tabs)
    json_str = json.dumps(context, indent=2, ensure_ascii=False)
    if output:
        Path(output).write_text(json_str, encoding="utf-8")
    return json_str
