from __future__ import annotations

from d2rhelper.bit_reader import BitReader
from d2rhelper.game_data import GameData
from d2rhelper.item_properties import ItemPropertyParser
from d2rhelper.item_recovery import ItemRecovery
from d2rhelper.item_rules import ItemRules
from d2rhelper.models import ItemQuality, ParsedItem, ParsedItemProperty

MIN_ITEM_BITS = 48
MAX_ITEM_BITS = 4096
PROBE_TAIL_BITS = 64
MAX_SOCKETED_ITEMS_TO_PARSE = 12
VALID_LOCATIONS = {0, 1, 2, 4, 6}
VALID_CONTAINERS = {0, 1, 4, 5}


class ItemParseError(ValueError):
    pass


class ItemParser:
    def __init__(self, game_data: GameData | None = None) -> None:
        self.game_data = game_data or GameData.get_instance()
        self.rules = ItemRules(self.game_data)
        self.properties = ItemPropertyParser(self.game_data)
        self.recovery = ItemRecovery(
            min_item_bits=MIN_ITEM_BITS,
            max_item_bits=MAX_ITEM_BITS,
            probe_tail_bits=PROBE_TAIL_BITS,
            valid_locations=VALID_LOCATIONS,
            valid_containers=VALID_CONTAINERS,
            parse_item_basic=self._parse_item_basic,
            is_known_item_code=self._is_known_item_code,
        )
        self.warnings: list[str] = []

    def parse_items(self, data: bytes, start: int, end: int, *, is_materials_stash: bool = False) -> list[ParsedItem]:
        self.warnings = []
        if start + 4 > len(data):
            return []
        if data[start : start + 2] != b"JM":
            raise ItemParseError("Problem parsing item header (should be JM)")

        count = int.from_bytes(data[start + 2 : start + 4], "little", signed=False)
        item_bytes = data[start + 4 : end]
        br = BitReader(item_bytes)
        results: list[ParsedItem] = []

        for idx in range(count):
            before = br.position_in_bits
            try:
                parsed = self._parse_item(idx, br, is_materials_stash=is_materials_stash)
                consumed = br.position_in_bits - before
                self._validate_parsed_item(parsed, consumed, recovered=False)
                self.recovery.nudge_to_plausible_next_start(br)
                results.append(parsed)
            except Exception:
                failed_pos = before
                placeholder = self._placeholder_item(idx, failed_pos)
                fallback_item = self.recovery.recover_item_from_position(br, idx, failed_pos)
                if fallback_item is not None:
                    results.append(fallback_item)
                    self.warnings.append(f"item[{idx}] recovered from failed position (bit {failed_pos})")
                    continue

                fallback = self.recovery.recover_next_item_start(br, failed_pos)
                if fallback is None:
                    placeholder.parse_ok = False
                    results.append(placeholder)
                    self.warnings.append(f"item[{idx}] recovery failed at bit {failed_pos}, advancing one byte")
                    br.set_position_in_bits(min(failed_pos + 8, br.length_in_bits - 8))
                    continue
                br.set_position_in_bits(fallback)
                try:
                    before = br.position_in_bits
                    recovered = self._parse_item(idx, br, is_materials_stash=is_materials_stash)
                    consumed = br.position_in_bits - before
                    self._validate_parsed_item(recovered, consumed, recovered=True)
                    self.recovery.nudge_to_plausible_next_start(br)
                    recovered.recovered = True
                    results.append(recovered)
                    skipped = fallback - failed_pos
                    self.warnings.append(f"item[{idx}] recovered: shifted {skipped} bits (from bit {failed_pos} to {fallback})")
                except Exception as recover_exc:
                    placeholder.parse_ok = False
                    results.append(placeholder)
                    self.warnings.append(f"item[{idx}] recovery parse failed at bit {fallback}: {recover_exc}")

        return results

    def _parse_item_basic(self, index: int, br: BitReader) -> ParsedItem:
        start_bit = br.position_in_bits
        flags = br.read_flipped_int(32)
        identified = self._is_bit_checked(flags, 5)
        socketed = self._is_bit_checked(flags, 12)
        ear = self._is_bit_checked(flags, 17)
        simple = self._is_bit_checked(flags, 22)
        ethereal = self._is_bit_checked(flags, 23)
        personalized = self._is_bit_checked(flags, 25)
        runeword = self._is_bit_checked(flags, 27)

        br.skip(3)
        location = br.read_short(3)
        position = br.read_short(4)
        y = br.read_short(4)
        x = br.read_short(4)
        container = br.read_short(3)

        code: str | None = None
        if ear:
            self._parse_ear(br)
        else:
            code = br.read_huffman_encoded_string()

        br.move_to_next_byte_boundary()
        end_bit = br.position_in_bits
        return ParsedItem(
            index=index,
            start_bit=start_bit,
            end_bit=end_bit,
            location=location,
            position=position,
            x=x,
            y=y,
            container=container,
            code=code,
            item_name=self._item_name(code),
            display_name=self._item_name(code),
            raw_flags=flags,
            identified=identified,
            socketed=socketed,
            ear=ear,
            simple=simple,
            ethereal=ethereal,
            personalized=personalized,
            runeword=runeword,
        )

    @staticmethod
    def _placeholder_item(index: int, bit_pos: int) -> ParsedItem:
        return ParsedItem(
            index=index,
            start_bit=bit_pos,
            end_bit=bit_pos,
            location=0,
            position=0,
            x=0,
            y=0,
            container=0,
            code="PARSE_ERROR",
            raw_flags=0,
        )

    @staticmethod
    def _is_plausible_code(code: str) -> bool:
        if not (1 <= len(code) <= 8):
            return False
        return all(c.isalnum() for c in code)

    def _is_known_item_code(self, code: str) -> bool:
        if not self._is_plausible_code(code):
            return False
        return self._stats_row(code, self._determine_item_type(code)) is not None

    @staticmethod
    def _is_valid_basic_item_fields(item: ParsedItem) -> bool:
        return item.location in VALID_LOCATIONS and item.container in VALID_CONTAINERS

    def _validate_parsed_item(self, item: ParsedItem, consumed_bits: int, *, recovered: bool) -> None:
        tag = "recovered " if recovered else ""
        if item.code is None and not item.ear:
            raise ValueError(f"{tag}item without code")
        if item.ear:
            raise ValueError(f"{tag}ear item encountered in D2R offline item stream")
        if item.code is None or not self._is_known_item_code(item.code):
            raise ValueError(f"implausible {tag}item code: {item.code}")
        if item.location not in VALID_LOCATIONS:
            raise ValueError(f"implausible {tag}item location: {item.location}")
        if item.container not in VALID_CONTAINERS:
            raise ValueError(f"implausible {tag}item container: {item.container}")
        if consumed_bits <= 0 or consumed_bits > MAX_ITEM_BITS:
            raise ValueError(f"implausible {tag}item length bits: {consumed_bits}")

    def _parse_item(self, index: int, br: BitReader, *, is_materials_stash: bool = False) -> ParsedItem:
        start_bit = br.position_in_bits
        flags = br.read_flipped_int(32)
        identified = self._is_bit_checked(flags, 5)
        socketed = self._is_bit_checked(flags, 12)
        ear = self._is_bit_checked(flags, 17)
        simple = self._is_bit_checked(flags, 22)
        ethereal = self._is_bit_checked(flags, 23)
        personalized = self._is_bit_checked(flags, 25)
        runeword = self._is_bit_checked(flags, 27)

        br.skip(3)
        location = br.read_short(3)
        position = br.read_short(4)
        y = br.read_short(4)
        x = br.read_short(4)
        container = br.read_short(3)

        code: str | None = None
        quality = ItemQuality.UNKNOWN
        level = None
        cnt_filled_sockets = None
        cnt_sockets: int | None = None
        stacks: int | None = None
        max_stacks: int | None = None
        unique_name: str | None = None
        set_name: str | None = None
        req_str: int | None = None
        req_dex: int | None = None
        req_level: int | None = None
        properties: list[ParsedItemProperty] = []
        socketed_items: list[ParsedItem] = []
        runeword_name = None

        if ear:
            self._parse_ear(br)
        else:
            code = br.read_huffman_encoded_string()
            if not simple:
                cnt_filled_sockets = br.read_short(3)
                br.read_int(32)  # fingerprint
                level = br.read_short(7)
                quality = self._quality_by_value(br.read_short(4))
                picture_flag = br.read_short(1)
                if picture_flag == 1:
                    br.read_short(3)
                class_specific_flag = br.read_short(1)
                if class_specific_flag == 1:
                    br.read_int(11)

                quality_id = self._consume_quality_specific(quality, br, code)
                if quality == ItemQuality.UNIQUE and quality_id is not None:
                    unique_name = self.game_data.unique_name(quality_id)
                elif quality == ItemQuality.SET and quality_id is not None:
                    set_name = self.game_data.set_name(quality_id)

                if runeword:
                    br.skip(16)
                if personalized:
                    self._consume_personalization(br)

                self._consume_quest_or_guid(br, code)

                properties, socketed_items, cnt_sockets = self._parse_extended_part2(
                    br,
                    code,
                    quality,
                    socketed,
                    runeword,
                    cnt_filled_sockets or 0,
                )
                self._combine_properties(properties)
                if runeword:
                    runeword_name = self._resolve_runeword_name(socketed_items)

            req_str, req_dex, req_level = self._item_requirements(code, ethereal, properties)

            if simple and code is not None:
                if is_materials_stash and self._is_advanced_stash_stackable(code):
                    stacks = y
                    max_stacks = self._max_stacks(code, self._determine_item_type(code))

                peeked_next_byte = br.peek_next_byte()
                if (
                    br.bits_to_next_boundary() == 0
                    and peeked_next_byte != 16
                    and (br.peek_next_bytes(16) != 0 or br.peek_next_bytes(24) == 0)
                ):
                    br.skip(1)

                if (
                    peeked_next_byte == 0
                    and br.get_current_byte() != 0
                    and br.peek_next_bytes(16) != 0
                ):
                    br.skip(8)
            elif code == "xyz":
                br.skip(16)

        br.move_to_next_byte_boundary()
        end_bit = br.position_in_bits
        return ParsedItem(
            index=index,
            start_bit=start_bit,
            end_bit=end_bit,
            location=location,
            position=position,
            x=x,
            y=y,
            container=container,
            code=code,
            item_name=self._item_name(code),
            display_name=runeword_name or unique_name or set_name or self._item_name(code),
            runeword_name=runeword_name,
            unique_name=unique_name,
            set_name=set_name,
            weapon_damage=self._weapon_damage_text(code, properties),
            raw_flags=flags,
            identified=identified,
            socketed=socketed,
            ear=ear,
            simple=simple,
            ethereal=ethereal,
            personalized=personalized,
            runeword=runeword,
            req_level=req_level,
            req_str=req_str,
            req_dex=req_dex,
            quality=quality,
            level=level,
            cnt_filled_sockets=cnt_filled_sockets,
            cnt_sockets=cnt_sockets,
            stacks=stacks,
            max_stacks=max_stacks,
            socketed_items=socketed_items,
            properties=properties,
        )

    @staticmethod
    def _is_bit_checked(value: int, bit: int) -> bool:
        return ((value >> (32 - bit)) & 1) == 1

    @staticmethod
    def _parse_ear(br: BitReader) -> None:
        br.read_short(3)
        br.read_short(7)
        for _ in range(16):
            c = br.read_char(7)
            if c == "\x00":
                break
        br.move_to_next_byte_boundary()

    @staticmethod
    def _quality_by_value(value: int) -> ItemQuality:
        try:
            return ItemQuality(value)
        except ValueError:
            return ItemQuality.UNKNOWN

    @staticmethod
    def _consume_quality_specific(quality: ItemQuality, br: BitReader, code: str) -> int | None:
        if quality == ItemQuality.INFERIOR:
            br.read_short(3)
        elif quality == ItemQuality.NORMAL:
            if code in {"tbk", "ibk"}:
                br.read_short(5)
        elif quality == ItemQuality.SUPERIOR:
            br.read_short(3)
        elif quality == ItemQuality.MAGIC:
            br.read_short(11)
            br.read_short(11)
        elif quality == ItemQuality.SET:
            return br.read_short(12)
        elif quality in {ItemQuality.RARE, ItemQuality.CRAFT}:
            br.read_short(8)
            br.read_short(8)
            for _ in range(3):
                if br.read_short(1) == 1:
                    br.read_short(11)
                if br.read_short(1) == 1:
                    br.read_short(11)
        elif quality == ItemQuality.UNIQUE:
            return br.read_short(12)
        return None

    @staticmethod
    def _consume_personalization(br: BitReader) -> None:
        for _ in range(16):
            if br.read_char(8) == "\x00":
                break

    def _consume_quest_or_guid(self, br: BitReader, code: str) -> None:
        if self._has_quest_difficulty(code):
            if code in {"vip", "ice"}:
                br.revert(2)
            br.read_byte(3)
            return

        if br.read_short(1) != 1:
            return

        item_type = self._determine_item_type(code)
        no_misc_item = item_type != "misc"
        if self._needs_guid(code, no_misc_item):
            br.read_int(32)
            br.read_int(32)
            br.read_int(32)
            br.read_int(32)
        elif code != "bks":
            br.skip(3)

    def _parse_extended_part2(
        self,
        br: BitReader,
        code: str,
        quality: ItemQuality,
        socketed: bool,
        runeword: bool,
        cnt_filled_sockets: int,
    ) -> tuple[list[ParsedItemProperty], list[ParsedItem], int | None]:
        item_type = self._determine_item_type(code)
        max_stacks = self._max_stacks(code, item_type)

        if item_type == "armor":
            br.read_short(11)
            max_durability = br.read_short(8)
            if max_durability != 0:
                br.read_short(9)
        elif item_type == "weapon":
            max_durability = br.read_short(8)
            if max_durability != 0:
                br.read_short(9)
            if self._is_stackable(code, item_type):
                br.skip(1)
                br.read_short(9)
        else:
            if self._is_stackable(code, item_type):
                br.skip(1)
                br.read_short(9)

        if max_stacks == 0 and code != "xyz":
            br.skip(1)

        if socketed:
            cnt_sockets = br.read_short(4)
        else:
            cnt_sockets = None

        set_bonus_flags = [0, 0, 0, 0, 0]
        if quality == ItemQuality.SET:
            for i in range(5):
                set_bonus_flags[i] = br.read_int(1)

        properties = self._read_properties(br, 1 if code == "jew" else 0)

        if quality == ItemQuality.SET:
            for i in range(5):
                if set_bonus_flags[i] == 1:
                    properties.extend(self._read_properties(br, i + 2))

        if runeword:
            properties.extend(self._read_properties(br, 0))

        socketed_items: list[ParsedItem] = []
        if cnt_filled_sockets > 0:
            br.move_to_next_byte_boundary()
            saved_pos = br.position_in_bits
            if not self.recovery.position_has_known_basic_item(br, br.position_in_bits):
                if br.read_short(1) == 1:
                    br.read_byte(8)
                br.move_to_next_byte_boundary()
                if not self.recovery.position_has_known_basic_item(br, br.position_in_bits):
                    br.set_position_in_bits(saved_pos)

            for _ in range(min(cnt_filled_sockets, MAX_SOCKETED_ITEMS_TO_PARSE)):
                socketed_items.append(self._parse_item_basic(-1, br))
                self.recovery.nudge_to_plausible_next_start(br)

        return properties, socketed_items, cnt_sockets

    def _read_properties(self, br: BitReader, qflag: int) -> list[ParsedItemProperty]:
        return self.properties.read_properties(br, qflag)

    def _parse_item_property(
        self, br: BitReader, root_prop: int, qflag: int
    ) -> ParsedItemProperty | None:
        return self.properties.parse_item_property(br, root_prop, qflag)

    def _property_display_name(self, stat_name: str) -> str:
        return self.properties.property_display_name(stat_name)

    def _property_display_text(self, stat_name: str, values: list[int]) -> str:
        return self.properties.property_display_text(stat_name, values)

    def _skill_property_display_text(self, stat_name: str, values: list[int]) -> str | None:
        return self.properties.skill_property_display_text(stat_name, values)

    @staticmethod
    def _combine_properties(properties: list[ParsedItemProperty]) -> None:
        ItemPropertyParser.combine_properties(properties)

    def _item_requirements(
        self, code: str | None, ethereal: bool, properties: list[ParsedItemProperty]
    ) -> tuple[int | None, int | None, int | None]:
        return self.rules.item_requirements(code, ethereal, properties)

    def _determine_item_type(self, code: str) -> str:
        return self.rules.determine_item_type(code)

    def _is_stackable(self, code: str, item_type: str) -> bool:
        return self.rules.is_stackable(code, item_type)

    def _max_stacks(self, code: str, item_type: str) -> int:
        return self.rules.max_stacks(code, item_type)

    def _stats_row(self, code: str, item_type: str) -> dict[str, str] | None:
        return self.rules.stats_row(code, item_type)

    def _is_advanced_stash_stackable(self, code: str) -> bool:
        return self.rules.is_advanced_stash_stackable(code)

    def _item_name(self, code: str | None) -> str | None:
        return self.rules.item_name(code)

    def _weapon_damage_text(self, code: str | None, properties: list[ParsedItemProperty]) -> str | None:
        return self.rules.weapon_damage_text(code, properties)

    def _has_quest_difficulty(self, code: str) -> bool:
        return self.rules.has_quest_difficulty(code)

    def _needs_guid(self, code: str, no_misc_item: bool) -> bool:
        return self.rules.needs_guid(code, no_misc_item)

    def _resolve_runeword_name(self, socketed_items: list[ParsedItem]) -> str | None:
        return self.rules.resolve_runeword_name(socketed_items)
