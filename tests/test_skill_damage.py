from __future__ import annotations

from d2rhelper.services.game_data_provider import get_game_data
from d2rhelper.services.skill_damage import estimate_skill_damage


def test_estimate_skill_damage_blizzard_reference_values() -> None:
    result = estimate_skill_damage(
        get_game_data(),
        class_name="sorceress",
        skill_name="Blizzard",
        skill_level=20,
        plus_skills=5,
        synergy_levels={"Ice Bolt": 13, "Ice Blast": 20, "Glacial Spike": 20},
        enemy_resist=0,
    )

    assert result["ok"] is True
    assert result["skill_name"] == "Blizzard"
    assert abs(result["final_damage_min"] - 3011.25) < 0.01
    assert abs(result["final_damage_max"] - 3208.35) < 0.01


def test_estimate_skill_damage_ice_blast_hitshift_applied() -> None:
    result = estimate_skill_damage(
        get_game_data(),
        class_name="sorceress",
        skill_name="Ice Blast",
        skill_level=20,
        plus_skills=5,
        synergy_levels={"Ice Bolt": 13, "Blizzard": 20},
        enemy_resist=0,
    )

    assert result["ok"] is True
    assert result["skill_name"] == "Ice Blast"
    assert abs(result["final_damage_min"] - 1379.56) < 0.01
    assert abs(result["final_damage_max"] - 1437.8) < 0.01
    assert any("hitshift" in note for note in result["assumptions"])
