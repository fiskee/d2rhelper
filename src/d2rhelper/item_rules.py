from __future__ import annotations

from d2rhelper.game_data import GameData
from d2rhelper.models import ParsedItem, ParsedItemProperty


class ItemRules:
    def __init__(self, game_data: GameData) -> None:
        self.game_data = game_data

    def item_requirements(
        self, code: str | None, ethereal: bool, properties: list[ParsedItemProperty]
    ) -> tuple[int | None, int | None, int | None]:
        if code is None:
            return None, None, None
        row = self.stats_row(code, self.determine_item_type(code))
        if row is None:
            return None, None, None

        req_str = self._as_int(row.get("reqstr", "0"))
        req_dex = self._as_int(row.get("reqdex", "0"))
        req_lvl_raw = self._as_int(row.get("levelreq", "0"))
        base_level = self._as_int(row.get("level", "0"))
        req_level = req_lvl_raw if req_lvl_raw > 0 else base_level
        if req_level == 0:
            req_level = None

        if ethereal:
            if req_str is not None and req_str > 0:
                req_str -= 10
            if req_dex is not None and req_dex > 0:
                req_dex -= 10

        req_pct = sum(p.values[0] for p in properties if p.name == "item_req_percent" and p.values)
        if req_pct != 0:
            pct = 1.0 + req_pct / 100.0
            if req_str:
                req_str = int(req_str * pct)
            if req_dex:
                req_dex = int(req_dex * pct)
            if req_level:
                req_level = int(req_level * pct)

        if req_str == 0:
            req_str = None
        if req_dex == 0:
            req_dex = None

        return req_str, req_dex, req_level

    def determine_item_type(self, code: str) -> str:
        if self.game_data.armor_by_code(code) is not None:
            return "armor"
        if self.game_data.weapon_by_code(code) is not None:
            return "weapon"
        return "misc"

    def is_stackable(self, code: str, item_type: str) -> bool:
        row = self.stats_row(code, item_type)
        if row is None:
            return False
        return self._as_int(row.get("stackable", "0")) == 1

    def max_stacks(self, code: str, item_type: str) -> int:
        row = self.stats_row(code, item_type)
        if row is None:
            return 0
        return self._as_int(row.get("maxstack", "0"))

    def stats_row(self, code: str, item_type: str) -> dict[str, str] | None:
        if item_type == "armor":
            return self.game_data.armor_by_code(code)
        if item_type == "weapon":
            return self.game_data.weapon_by_code(code)
        return self.game_data.misc_by_code(code)

    def is_advanced_stash_stackable(self, code: str) -> bool:
        row = self.game_data.misc_by_code(code)
        if row is None:
            return False
        return row.get("AdvancedStashStackable", "0") == "1"

    def item_name(self, code: str | None) -> str | None:
        if code is None:
            return None
        row = self.stats_row(code, self.determine_item_type(code))
        if row is None:
            return None
        return row.get("name") or row.get("namestr") or code

    def weapon_damage_text(self, code: str | None, properties: list[ParsedItemProperty]) -> str | None:
        if code is None:
            return None
        row = self.game_data.weapon_by_code(code)
        if row is None:
            return None

        one_min = self._as_int(row.get("mindam", "0"))
        one_max = self._as_int(row.get("maxdam", "0"))
        two_min = self._as_int(row.get("2handmindam", "0"))
        two_max = self._as_int(row.get("2handmaxdam", "0"))

        enhanced_min = sum(p.values[0] for p in properties if p.name == "item_mindamage_percent" and p.values)
        enhanced_max = sum(p.values[0] for p in properties if p.name == "item_maxdamage_percent" and p.values)
        enhanced = min(enhanced_min, enhanced_max) if enhanced_min and enhanced_max else max(enhanced_min, enhanced_max)

        flat_min = sum(p.values[0] for p in properties if p.name in {"mindamage", "secondary_mindamage"} and p.values)
        flat_max = sum(p.values[0] for p in properties if p.name in {"maxdamage", "secondary_maxdamage"} and p.values)

        parts: list[str] = []
        if one_min or one_max:
            parts.append(f"1H {self._apply_damage(one_min, enhanced, flat_min)}-{self._apply_damage(one_max, enhanced, flat_max)}")
        if two_min or two_max:
            parts.append(f"2H {self._apply_damage(two_min, enhanced, flat_min)}-{self._apply_damage(two_max, enhanced, flat_max)}")
        return ", ".join(parts) if parts else None

    def has_quest_difficulty(self, code: str) -> bool:
        row = self.stats_row(code, self.determine_item_type(code))
        if row is None:
            return False
        return self._as_int(row.get("questdiffcheck", "0")) == 1

    def needs_guid(self, code: str, no_misc_item: bool) -> bool:
        row = self.stats_row(code, self.determine_item_type(code))
        item_type = (row or {}).get("type", "")
        return (
            item_type == "rune"
            or item_type.startswith("gem")
            or item_type.startswith("amu")
            or item_type.startswith("rin")
            or code in {"cm1", "cm2", "cm3"}
            or no_misc_item
        )

    def resolve_runeword_name(self, socketed_items: list[ParsedItem]) -> str | None:
        rune_names: list[str] = []
        for item in socketed_items:
            if item.item_name is None or not item.item_name.endswith(" Rune"):
                return None
            rune_names.append(item.item_name.removesuffix(" Rune"))
        runeword = self.game_data.runeword_by_string("".join(rune_names))
        if runeword is None:
            return None
        return runeword["name"]

    @staticmethod
    def _apply_damage(base: int, enhanced_percent: int, flat: int) -> int:
        return (base * (100 + enhanced_percent) // 100) + flat

    @staticmethod
    def _as_int(value: str) -> int:
        try:
            return int(value)
        except ValueError:
            return 0
