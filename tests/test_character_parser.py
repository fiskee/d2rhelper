from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from d2rhelper.parser import CharacterParser, ParseError

if TYPE_CHECKING:
    from d2rhelper.models import D2Character


@pytest.fixture(scope="module")
def farming() -> D2Character:
    return CharacterParser().parse_file("tests/resources/Farming.d2s")


def test_file_header(farming) -> None:
    assert farming.file_data.version == 105
    assert farming.file_data.header == 0xAA55AA55


def test_identity(farming) -> None:
    assert farming.level == 63
    assert farming.name == "Farming"
    assert farming.character_type == "Sorceress"
    assert farming.status.hardcore is False
    assert farming.status.lord_of_destruction is False
    assert farming.status.reign_of_the_warlock is True


def test_attributes(farming) -> None:
    a = farming.attributes
    assert a.strength == 70
    assert a.dexterity == 25
    assert a.vitality == 245
    assert a.energy == 35
    assert a.hp == 641
    assert a.max_hp == 592
    assert a.mana == 358
    assert a.max_mana == 159
    assert a.level == 63
    assert a.experience == 155276313
    assert a.gold == 4537
    assert a.gold_in_stash == 437644


def test_skills(farming) -> None:
    skills = {s.name: s.level for s in farming.skills}
    assert len(skills) == 11
    assert skills["Blizzard"] == 20
    assert skills["Ice Blast"] == 20
    assert skills["Cold Mastery"] == 10
    assert skills["Glacial Spike"] == 13
    assert skills["Teleport"] == 1


def test_waypoints(farming) -> None:
    wp = {w.difficulty: w.waypoints for w in farming.waypoints}
    assert len(wp["normal"]) == 28
    assert len(wp["nightmare"]) == 25
    assert len(wp["hell"]) == 1
    assert "Worldstone Keep" in wp["normal"]
    assert "Harrogath" in wp["nightmare"]
    assert "Rogue Encampment" in wp["hell"]
    assert "Cold Plains" not in wp["hell"]


def test_quests(farming) -> None:
    q = {q.difficulty: q for q in farming.quest_data}
    assert q["normal"].den_of_evil is True
    assert q["normal"].radament is True
    assert q["normal"].resistance_scroll is True
    assert q["nightmare"].den_of_evil is True
    assert q["nightmare"].socket_quest_available is True
    assert q["hell"].den_of_evil is False


def test_items(farming) -> None:
    assert farming.item_count == 42
    assert len(farming.items) == 42
    assert all(i.parse_ok for i in farming.items)


def test_merc(farming) -> None:
    assert len(farming.mercenary.items) == 3
    codes = [i.code for i in farming.mercenary.items]
    assert "qui" in codes
    assert "bhm" in codes
    assert "9vo" in codes


def test_unsupported_version() -> None:
    data = bytes([0x55, 0xAA, 0x55, 0xAA]) + (0).to_bytes(4, "little") + b"\x00" * 400
    with pytest.raises(ParseError, match="Unsupported version"):
        CharacterParser().parse_bytes(data)


def test_wrong_header() -> None:
    data = b"\x00" * 400
    with pytest.raises(ParseError, match="Wrong fileHeader"):
        CharacterParser().parse_bytes(data)


def test_parse_merc_items_failure_returns_none() -> None:
    parser = CharacterParser()
    data = b"\x00" * 200 + b"jfJM\x00\x00"
    result = parser._parse_merc_items(data, 0)
    assert result in (None, [])
