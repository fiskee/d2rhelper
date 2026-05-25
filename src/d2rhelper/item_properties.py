from __future__ import annotations

from d2rhelper.bit_reader import BitReader
from d2rhelper.game_data import GameData
from d2rhelper.models import ParsedItemProperty

PROPERTY_PHYS_MAX_DMG = 17
PROPERTY_FIRE_MIN_DMG = 48
PROPERTY_LIGHT_MIN_DMG = 50
PROPERTY_MAGIC_MIN_DMG = 52
PROPERTY_COLD_MIN_DMG = 54
PROPERTY_POISON_MIN_DMG = 57
PROPERTY_SKILL_ATTACK = 195
PROPERTY_SKILL_KILL = 196
PROPERTY_SKILL_DEATH = 197
PROPERTY_SKILL_HIT = 198
PROPERTY_SKILL_LEVEL_UP = 199
PROPERTY_SKILL_GET_HIT = 201
PROPERTY_CHARGED_SKILL = 204
PROPERTY_END = 511
MAX_PROPERTY_ID = 368
MAX_PROPERTY_ITERATIONS = 64
POISON_FRAMES_PER_SECOND = 25

CLASS_NAMES: list[str] = []
CHANCE_SKILL_LEVEL_STATS = {
    "item_skillonattack": "on attack",
    "item_skillonhit": "on striking",
    "item_skillongethit": "when struck",
    "item_skillonkill": "when you kill an enemy",
    "item_skillondeath": "when you die",
    "item_skillonlevelup": "when you level up",
}
PROPERTY_TEXT_OVERRIDES = {
    "item_maxdamage_percent": "+#% Enhanced Maximum Damage",
    "item_mindamage_percent": "+#% Enhanced Minimum Damage",
    "mindamage": "+# to Minimum Damage",
    "maxdamage": "+# to Maximum Damage",
    "secondary_mindamage": "+# to Minimum Damage",
    "secondary_maxdamage": "+# to Maximum Damage",
}


class ItemPropertyParser:
    def __init__(self, game_data: GameData) -> None:
        self.game_data = game_data

    def read_properties(self, br: BitReader, qflag: int) -> list[ParsedItemProperty]:
        properties: list[ParsedItemProperty] = []
        iterations = 0
        root_prop = br.read_int(9)
        while root_prop != PROPERTY_END and root_prop < MAX_PROPERTY_ID:
            iterations += 1
            if iterations > MAX_PROPERTY_ITERATIONS or br.position_in_bits >= br.length_in_bits:
                break
            prop = self.parse_item_property(br, root_prop, qflag)
            if prop is not None:
                properties.append(prop)
            if root_prop in {
                PROPERTY_PHYS_MAX_DMG,
                PROPERTY_FIRE_MIN_DMG,
                PROPERTY_LIGHT_MIN_DMG,
                PROPERTY_MAGIC_MIN_DMG,
            }:
                p2 = self.parse_item_property(br, root_prop + 1, qflag)
                if p2 is not None:
                    properties.append(p2)
            elif root_prop in {PROPERTY_COLD_MIN_DMG, PROPERTY_POISON_MIN_DMG}:
                p2 = self.parse_item_property(br, root_prop + 1, qflag)
                if p2 is not None:
                    properties.append(p2)
                p3 = self.parse_item_property(br, root_prop + 2, qflag)
                if p3 is not None:
                    properties.append(p3)
                if root_prop == PROPERTY_POISON_MIN_DMG and p2 is not None and p3 is not None:
                    dam1 = properties[-3].values[-1]
                    dam2 = p2.values[-1]
                    secs = p3.values[-1] // POISON_FRAMES_PER_SECOND
                    properties[-3].display_text = ""
                    p2.display_text = ""
                    p3.display_text = f"Adds {dam1}-{dam2} Poison Damage Over {secs} Seconds"

            root_prop = br.read_int(9)
        return properties

    def parse_item_property(self, br: BitReader, root_prop: int, qflag: int) -> ParsedItemProperty | None:
        isc = self.game_data.item_stat_cost(root_prop)
        if isc is None:
            return None
        length = int(isc["save_bits"])
        save_add = int(isc["save_add"])
        save_param_bits = int(isc["save_param_bits"])
        order = int(isc["desc_priority"])
        stat_name = str(isc["stat"])

        if root_prop in {
            PROPERTY_SKILL_GET_HIT,
            PROPERTY_SKILL_DEATH,
            PROPERTY_SKILL_LEVEL_UP,
            PROPERTY_SKILL_ATTACK,
            PROPERTY_SKILL_HIT,
            PROPERTY_SKILL_KILL,
        }:
            values = [
                br.read_int(6) - save_add,
                br.read_int(10) - save_add,
                br.read_int(length) - save_add,
            ]
        elif root_prop == PROPERTY_CHARGED_SKILL:
            values = [
                br.read_int(6) - save_add,
                br.read_int(10) - save_add,
                br.read_int(8) - save_add,
                br.read_int(8) - save_add,
            ]
        elif save_param_bits >= 0:
            values = [br.read_int(save_param_bits) - save_add, br.read_int(length) - save_add]
        else:
            values = [br.read_int(length) - save_add]

        return ParsedItemProperty(
            index=root_prop,
            name=stat_name,
            values=values,
            display_name=self.property_display_name(stat_name),
            display_text=self.property_display_text(stat_name, values),
            quality_flag=qflag,
            order=order,
        )

    def property_display_name(self, stat_name: str) -> str:
        tooltip = self.game_data.property_tooltip(stat_name)
        if tooltip is None:
            return stat_name.replace("_", " ")
        return tooltip.replace("#", "").replace("+", "").strip()

    def property_display_text(self, stat_name: str, values: list[int]) -> str:
        skill_text = self.skill_property_display_text(stat_name, values)
        if skill_text is not None:
            return skill_text

        tooltip = self.game_data.property_tooltip(stat_name)
        if tooltip is None:
            tooltip = PROPERTY_TEXT_OVERRIDES.get(stat_name)
        if tooltip is None:
            return f"{stat_name.replace('_', ' ')}: {values}"
        if not values:
            return tooltip
        return tooltip.replace("#", str(values[-1]))

    def skill_property_display_text(self, stat_name: str, values: list[int]) -> str | None:
        if stat_name == "item_addclassskills" and len(values) >= 2:
            class_id, level = values[0], values[1]
            class_name = self.game_data.class_name_by_id(class_id) or f"Class {class_id}"
            return f"+{level} to {class_name} Skill Levels"
        if stat_name == "poisonlength" and values:
            return f"{values[-1] // POISON_FRAMES_PER_SECOND} Seconds"
        if stat_name in {"item_singleskill", "item_nonclassskill"} and len(values) >= 2:
            skill_id, level = values[0], values[1]
            skill_name = self.game_data.skill_name(skill_id) or f"Skill {skill_id}"
            class_name = self.game_data.skill_class_name(skill_id)
            suffix = "" if stat_name == "item_nonclassskill" else f" ({class_name or 'Class'} only)"
            return f"+{level} to {skill_name}{suffix}"
        if stat_name == "item_aura" and len(values) >= 2:
            skill_id, level = values[0], values[1]
            return f"Level {level} {self.game_data.skill_name(skill_id) or f'Skill {skill_id}'} Aura When Equipped"
        if stat_name in CHANCE_SKILL_LEVEL_STATS and len(values) >= 3:
            chance, skill_id, level = values[0], values[1], values[2]
            skill_name = self.game_data.skill_name(skill_id) or f"Skill {skill_id}"
            return f"{chance}% Chance to cast level {level} {skill_name} {CHANCE_SKILL_LEVEL_STATS[stat_name]}"
        if stat_name == "item_charged_skill" and len(values) >= 4:
            level, skill_id, charges, max_charges = values[0], values[1], values[2], values[3]
            skill_name = self.game_data.skill_name(skill_id) or f"Skill {skill_id}"
            return f"Level {level} {skill_name} ({charges}/{max_charges} Charges)"
        return None

    @staticmethod
    def combine_properties(properties: list[ParsedItemProperty]) -> None:
        names = [p.name for p in properties]
        n = len(properties)
        combined_groups = [
            (("fireresist", "lightresist", "coldresist", "poisonresist"), "All Resistances +{}%", True),
            (("maxfireresist", "maxlightresist", "maxcoldresist", "maxpoisonresist"), "All Maximum Resistances +{}%", True),
            (("item_mindamage_percent", "item_maxdamage_percent"), "+{}% Enhanced Damage", True),
            (("item_maxdamage_percent", "item_mindamage_percent"), "+{}% Enhanced Damage", True),
            (("mindamage", "maxdamage"), "Adds {}-{} Damage", False),
            (("secondary_mindamage", "secondary_maxdamage"), "Adds {}-{} Damage", False),
        ]
        for group, template, require_equal in combined_groups:
            for i in range(n - len(group) + 1):
                if names[i : i + len(group)] != list(group):
                    continue
                vals = [properties[i + j].values[-1] for j in range(len(group))]
                if require_equal and len(set(vals)) != 1:
                    continue
                if len(group) > 2 and len(set(vals)) != 1:
                    continue
                for j in range(len(group)):
                    properties[i + j].display_text = ""
                if len(group) == 2:
                    properties[i + len(group) - 1].display_text = template.format(vals[0], vals[1])
                else:
                    properties[i + len(group) - 1].display_text = template.format(vals[0])
