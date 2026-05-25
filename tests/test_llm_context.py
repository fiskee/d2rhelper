from d2rhelper.llm_context import build_llm_context
from d2rhelper.parser import CharacterParser
from d2rhelper.shared_stash_parser import SharedStashParser


def test_llm_context_structure() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    try:
        tabs = SharedStashParser().parse_file("tests/resources/ModernSharedStashSoftCoreV2.d2i")
    except Exception:
        tabs = []
    ctx = build_llm_context(char, tabs)

    assert set(ctx.keys()) == {"character", "equipped", "belt", "inventory", "personal_stash", "mercenary", "shared_stash"}


def test_llm_character_section() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    ctx = build_llm_context(char, [])

    c = ctx["character"]
    assert c["name"] == "Farming"
    assert c["class"] == "Sorceress"
    assert c["level"] == 63
    assert c["stats"]["strength"] == 70
    assert c["stats"]["vitality"] == 245
    assert len(c["skills"]) == 11
    assert c["skills"]["Blizzard"] == 20


def test_llm_equipped_section() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    ctx = build_llm_context(char, [])

    eq = {it.get("slot"): it for it in ctx["equipped"] if it.get("slot")}
    assert len(eq) == 10
    assert eq["Weapon"]["runeword"] == "Spirit"
    assert eq["Helm"]["runeword"] == "Lore"
    assert eq["Armor"]["runeword"] == "Stealth"


def test_llm_item_fields() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    ctx = build_llm_context(char, [])

    weapon = next(it for it in ctx["equipped"] if it.get("slot") == "Weapon")
    assert weapon["name"] == "Crystal Sword"
    assert weapon["code"] == "crs"
    assert weapon["runeword"] == "Spirit"
    assert weapon["sockets_total"] == 4
    assert weapon["sockets_filled"] == 4
    assert weapon["sockets_free"] == 0
    assert weapon["requirements"] == {"level": 11, "strength": 43}
    assert "properties" in weapon


def test_llm_stash_structure() -> None:
    char = CharacterParser().parse_file("tests/resources/Farming.d2s")
    tabs = SharedStashParser().parse_file("tests/resources/ModernSharedStashSoftCoreV2.d2i")
    ctx = build_llm_context(char, tabs)

    assert len(ctx["shared_stash"]) == 6
    assert ctx["shared_stash"][5]["items"][0]["quantity"] is not None
