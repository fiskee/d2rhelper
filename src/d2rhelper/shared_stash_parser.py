from __future__ import annotations

from pathlib import Path

from d2rhelper.item_parser import ItemParser
from d2rhelper.models import SharedStashTab
from d2rhelper.parser import ParseError


class SharedStashParser:
    STASH_INIT_BYTES = bytes([85, 170, 85, 170])

    def __init__(self) -> None:
        self.item_parser = ItemParser()

    def parse_file(self, file_path: str | Path) -> list[SharedStashTab]:
        data = Path(file_path).read_bytes()
        return self.parse_bytes(data)

    def parse_bytes(self, data: bytes) -> list[SharedStashTab]:
        tab_indices = self._get_start_indices(data)
        tabs: list[SharedStashTab] = []

        if len(tab_indices) == 3:
            parse_indices = tab_indices
        elif len(tab_indices) == 7:
            parse_indices = tab_indices[:6]
        else:
            raise ParseError(
                f"Shared stash marker count must be 3 or 7, but was {len(tab_indices)}"
            )

        for i, index in enumerate(parse_indices):
            is_last = (i == len(parse_indices) - 1)
            tab = self._parse_tab(i, index, data, is_materials_stash=is_last)
            tabs.append(tab)
        return tabs

    def _parse_tab(self, tab_number: int, index: int, data: bytes, *, is_materials_stash: bool = False) -> SharedStashTab:
        version = int.from_bytes(data[index + 8:index + 12], "little", signed=False)
        if version != 105:
            raise ParseError(f"Unsupported shared stash version {version}")
        gold = int.from_bytes(data[index + 12:index + 16], "little", signed=False)
        length_in_bytes = int.from_bytes(data[index + 16:index + 20], "little", signed=False)

        item_start = index + 64
        item_end = index + length_in_bytes
        items = self.item_parser.parse_items(data, item_start, min(item_end, len(data)), is_materials_stash=is_materials_stash)

        item_count = 0
        if item_start + 4 <= len(data) and data[item_start:item_start + 2] == b"JM":
            item_count = int.from_bytes(data[item_start + 2:item_start + 4], "little", signed=False)

        return SharedStashTab(
            index=tab_number,
            version=version,
            gold=gold,
            length_in_bytes=length_in_bytes,
            item_count=item_count,
            items=items,
        )

    def _get_start_indices(self, data: bytes) -> list[int]:
        indices: list[int] = []
        i = 0
        while i < len(data) - 3:
            if data[i:i + 4] == self.STASH_INIT_BYTES:
                indices.append(i)
                i += 4
            else:
                i += 1
        return indices
