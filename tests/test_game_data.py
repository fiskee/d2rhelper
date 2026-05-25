from d2rhelper.game_data import DEFAULT_DB_PATH, GameData


def test_game_data_load() -> None:
    gd = GameData()
    assert gd.db_path == DEFAULT_DB_PATH


def test_skill_lookups() -> None:
    gd = GameData()
    assert gd.skill_name(36) == "Fire Bolt"
    assert gd.skill_name(0) == "Attack"
    assert gd.skill_class_name(36) == "Sorceress"
    assert gd.skill_class_name(66) == "Necromancer"


def test_skill_offsets() -> None:
    gd = GameData()
    offsets = gd.skill_offsets("Amazon")
    assert len(offsets) == 30
    assert offsets[0] == (0, "Magic Arrow")


def test_player_classes() -> None:
    gd = GameData()
    assert gd.class_name_by_id(0) == "Amazon"
    assert gd.class_name_by_id(1) == "Sorceress"
    assert gd.class_name_by_id(7) == "Warlock"
    classes = gd.player_classes()
    assert len(classes) == 8


def test_item_lookups() -> None:
    gd = GameData()
    assert gd.weapon_by_code("hax") is not None
    assert gd.armor_by_code("cap") is not None
    assert gd.misc_by_code("hp1") is not None


def test_stat_cost() -> None:
    gd = GameData()
    isc = gd.item_stat_cost(0)
    assert isc is not None
    assert isc.get("stat") == "strength"


def test_runewords() -> None:
    gd = GameData()
    rw = gd.runeword_by_string("TalThulOrtAmn")
    assert rw is not None
    assert rw["name"] == "Spirit"


def test_tooltips() -> None:
    gd = GameData()
    assert gd.property_tooltip("dexterity") == "+# to Dexterity"


def test_unique_and_set() -> None:
    gd = GameData()
    assert gd.unique_name(0) == "The Gnasher"
    assert gd.set_name(0) == "Civerb's Ward"
