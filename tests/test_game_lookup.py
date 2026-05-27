from __future__ import annotations

from d2rhelper.services.game_data_provider import get_game_data
from d2rhelper.services.game_lookup import list_class_skills, lookup_game_item, lookup_skill_data


def test_lookup_skill_data_warlock() -> None:
    result = lookup_skill_data(get_game_data(), "Miasma Chains", "warlock")
    assert result is not None
    assert result["name"] == "Miasma Chains"
    assert result["class_code"] == "war"
    assert result["required_level"] == 12
    assert result["tree"] == {"tab_index": 3, "row": 3, "column": 3}
    assert result["prerequisites"] == ["Miasma Bolt"]
    assert result["damage_formula"]["emin"] == "6"
    assert result["damage_formula"]["emax"] == "9"
    assert result["damage_formula"]["hitshift"] == "8"
    assert result["damage_formula"]["edmgsympercalc"] == "(skill('Miasma Bolt'.blvl)+skill('Abyss'.blvl))*par8"
    assert {s["skill"] for s in result["synergy_sources"]} == {"Miasma Bolt", "Abyss"}


def test_list_class_skills_warlock_has_expected_shape() -> None:
    result = list_class_skills(get_game_data(), "warlock")
    assert result["class_code"] == "war"
    assert result["total_skills"] == 30
    assert len(result["skills"]) == 30
    by_name = {s["name"]: s for s in result["skills"]}
    assert by_name["Summon Goatman"]["required_level"] == 1
    assert by_name["Abyss"]["required_level"] == 30
    assert by_name["Abyss"]["tree"] == {"tab_index": 3, "row": 6, "column": 3}


def test_lookup_game_item_runeword() -> None:
    result = lookup_game_item(get_game_data(), "Spirit", "rw")
    assert result is not None
    assert result["quality"] == "runeword"
    assert result["name"] == "Spirit"
    assert result["base_hint"] == "4-Socket Item"
    assert result["runes"] == ["Tal", "Thul", "Ort", "Amn"]
    assert "+2 to All Skills" in result["properties"]
