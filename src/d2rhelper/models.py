from __future__ import annotations

from datetime import UTC, datetime
from enum import IntEnum

from pydantic import BaseModel, Field


class ItemQuality(IntEnum):
    NONE = 0
    INFERIOR = 1
    NORMAL = 2
    SUPERIOR = 3
    MAGIC = 4
    SET = 5
    RARE = 6
    UNIQUE = 7
    CRAFT = 8
    UNKNOWN = -99


class FileData(BaseModel):
    header: int
    version: int
    file_size: int
    checksum: int
    unknown: int


class CharacterStatus(BaseModel):
    hardcore: bool
    died: bool
    lord_of_destruction: bool
    reign_of_the_warlock: bool


class CharacterLocation(BaseModel):
    difficulty: str
    active: bool
    act: int


class Mercenary(BaseModel):
    alive_flag: int
    merc_id: int
    name_id: int
    type_id: int
    experience: int
    hireling_name: str | None = None
    hireling_subtype: str | None = None
    hireling_skills: list[str] = Field(default_factory=list)
    items: list[ParsedItem] = Field(default_factory=list)


class CharacterAttributes(BaseModel):
    strength: int = 0
    dexterity: int = 0
    vitality: int = 0
    energy: int = 0
    stat_points_left: int = 0
    skill_points_left: int = 0
    hp: int = 0
    max_hp: int = 0
    mana: int = 0
    max_mana: int = 0
    stamina: int = 0
    max_stamina: int = 0
    level: int = 0
    experience: int = 0
    gold: int = 0
    gold_in_stash: int = 0


class Skill(BaseModel):
    name: str
    level: int


class QuestData(BaseModel):
    difficulty: str
    den_of_evil: bool = False
    radament: bool = False
    golden_bird: bool = False
    siege_completed: bool = False
    socket_quest_available: bool = False
    resistance_scroll: bool = False


class WaypointStatus(BaseModel):
    difficulty: str
    waypoints: list[str] = Field(default_factory=list)


class ParsedItemProperty(BaseModel):
    index: int
    name: str
    values: list[int]
    display_name: str | None = None
    display_text: str | None = None
    quality_flag: int = 0
    order: int = 0


class ParsedItem(BaseModel):
    index: int
    start_bit: int
    end_bit: int
    location: int
    position: int
    x: int
    y: int
    container: int
    code: str | None = None
    item_name: str | None = None
    display_name: str | None = None
    runeword_name: str | None = None
    unique_name: str | None = None
    set_name: str | None = None
    weapon_damage: str | None = None
    raw_flags: int
    identified: bool = False
    socketed: bool = False
    ear: bool = False
    simple: bool = False
    ethereal: bool = False
    personalized: bool = False
    runeword: bool = False
    req_level: int | None = None
    req_str: int | None = None
    req_dex: int | None = None
    quality: ItemQuality = ItemQuality.UNKNOWN
    level: int | None = None
    cnt_filled_sockets: int | None = None
    cnt_sockets: int | None = None
    stacks: int | None = None
    max_stacks: int | None = None
    socketed_items: list[ParsedItem] = Field(default_factory=list)
    properties: list[ParsedItemProperty] = Field(default_factory=list)
    parse_ok: bool = True
    recovered: bool = False


class D2Character(BaseModel):
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    file_data: FileData
    name: str
    status: CharacterStatus
    act_progression: int
    character_type: str
    level: int
    map_id: int
    locations: list[CharacterLocation]
    mercenary: Mercenary
    attributes: CharacterAttributes = Field(default_factory=CharacterAttributes)
    skills: list[Skill] = Field(default_factory=list)
    quest_data: list[QuestData] = Field(default_factory=list)
    waypoints: list[WaypointStatus] = Field(default_factory=list)
    raw_skill_block_start: int | None = None
    item_list_start: int | None = None
    item_count: int = 0
    items: list[ParsedItem] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)


class CharacterInfo(BaseModel):
    path: str
    name: str
    character_type: str
    level: int
    hardcore: bool
    mtime: float | None = None


class SharedStashTab(BaseModel):
    index: int
    version: int
    gold: int
    length_in_bytes: int
    item_count: int = 0
    items: list[ParsedItem] = Field(default_factory=list)
