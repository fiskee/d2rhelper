from pathlib import Path

from sqlalchemy import create_engine, text

from d2rhelper.db import persist_character_snapshot
from d2rhelper.parser import CharacterParser


def test_persist_character_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    fixture = Path("tests/resources/Farming.d2s")
    character = CharacterParser().parse_file(fixture)

    snapshot_id = persist_character_snapshot(str(db_path), str(fixture), character)
    assert snapshot_id > 0

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        count = conn.execute(text("select count(*) from character_item_snapshot")).scalar_one()
        assert count == len(character.items)
