from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from d2rhelper.models import D2Character


class Base(DeclarativeBase):
    pass


class ParseSnapshot(Base):
    __tablename__ = "parse_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum_hex: Mapped[str] = mapped_column(String(16), nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False, default="0.1.0")

    characters: Mapped[list[CharacterSnapshot]] = relationship(back_populates="snapshot")


class CharacterSnapshot(Base):
    __tablename__ = "character_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("parse_snapshot.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    character_type: Mapped[str] = mapped_column(String(32), nullable=False)
    act_progression: Mapped[int] = mapped_column(Integer, nullable=False)
    map_id: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    snapshot: Mapped[ParseSnapshot] = relationship(back_populates="characters")
    items: Mapped[list[CharacterItemSnapshot]] = relationship(back_populates="character")


class CharacterItemSnapshot(Base):
    __tablename__ = "character_item_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("character_snapshot.id"), nullable=False
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    item_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    identified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    simple: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    container: Mapped[int] = mapped_column(Integer, nullable=False)
    start_bit: Mapped[int] = mapped_column(Integer, nullable=False)
    end_bit: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_flags: Mapped[int] = mapped_column(Integer, nullable=False)

    character: Mapped[CharacterSnapshot] = relationship(back_populates="items")


def create_sqlite_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", future=True)


def create_schema(db_path: str) -> None:
    engine = create_sqlite_engine(db_path)
    Base.metadata.create_all(engine)


def persist_character_snapshot(db_path: str, source_path: str, character: D2Character) -> int:
    engine = create_sqlite_engine(db_path)
    Base.metadata.create_all(engine)

    checksum_hex = f"{character.file_data.checksum:08x}"

    with Session(engine) as session:
        snapshot = ParseSnapshot(
            source_path=source_path,
            file_type="d2s",
            checksum_hex=checksum_hex,
            parsed_at=datetime.now(UTC),
        )
        session.add(snapshot)
        session.flush()

        row = CharacterSnapshot(
            snapshot_id=snapshot.id,
            name=character.name,
            level=character.level,
            character_type=character.character_type,
            act_progression=character.act_progression,
            map_id=character.map_id,
            payload=character.model_dump(mode="json"),
        )
        session.add(row)
        session.flush()

        for item in character.items:
            session.add(
                CharacterItemSnapshot(
                    character_snapshot_id=row.id,
                    item_index=item.index,
                    code=item.code,
                    quality=item.quality.name,
                    item_level=item.level,
                    identified=1 if item.identified else 0,
                    simple=1 if item.simple else 0,
                    location=item.location,
                    position=item.position,
                    x=item.x,
                    y=item.y,
                    container=item.container,
                    start_bit=item.start_bit,
                    end_bit=item.end_bit,
                    raw_flags=item.raw_flags,
                )
            )
        session.commit()
        return snapshot.id
