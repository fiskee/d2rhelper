from d2rhelper.parser import CharacterParser
from d2rhelper.ui import (
    render_character_page,
    render_equipped_card,
    render_mercenary_card,
    render_items_table,
)


def test_equipped_card_renders() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    equipped = [i for i in char.items if i.location == 1]
    assert len(equipped) == 10
    html = render_equipped_card(equipped)
    assert "equipment-grid" in html
    assert "Spirit" in html
    assert "Crystal Sword" in html
    assert "Stealth" in html
    assert "Lore" in html
    assert "Helm" in html
    assert "Shield" in html
    assert "Armor" in html


def test_mercenary_card_renders() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    assert len(char.mercenary.items) == 3
    html = render_mercenary_card(char.mercenary.items)
    assert "mercenary-grid" in html
    assert "Insight" in html
    assert "Bone Helm" in html
    assert "Quilted Armor" in html


def test_items_table_renders() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    html = render_items_table(char.items)
    assert "<table>" in html
    assert "Short Staff" in html


def test_full_page_renders() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    html = render_character_page(char, "tests/resources/Farming.d2s")
    assert "Farming" in html
    assert "lvl 63" in html
    assert "Sorceress" in html
