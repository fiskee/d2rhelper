from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from d2rhelper.bit_reader import BitReader
from d2rhelper.item_parser import ItemParser
from d2rhelper.models import ItemQuality

if TYPE_CHECKING:
    from d2rhelper.models import ParsedItem


# ── Huffman / simple items ────────────────────────────────────────────

def test_potion_huffman() -> None:
    br = BitReader(bytes([16, 0, 160, 8, 21, 36, 0, 207, 175, 0]))
    it = ItemParser()._parse_item(0, br)
    assert it.code == "hp4"
    assert it.item_name == "Greater Healing Potion"
    assert it.simple is True


def test_mana_potion() -> None:
    br = BitReader(bytes([16, 0, 160, 0, 5, 212, 196, 78, 180, 0]))
    it = ItemParser()._parse_item(0, br)
    assert it.code == "mp5"
    assert it.item_name == "Super Mana Potion"
    assert it.simple is True


# ── Runeword (NORMAL quality) ─────────────────────────────────────────

def test_runeword_ancients_pledge() -> None:
    bytes_ = bytes(
        [16, 8, 128, 4, 77, 21, 96, 190, 109, 203, 195, 166, 19, 180, 136, 23,
         216, 128, 178, 1, 20, 19, 115, 34, 90, 138, 104, 43, 162, 181, 136,
         246, 31, 130, 140, 19, 213, 82, 84, 91, 49, 175, 69, 53, 57, 202, 127,
         16, 0, 160, 0, 53, 0, 224, 124, 35, 1, 16, 0, 160, 0, 53, 4, 224, 124,
         187, 0, 16, 0, 160, 0, 53, 8, 224, 124, 251, 0])
    it = ItemParser()._parse_item(0, BitReader(bytes_))
    assert it.code == "pa3"
    assert it.simple is False
    assert it.quality == ItemQuality.NORMAL
    assert it.runeword is True
    assert it.cnt_filled_sockets == 3
    assert len(it.properties) > 0


# ── Requirements ──────────────────────────────────────────────────────

def test_weapon_requirements() -> None:
    p = ItemParser()
    req_str, req_dex, req_level = p._item_requirements("crs", False, [])
    assert req_str == 43
    assert req_level == 11
    assert req_dex is None


def test_armor_requirements() -> None:
    p = ItemParser()
    req_str, req_dex, req_level = p._item_requirements("plt", False, [])
    assert req_str == 65
    assert req_level == 24


def test_ethereal_reduces_reqs() -> None:
    p = ItemParser()
    req_str, __, req_level = p._item_requirements("crs", True, [])
    assert req_str == 33


def test_weapon_damage_text() -> None:
    p = ItemParser()
    dmg = p._weapon_damage_text("vou", [])
    assert dmg == "2H 6-21"


# ── Advanced stash stackable detection ────────────────────────────────

def test_advanced_stash_detection() -> None:
    p = ItemParser()
    assert p._is_advanced_stash_stackable("r08") is True
    assert p._is_advanced_stash_stackable("gcy") is True
    assert p._is_advanced_stash_stackable("hp4") is False


# ── Property combining ────────────────────────────────────────────────

def test_combine_all_resists() -> None:
    from d2rhelper.models import ParsedItemProperty
    props = [
        ParsedItemProperty(index=39, name="fireresist", values=[15], display_text="Fire Resist +15%"),
        ParsedItemProperty(index=41, name="lightresist", values=[15], display_text="Lightning Resist +15%"),
        ParsedItemProperty(index=43, name="coldresist", values=[15], display_text="Cold Resist +15%"),
        ParsedItemProperty(index=45, name="poisonresist", values=[15], display_text="Poison Resist +15%"),
    ]
    ItemParser._combine_properties(props)
    texts = [p.display_text for p in props if p.display_text]
    assert texts == ["All Resistances +15%"]


def test_combine_enhanced_damage() -> None:
    from d2rhelper.models import ParsedItemProperty
    props = [
        ParsedItemProperty(index=18, name="item_mindamage_percent", values=[23]),
        ParsedItemProperty(index=17, name="item_maxdamage_percent", values=[23]),
    ]
    ItemParser._combine_properties(props)
    texts = [p.display_text for p in props if p.display_text]
    assert texts == ["+23% Enhanced Damage"]


def test_combine_min_max_damage() -> None:
    from d2rhelper.models import ParsedItemProperty
    props = [
        ParsedItemProperty(index=21, name="mindamage", values=[1]),
        ParsedItemProperty(index=22, name="maxdamage", values=[3]),
    ]
    ItemParser._combine_properties(props)
    texts = [p.display_text for p in props if p.display_text]
    assert texts == ["Adds 1-3 Damage"]


# ── Integration: exact counts from Farming.d2s ────────────────────────

@pytest.fixture(scope="module")
def char_items() -> list[ParsedItem]:
    from d2rhelper.parser import CharacterParser
    return CharacterParser().parse_file("tests/resources/Farming.d2s").items


@pytest.fixture(scope="module")
def stash_items() -> list[ParsedItem]:
    from d2rhelper.shared_stash_parser import SharedStashParser
    all_items = []
    for tab in SharedStashParser().parse_file("tests/resources/ModernSharedStashSoftCoreV2.d2i"):
        all_items.extend(tab.items)
    return all_items


def test_all_qualities_present(char_items) -> None:
    qualities = {it.quality for it in char_items if it.parse_ok}
    expected = {ItemQuality.NORMAL, ItemQuality.MAGIC, ItemQuality.RARE, ItemQuality.SET, ItemQuality.UNIQUE}
    missing = expected - qualities
    assert not missing, f"Missing quality types: {missing}"


def test_normal_items(char_items) -> None:
    normals = [it for it in char_items if it.quality == ItemQuality.NORMAL and it.parse_ok]
    assert len(normals) == 12


def test_magic_items(char_items) -> None:
    magics = [it for it in char_items if it.quality == ItemQuality.MAGIC and it.parse_ok]
    assert len(magics) == 7


def test_rare_items(char_items) -> None:
    rares = [it for it in char_items if it.quality == ItemQuality.RARE and it.parse_ok]
    assert len(rares) == 6


def test_unique_items(char_items) -> None:
    uniques = [it for it in char_items if it.quality == ItemQuality.UNIQUE and it.parse_ok]
    assert len(uniques) == 1
    assert uniques[0].unique_name == "Rakescar"


def test_set_items(char_items) -> None:
    sets = [it for it in char_items if it.quality == ItemQuality.SET and it.parse_ok]
    assert len(sets) == 1


def test_runewords(char_items) -> None:
    rws = [it for it in char_items if it.runeword and it.parse_ok]
    assert len(rws) == 5
    rw_names = {it.runeword_name for it in rws}
    assert rw_names == {"Spirit", "Stealth", "Lore", "Leaf", "Ancients' Pledge"}


def test_weapon_damage_on_weapons(char_items) -> None:
    weapons = [it for it in char_items if it.weapon_damage and it.parse_ok]
    assert len(weapons) == 5


def test_socket_counts(char_items) -> None:
    socketed = [it for it in char_items if it.cnt_sockets is not None and it.cnt_sockets > 0]
    assert len(socketed) == 7
    filled = [it for it in socketed if (it.cnt_filled_sockets or 0) > 0]
    assert len(filled) == 5


def test_advanced_stash_stack_counts(stash_items) -> None:
    stacked = [it for it in stash_items if it.stacks is not None]
    assert len(stacked) == 55


def test_parse_items_failure_adds_placeholder_and_warning() -> None:
    parser = ItemParser()
    data = b"JM\x01\x00" + b"\x00\x00"

    items = parser.parse_items(data, 0, len(data))

    assert len(items) == 1
    assert items[0].parse_ok is False
    assert items[0].code == "PARSE_ERROR"
    assert parser.warnings
