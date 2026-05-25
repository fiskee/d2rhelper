from __future__ import annotations

from collections.abc import Callable

from d2rhelper.bit_reader import BitReader
from d2rhelper.models import ParsedItem


class ItemRecovery:
    def __init__(
        self,
        *,
        min_item_bits: int,
        max_item_bits: int,
        probe_tail_bits: int,
        valid_locations: set[int],
        valid_containers: set[int],
        parse_item_basic: Callable[[int, BitReader], ParsedItem],
        is_known_item_code: Callable[[str], bool],
    ) -> None:
        self.min_item_bits = min_item_bits
        self.max_item_bits = max_item_bits
        self.probe_tail_bits = probe_tail_bits
        self.valid_locations = valid_locations
        self.valid_containers = valid_containers
        self.parse_item_basic = parse_item_basic
        self.is_known_item_code = is_known_item_code

    def recover_item_from_position(self, br: BitReader, index: int, failed_pos: int) -> ParsedItem | None:
        probe = BitReader(br._data)  # noqa: SLF001
        probe.set_position_in_bits(failed_pos)
        try:
            recovered = self.parse_item_basic(index, probe)
        except Exception:
            return None
        consumed = probe.position_in_bits - failed_pos
        if consumed <= 0 or consumed > self.max_item_bits:
            return None
        if recovered.location not in self.valid_locations:
            return None
        if recovered.container not in self.valid_containers:
            return None
        if recovered.ear or recovered.code is None:
            return None
        if not self.is_known_item_code(recovered.code):
            return None
        br.set_position_in_bits(probe.position_in_bits)
        return recovered

    def position_has_known_basic_item(self, br: BitReader, position: int) -> bool:
        probe = BitReader(br._data)  # noqa: SLF001
        probe.set_position_in_bits(position)
        try:
            item = self.parse_item_basic(-1, probe)
        except Exception:
            return False
        return (
            item.code is not None
            and self.is_known_item_code(item.code)
            and item.location in self.valid_locations
            and item.container in self.valid_containers
        )

    def nudge_to_plausible_next_start(self, br: BitReader) -> None:
        current = br.position_in_bits
        if self.position_has_known_basic_item(br, current):
            return
        for offset in (8, 16):
            candidate = current + offset
            if candidate >= br.length_in_bits - self.probe_tail_bits:
                return
            if self.position_has_known_basic_item(br, candidate):
                br.set_position_in_bits(candidate)
                return

    def recover_next_item_start(self, br: BitReader, failed_pos: int) -> int | None:
        start = ((failed_pos + 7) // 8) * 8
        end = br.length_in_bits - self.probe_tail_bits
        probe = BitReader(br._data)  # noqa: SLF001
        best_candidate: int | None = None
        best_score = -1
        for candidate in range(start, end, 8):
            probe.set_position_in_bits(candidate)
            try:
                item = self.parse_item_basic(-1, probe)
            except Exception:
                continue
            if probe.position_in_bits <= candidate:
                continue
            score = 0
            if item.code is not None and self.is_known_item_code(item.code):
                score += 3
            if item.location in self.valid_locations:
                score += 2
            if item.container in self.valid_containers:
                score += 2
            consumed = probe.position_in_bits - candidate
            if self.min_item_bits <= consumed <= self.max_item_bits:
                score += 2
            if item.ear:
                score += 1
            if score > best_score:
                best_score = score
                best_candidate = candidate
                if score >= 8:
                    return candidate
        return best_candidate
