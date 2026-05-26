from __future__ import annotations

from pathlib import Path

from d2rhelper.item_parser import ItemParser
from d2rhelper.models import (
    CharacterAttributes,
    CharacterLocation,
    CharacterStatus,
    D2Character,
    FileData,
    Mercenary,
    ParsedItem,
    ParsedItemProperty,
    QuestData,
    Skill,
    WaypointStatus,
)
from d2rhelper.game_data import GameData


class ParseError(ValueError):
    pass


class CharacterParser:
    SUPPORTED_VERSION = 105
    MIN_FILE_SIZE = 335
    SKILL_BLOCK_SCAN_START = 870
    SKILL_BLOCK_SCAN_END = 933
    SKILL_BLOCK_LENGTH = 30
    ATTR_BLOCK_START = 833
    QUEST_START = 403
    WAYPOINT_BLOCK_START = 709
    WAYPOINT_BLOCK_SIZE = 24
    WAYPOINT_BIT_OFFSET = 16
    DIFFICULTIES = ["normal", "nightmare", "hell"]

    def __init__(self, game_data: GameData | None = None) -> None:
        self.game_data = game_data or GameData.get_instance()
        self.item_parser = ItemParser(self.game_data)

    DEFAULT_CLASS_NAMES: dict[int, str] = {
        0: "Amazon",
        1: "Sorceress",
        2: "Necromancer",
        3: "Paladin",
        4: "Barbarian",
        5: "Druid",
        6: "Assassin",
    }

    def parse_file(self, file_path: str | Path) -> D2Character:
        data = Path(file_path).read_bytes()
        return self.parse_bytes(data)

    @staticmethod
    def read_character_info(file_path: str | Path) -> dict | None:
        try:
            path = Path(file_path)
            if not path.is_file():
                return None
            data = path.read_bytes()
            if len(data) < 315:
                return None
            header = int.from_bytes(data[0:4], byteorder="little", signed=False)
            if header != 0xAA55AA55:
                return None
            version = int.from_bytes(data[4:8], "little", signed=False)
            if version != CharacterParser.SUPPORTED_VERSION:
                return None
            status_byte = data[20]
            hardcore = bool(status_byte & (1 << 2))
            class_id = data[24]
            character_type = CharacterParser.DEFAULT_CLASS_NAMES.get(class_id, "Unknown")
            level = data[27]
            name_bytes = data[299:315]
            null_pos = name_bytes.find(b"\x00")
            if null_pos >= 0:
                name_bytes = name_bytes[:null_pos]
            name = name_bytes.decode("ascii", errors="replace").strip()
            if not name:
                name = path.stem
            mtime = path.stat().st_mtime
            return {
                "path": str(path),
                "name": name,
                "character_type": character_type,
                "level": level,
                "hardcore": hardcore,
                "mtime": mtime,
            }
        except Exception:
            return None

    def parse_bytes(self, data: bytes) -> D2Character:
        if len(data) < self.MIN_FILE_SIZE:
            raise ParseError(
                f"Less than {self.MIN_FILE_SIZE} bytes read ({len(data)}), either the file is locked, or this is not a valid .d2s file"
            )

        header = int.from_bytes(data[0:4], byteorder="little", signed=False)
        if header != 0xAA55AA55:
            raise ParseError(
                f"Wrong fileHeader {header}, this is not a Diablo II saveGame file"
            )

        file_data = FileData(
            header=header,
            version=int.from_bytes(data[4:8], "little", signed=False),
            file_size=int.from_bytes(data[8:12], "little", signed=False),
            checksum=int.from_bytes(data[12:16], "little", signed=False),
            unknown=int.from_bytes(data[16:20], "little", signed=False),
        )

        if file_data.version != self.SUPPORTED_VERSION:
            raise ParseError(f"Unsupported version: {file_data.version}")

        status_byte = data[20]
        status = CharacterStatus(
            hardcore=bool(status_byte & (1 << 2)),
            died=bool(status_byte & (1 << 3)),
            lord_of_destruction=bool(status_byte & (1 << 5)),
            reign_of_the_warlock=(data[248] == 3),
        )

        class_id = data[24]
        character_type = self.game_data.class_name_by_id(class_id)
        if character_type is None:
            raise ParseError(f"Unknown character class id: {class_id}")

        locations = [
            self._parse_location(self.DIFFICULTIES[0], data[152]),
            self._parse_location(self.DIFFICULTIES[1], data[153]),
            self._parse_location(self.DIFFICULTIES[2], data[154]),
        ]

        name = data[299:315].decode("ascii", errors="ignore").strip("\x00 ")
        merc = Mercenary(
            alive_flag=self._read_u16(data, 161),
            merc_id=self._read_u32(data, 163),
            name_id=self._read_u16(data, 167),
            type_id=self._read_u16(data, 169),
            experience=self._read_u32(data, 171),
        )
        hireling = self.game_data.hireling_by_id(merc.type_id)
        if hireling:
            merc.hireling_name = hireling["hireling"]
            merc.hireling_subtype = hireling["x_subtype"]
            merc.hireling_skills = hireling["skills"]

        skill_block_start = self._find_skill_block_start(data)
        item_list_start, item_count = self._find_item_list(data, skill_block_start)
        items = []
        warnings = []
        if item_list_start is not None:
            items = self.item_parser.parse_items(data, item_list_start, len(data))
            warnings = list(self.item_parser.warnings)
            merc_items = self._parse_merc_items(data, item_list_start)
            if merc_items is not None:
                merc.items = merc_items

        attributes = self._parse_attributes(data, skill_block_start)
        skills = self._parse_skills(data, skill_block_start, character_type)
        quests = self._parse_quest_data(data)
        waypoints = self._parse_waypoints(data)

        self._resolve_set_bonuses(items, merc.items)

        return D2Character(
            file_data=file_data,
            name=name,
            status=status,
            act_progression=data[21],
            character_type=character_type,
            level=data[27],
            map_id=int.from_bytes(data[155:163], "little", signed=False),
            locations=locations,
            mercenary=merc,
            attributes=attributes,
            skills=skills,
            quest_data=quests,
            waypoints=waypoints,
            raw_skill_block_start=skill_block_start,
            item_list_start=item_list_start,
            item_count=item_count,
            items=items,
            parse_warnings=warnings,
        )

    @staticmethod
    def _parse_location(difficulty: str, byte_value: int) -> CharacterLocation:
        active = bool(byte_value & (1 << 7))
        act = byte_value & 0b00000111
        return CharacterLocation(difficulty=difficulty, active=active, act=act)

    @staticmethod
    def _find_skill_block_start(data: bytes) -> int | None:
        if len(data) < CharacterParser.SKILL_BLOCK_SCAN_END + 2:
            return None
        for idx in range(CharacterParser.SKILL_BLOCK_SCAN_START, CharacterParser.SKILL_BLOCK_SCAN_END):
            if data[idx:idx + 2] == b"if":
                return idx
        return None

    @staticmethod
    def _find_item_list(data: bytes, skill_block_start: int | None) -> tuple[int | None, int]:
        if skill_block_start is None:
            return None, 0
        item_index = skill_block_start + 32
        if item_index + 4 > len(data):
            return None, 0
        if data[item_index:item_index + 2] != b"JM":
            return None, 0
        count = int.from_bytes(data[item_index + 2:item_index + 4], "little", signed=False)
        return item_index, count

    def _parse_merc_items(self, data: bytes, character_item_start: int) -> list[ParsedItem] | None:
        merc_header = data.find(b"jfJM", character_item_start)
        if merc_header < 0:
            return None
        merc_item_start = merc_header + 2
        iron_header = data.find(b"kf", merc_item_start)
        end = iron_header if iron_header > merc_item_start else len(data)
        try:
            return self.item_parser.parse_items(data, merc_item_start, end)
        except Exception as exc:
            self.item_parser.warnings.append(f"mercenary item parse failed: {type(exc).__name__}: {exc}")
            return None

    def _parse_attributes(self, data: bytes, skill_block_start: int | None) -> CharacterAttributes:
        if skill_block_start is None or len(data) < 865:
            return CharacterAttributes()

        stats_start = self.ATTR_BLOCK_START
        stats_end = skill_block_start
        if stats_end - stats_start < 4:
            return CharacterAttributes()

        stat_bytes = data[stats_start:stats_end]
        if stat_bytes[:2] != b"gf":
            return CharacterAttributes()

        stat_data = stat_bytes[2:]

        ATTR_LIST = [
            ("strength", 10, 1),
            ("energy", 10, 1),
            ("dexterity", 10, 1),
            ("vitality", 10, 1),
            ("stat_points_left", 10, 1),
            ("skill_points_left", 8, 1),
            ("hp", 21, 256),
            ("max_hp", 21, 256),
            ("mana", 21, 256),
            ("max_mana", 21, 256),
            ("stamina", 21, 256),
            ("max_stamina", 21, 256),
            ("level", 7, 1),
            ("experience", 32, 1),
            ("gold", 25, 1),
            ("gold_in_stash", 25, 1),
        ]

        attrs = CharacterAttributes()
        pos = 0
        while pos + 9 <= len(stat_data) * 8:
            attr_id = self._read_bits(stat_data, pos, 9)
            pos += 9
            if attr_id == 0x1FF:
                break
            if attr_id >= len(ATTR_LIST):
                break
            field_name, num_bits, coeff = ATTR_LIST[attr_id]
            if pos + num_bits > len(stat_data) * 8:
                break
            raw_val = self._read_bits(stat_data, pos, num_bits)
            pos += num_bits
            val = raw_val // coeff
            setattr(attrs, field_name, val)

        return attrs

    @staticmethod
    def _read_bits(data: bytes, bit_offset: int, num_bits: int) -> int:
        result = 0
        for i in range(num_bits):
            byte_idx = (bit_offset + i) // 8
            bit_idx = (bit_offset + i) % 8
            if byte_idx < len(data):
                bit = (data[byte_idx] >> bit_idx) & 1
                result |= bit << i
        return result

    def _parse_skills(self, data: bytes, skill_block_start: int | None, char_type: str) -> list[Skill]:
        if skill_block_start is None or skill_block_start + 2 + self.SKILL_BLOCK_LENGTH > len(data):
            return []

        skills_bytes = data[skill_block_start + 2 : skill_block_start + 32]
        char_key = char_type
        offset_map = self.game_data.skill_offsets(char_key)

        skills: list[Skill] = []
        for offset, name in offset_map:
            if offset < len(skills_bytes):
                level = skills_bytes[offset]
                if level > 0:
                    skills.append(Skill(name=name, level=level))
        return skills

    def _parse_quest_data(self, data: bytes) -> list[QuestData]:
        if len(data) < self.QUEST_START + 4:
            return []
        if data[self.QUEST_START:self.QUEST_START + 4] != b"Woo!":
            return []

        QUEST_OFFSETS: dict[str, int] = {
            "den_of_evil": 0,
            "radament": 14,
            "golden_bird": 54,
        }

        quests = []
        for diff_idx, diff_name in enumerate(self.DIFFICULTIES):
            larzuk_offset = self.QUEST_START + 10 + 70 + diff_idx * 96
            anya_offset = self.QUEST_START + 10 + 74 + diff_idx * 96

            larzuk = 0
            if larzuk_offset + 2 <= len(data):
                larzuk = self._read_u16(data, larzuk_offset)

            anya = 0
            if anya_offset + 2 <= len(data):
                anya = self._read_u16(data, anya_offset)

            quest_data = {
                "difficulty": diff_name,
                "siege_completed": bool(larzuk != 0),
                "socket_quest_available": bool(larzuk & (1 << 1) and larzuk & (1 << 5)),
                "resistance_scroll": bool(anya & (1 << 7)),
            }

            base = self.QUEST_START + 10 + diff_idx * 96
            for key, offset in QUEST_OFFSETS.items():
                if base + offset + 2 <= len(data):
                    val = self._read_u16(data, base + offset)
                    quest_data[key] = val != 0
                else:
                    quest_data[key] = False

            quests.append(QuestData(**quest_data))
        return quests

    def _parse_waypoints(self, data: bytes) -> list[WaypointStatus]:
        if len(data) < self.WAYPOINT_BLOCK_START + (3 * self.WAYPOINT_BLOCK_SIZE):
            return []

        WP_NAMES = [
            "Rogue Encampment", "Cold Plains", "Stony Field", "Dark Wood",
            "Black Marsh", "Outer Cloister", "Jail", "Inner Cloister", "Catacombs",
            "Lut Gholein", "Sewers", "Dry Hills", "Halls of the Dead",
            "Far Oasis", "Lost City", "Palace Cellar", "Arcane Sanctuary",
            "Canyon of the Magi",
            "Kurast Docks", "Spider Forest", "Great Marsh", "Flayer Jungle",
            "Lower Kurast", "Kurast Bazaar", "Upper Kurast", "Travincal",
            "Durance of Hate",
            "Pandemonium Fortress", "City of the Damned", "River of Flames",
            "Harrogath", "Frigid Highlands", "Arreat Plateau",
            "Crystalline Passage", "Halls of Pain", "Glacial Trail",
            "Frozen Tundra", "The Ancients' Way", "Worldstone Keep",
        ]

        results = []
        for diff_idx, diff_name in enumerate(self.DIFFICULTIES):
            base = self.WAYPOINT_BLOCK_START + diff_idx * self.WAYPOINT_BLOCK_SIZE
            wp_bytes = data[base:base + self.WAYPOINT_BLOCK_SIZE]
            active = []
            for i, name in enumerate(WP_NAMES):
                byte_idx = (self.WAYPOINT_BIT_OFFSET + i) // 8
                bit_idx = (self.WAYPOINT_BIT_OFFSET + i) % 8
                if byte_idx < len(wp_bytes) and (wp_bytes[byte_idx] >> bit_idx) & 1:
                    active.append(name)
            results.append(WaypointStatus(difficulty=diff_name, waypoints=active))
        return results

    @staticmethod
    def _resolve_set_bonuses(
        char_items: list[ParsedItem],
        merc_items: list[ParsedItem],
    ) -> None:
        char_counts: dict[str, int] = {}
        for item in char_items:
            if item.location == 1 and item.set_group:
                char_counts[item.set_group] = char_counts.get(item.set_group, 0) + 1

        merc_counts: dict[str, int] = {}
        for item in merc_items:
            if item.location == 1 and item.set_group:
                merc_counts[item.set_group] = merc_counts.get(item.set_group, 0) + 1

        for item in char_items:
            if not item.set_group:
                continue
            count = char_counts.get(item.set_group, 0)
            for prop in item.properties:
                if prop.quality_flag >= 2 and prop.display_text:
                    if count >= prop.quality_flag:
                        prop.display_text = f"{prop.display_text} ({prop.quality_flag} items)"
                    else:
                        prop.display_text = None

        for item in merc_items:
            if not item.set_group:
                continue
            count = merc_counts.get(item.set_group, 0)
            for prop in item.properties:
                if prop.quality_flag >= 2 and prop.display_text:
                    if count >= prop.quality_flag:
                        prop.display_text = f"{prop.display_text} ({prop.quality_flag} items)"
                    else:
                        prop.display_text = None

    @staticmethod
    def _read_u16(data: bytes, offset: int) -> int:
        return int.from_bytes(data[offset:offset + 2], "little", signed=False)

    @staticmethod
    def _read_u32(data: bytes, offset: int) -> int:
        return int.from_bytes(data[offset:offset + 4], "little", signed=False)
