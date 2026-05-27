from __future__ import annotations

import json

from d2rhelper.tools import CharacterContextStore, execute_tool_call


def _sample_store() -> CharacterContextStore:
    payload = {
        "character": {
            "name": "Tester",
            "level": 80,
            "character_type": "Sorceress",
            "status": {"hardcore": False},
            "attributes": {"strength": 50, "dexterity": 40, "vitality": 200, "energy": 100},
            "skills": [{"name": "Blizzard", "level": 20}],
            "equipment": {
                "mainhand": {
                    "id": "i-main",
                    "name": "Spirit Crystal Sword",
                    "quality": "runeword",
                    "base": "Crystal Sword",
                    "properties": ["+2 to All Skills"],
                }
            },
            "inventory": [
                {
                    "id": "i-inv",
                    "name": "Small Charm",
                    "quality": "magic",
                    "base": "Small Charm",
                    "properties": ["+7% Magic Find"],
                }
            ],
            "belt": [],
            "cube": [],
            "personal_stash": [],
            "quest_data": [],
            "waypoints": [],
        },
        "stash_tabs": [
            {
                "index": 1,
                "items": [
                    {"id": "i-rune", "name": "Sol Rune", "quality": "normal", "properties": []},
                    {"id": "i-gem", "name": "Perfect Topaz", "quality": "normal", "properties": []},
                ],
            }
        ],
    }
    return CharacterContextStore.from_json(json.dumps(payload))


def test_execute_tool_call_calculate_skill_damage() -> None:
    store = _sample_store()
    result = execute_tool_call(
        "calculate_skill_damage",
        {
            "class_name": "sorceress",
            "skill_name": "Blizzard",
            "skill_level": 20,
            "plus_skills": 5,
            "synergy_levels": {"Ice Bolt": 13, "Ice Blast": 20, "Glacial Spike": 20},
            "enemy_resist": 0,
        },
        store,
    )

    assert result["ok"] is True
    assert result["skill_name"] == "Blizzard"
    assert abs(result["final_damage_min"] - 3011.25) < 0.01
    assert abs(result["final_damage_max"] - 3208.35) < 0.01


def test_execute_tool_call_lookup_skill_data() -> None:
    store = _sample_store()
    result = execute_tool_call(
        "lookup_skill_data",
        {"skill_name": "Blizzard", "class_name": "sorceress"},
        store,
    )

    assert result["ok"] is True
    assert result["name"] == "Blizzard"


def test_execute_tool_call_lookup_game_item() -> None:
    store = _sample_store()
    result = execute_tool_call(
        "lookup_game_item",
        {"item_name": "Spirit", "item_type": "rw"},
        store,
    )

    assert result["ok"] is True
    assert result["item"]["quality"] == "runeword"


def test_execute_tool_call_list_class_skills() -> None:
    store = _sample_store()
    result = execute_tool_call(
        "list_class_skills",
        {"class_name": "warlock"},
        store,
    )

    assert result["ok"] is True
    assert result["class_code"] == "war"
    assert result["total_skills"] == 30


def test_execute_tool_call_lookup_tool_input_validation() -> None:
    store = _sample_store()

    missing_skill = execute_tool_call("lookup_skill_data", {}, store)
    assert missing_skill["ok"] is False
    assert "skill_name" in missing_skill["error"]

    missing_class = execute_tool_call("list_class_skills", {}, store)
    assert missing_class["ok"] is False
    assert "class_name" in missing_class["error"]

    missing_item = execute_tool_call("lookup_game_item", {}, store)
    assert missing_item["ok"] is False
    assert "item_name" in missing_item["error"]


def test_execute_tool_call_character_overview_and_mercenary() -> None:
    store = _sample_store()
    overview = execute_tool_call("get_character_overview", {}, store)
    assert overview["name"] == "Tester"
    assert overview["class"] == "Sorceress"

    merc = execute_tool_call("get_mercenary_overview", {}, store)
    assert merc["found"] is False


def test_execute_tool_call_searches_and_item_details() -> None:
    store = _sample_store()

    char_search = execute_tool_call("search_character_items", {"query": "spirit"}, store)
    assert char_search["total_found"] == 1
    assert char_search["shown"] == 1
    assert any(m.get("name") == "Spirit Crystal Sword" for m in char_search["matches"])

    stash_search = execute_tool_call("search_stash", {"query": ["sol rune", "topaz"]}, store)
    assert stash_search["total_found"] == 2
    assert stash_search["unique_items"] == 2
    assert len(stash_search["queries"]) == 2

    details = execute_tool_call("get_item_details", {"item_id": "i-main"}, store)
    assert details["found"] is True
    assert details["item"]["name"] == "Spirit Crystal Sword"


def test_execute_tool_call_materials_summary_and_unknown_tool() -> None:
    store = _sample_store()
    mats = execute_tool_call("get_materials_summary", {}, store)
    assert mats["runes"]["Sol"] == 1
    assert mats["gems"]["Perfect Topaz"] == 1

    unknown = execute_tool_call("no_such_tool", {}, store)
    assert "error" in unknown
