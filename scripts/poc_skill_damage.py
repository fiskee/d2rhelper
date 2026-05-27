from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from d2rhelper.parser import CharacterParser


DB_PATH = Path(__file__).resolve().parents[1] / "src" / "d2rhelper" / "data" / "game.db"


CLASS_ALIASES = {
    "amazon": "ama",
    "assassin": "ass",
    "barbarian": "bar",
    "druid": "dru",
    "necromancer": "nec",
    "paladin": "pal",
    "sorceress": "sor",
    "warlock": "war",
    "war": "war",
}


@dataclass
class SkillDamageEstimate:
    skill_name: str
    class_code: str
    skill_level: int
    plus_skills: int
    effective_skill_level: int
    base_damage_min: float
    base_damage_max: float
    synergy_bonus_pct: float
    enemy_resist_initial: float
    enemy_resist_after_mods: float
    final_damage_min: float
    final_damage_max: float
    assumptions: list[str]
    issues: list[dict[str, Any]]


@dataclass
class PetEstimate:
    summon_skill: str
    class_code: str
    skill_level: int
    plus_skills: int
    effective_skill_level: int
    pet_type: str
    pet_monster_id: str
    pet_count: int
    pet_base_damage_min: float
    pet_base_damage_max: float
    pet_base_hp_min: float
    pet_base_hp_max: float
    pet_damage_bonus_pct: float
    pet_hp_bonus_pct: float
    pet_scaled_damage_min: float
    pet_scaled_damage_max: float
    pet_scaled_hp_min: float
    pet_scaled_hp_max: float
    assumptions: list[str]
    issues: list[dict[str, Any]]


def _fnum(raw: Any) -> float:
    if raw in (None, ""):
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _canonical_class_code(class_name: str) -> str:
    key = class_name.strip().lower()
    if key in CLASS_ALIASES:
        return CLASS_ALIASES[key]
    return key


def _find_skill(conn: sqlite3.Connection, class_code: str, skill_name: str) -> sqlite3.Row | None:
    row = conn.execute(
        "SELECT * FROM skills WHERE charclass = ? AND LOWER(skill) = ?",
        (class_code, skill_name.strip().lower()),
    ).fetchone()
    if row:
        return row
    row = conn.execute(
        "SELECT * FROM skills WHERE charclass = ? AND LOWER(skill) LIKE ? ORDER BY skill LIMIT 1",
        (class_code, f"%{skill_name.strip().lower()}%"),
    ).fetchone()
    return row


def _d2_scaled_component(base: float, level: int, row: sqlite3.Row, prefix: str) -> float:
    if level <= 1:
        return base
    remaining = level - 1
    # POC approximation for D2 per-level fields:
    # lev1 applies to levels 2-8, lev2: 9-16, lev3: 17-22, lev4: 23-28, lev5: 29+
    # In the extracted game.db used here, levN values are already in display units.
    brackets = [
        (7, _fnum(row[f"{prefix}lev1"])),
        (8, _fnum(row[f"{prefix}lev2"])),
        (6, _fnum(row[f"{prefix}lev3"])),
        (6, _fnum(row[f"{prefix}lev4"])),
        (999, _fnum(row[f"{prefix}lev5"])),
    ]
    value = base
    for size, inc in brackets:
        if remaining <= 0:
            break
        steps = min(remaining, size)
        value += steps * inc
        remaining -= steps
    return value


_SKILL_RE = re.compile(r"skill\('([^']+)'\.blvl\)")
_PAR_RE = re.compile(r"par(\d+)")
_SKILL_METRIC_RE = re.compile(r"skill\('([^']+)'\.(blvl|ln\d\d|dm\d\d)\)")
_LN_DM_RE = re.compile(r"\b(ln|dm)(\d)(\d)\b")


def _safe_eval_arith(expr: str) -> float:
    node = ast.parse(expr, mode="eval")

    def _eval(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = _eval(n.operand)
            return v if isinstance(n.op, ast.UAdd) else -v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            l = _eval(n.left)
            r = _eval(n.right)
            if isinstance(n.op, ast.Add):
                return l + r
            if isinstance(n.op, ast.Sub):
                return l - r
            if isinstance(n.op, ast.Mult):
                return l * r
            return l / r if r != 0 else 0.0
        raise ValueError(f"Unsupported expression node: {type(n).__name__}")

    return _eval(node)


def _ln_dm_value(skill_row: sqlite3.Row, token_type: str, a: int, b: int, level: int) -> float:
    # POC approximation: ln56/dm56 -> param5 + (lvl-1)*param6
    base = _fnum(skill_row[f"param{a}"])
    per_lvl = _fnum(skill_row[f"param{b}"])
    if level <= 1:
        return base
    return base + (level - 1) * per_lvl


def _eval_formula_expr(
    expr: str,
    *,
    current_skill_row: sqlite3.Row,
    current_skill_level: int,
    conn: sqlite3.Connection,
    extra_levels: dict[str, int],
) -> tuple[float, list[str], list[dict[str, Any]]]:
    assumptions: list[str] = []
    issues: list[dict[str, Any]] = []

    if not expr.strip():
        return 0.0, assumptions, issues

    # Handle simple ternary condition pattern manually: (X>=N)?A:B
    ternary = re.match(r"^\((.+)>=([0-9]+)\)\?(.+):(.+)$", expr.strip())
    if ternary:
        lhs_expr = ternary.group(1)
        req = float(ternary.group(2))
        yes_expr = ternary.group(3)
        no_expr = ternary.group(4)
        lhs, a1, i1 = _eval_formula_expr(
            lhs_expr,
            current_skill_row=current_skill_row,
            current_skill_level=current_skill_level,
            conn=conn,
            extra_levels=extra_levels,
        )
        assumptions.extend(a1)
        issues.extend(i1)
        chosen = yes_expr if lhs >= req else no_expr
        val, a2, i2 = _eval_formula_expr(
            chosen,
            current_skill_row=current_skill_row,
            current_skill_level=current_skill_level,
            conn=conn,
            extra_levels=extra_levels,
        )
        assumptions.extend(a2)
        issues.extend(i2)
        return val, assumptions, issues

    text = expr
    text = re.sub(r"\blvl\b", str(float(current_skill_level)), text)

    for m in _SKILL_METRIC_RE.finditer(text):
        full = m.group(0)
        skill_name = m.group(1)
        metric = m.group(2)
        ref_level = int(extra_levels.get(skill_name, 0))
        ref_row = conn.execute("SELECT * FROM skills WHERE LOWER(skill)=?", (skill_name.lower(),)).fetchone()
        if metric == "blvl":
            rep = float(ref_level)
        elif metric.startswith("ln") or metric.startswith("dm"):
            if ref_row is None:
                rep = 0.0
                issues.append({
                    "code": "DB_INCOMPLETE",
                    "message": "Referenced skill row not found while evaluating formula.",
                    "context": {"skill": skill_name, "metric": metric},
                })
            else:
                a = int(metric[2])
                b = int(metric[3])
                rep = _ln_dm_value(ref_row, metric[:2], a, b, max(ref_level, 1))
                assumptions.append(f"Interpreted {metric} as param{a} + (lvl-1)*param{b} for '{skill_name}'.")
        else:
            rep = 0.0
        text = text.replace(full, str(rep))

    # Local ln/dm tokens use current skill row + current skill level.
    for m in _LN_DM_RE.finditer(text):
        full = m.group(0)
        t = m.group(1)
        a = int(m.group(2))
        b = int(m.group(3))
        rep = _ln_dm_value(current_skill_row, t, a, b, max(current_skill_level, 1))
        assumptions.append(f"Interpreted {full} as param{a} + (lvl-1)*param{b} for current skill.")
        text = text.replace(full, str(rep))

    # parN references on current skill
    for i in range(1, 21):
        text = re.sub(rf"\bpar{i}\b", str(_fnum(current_skill_row[f"param{i}"])), text)

    text = text.replace('"', "")
    open_count = text.count("(")
    close_count = text.count(")")
    if open_count > close_count:
        text = text + (")" * (open_count - close_count))
        assumptions.append("Auto-balanced unmatched parentheses in formula expression.")

    try:
        return _safe_eval_arith(text), assumptions, issues
    except Exception as exc:  # noqa: BLE001
        issues.append({
            "code": "FORMULA_UNPARSED",
            "message": f"Could not evaluate formula expression: {expr}",
            "context": {"normalized": text, "error": str(exc)},
        })
        return 0.0, assumptions, issues


def _synergy_bonus_percent(row: sqlite3.Row, synergy_levels: dict[str, int]) -> tuple[float, list[str]]:
    expr = str(row["edmgsympercalc"] or "").strip()
    if not expr:
        return 0.0, []

    assumptions: list[str] = []
    par_match = _PAR_RE.search(expr)
    if not par_match:
        assumptions.append("No parN multiplier found in synergy expression; treating synergy as 0%.")
        return 0.0, assumptions
    par_idx = int(par_match.group(1))
    par_val = _fnum(row[f"param{par_idx}"])

    skills = _SKILL_RE.findall(expr)
    if not skills:
        assumptions.append("No skill('X'.blvl) terms found in synergy expression; treating synergy as 0%.")
        return 0.0, assumptions

    total_levels = 0
    missing: list[str] = []
    for s in skills:
        lvl = int(synergy_levels.get(s, 0))
        total_levels += max(lvl, 0)
        if s not in synergy_levels:
            missing.append(s)
    if missing:
        assumptions.append(
            "Missing explicit synergy levels for "
            + ", ".join(missing)
            + "; defaulted those skills to level 0."
        )

    return total_levels * par_val, assumptions


def estimate_damage(
    conn: sqlite3.Connection,
    *,
    class_name: str,
    skill_name: str,
    skill_level: int,
    plus_skills: int,
    synergy_levels: dict[str, int],
    enemy_resist: float,
    sunder: bool,
) -> SkillDamageEstimate:
    issues: list[dict[str, Any]] = []
    assumptions: list[str] = []

    class_code = _canonical_class_code(class_name)
    row = _find_skill(conn, class_code, skill_name)
    if row is None:
        raise ValueError(f"Skill not found for class '{class_name}': {skill_name}")

    effective = max(skill_level + plus_skills, 1)
    emin = _fnum(row["emin"])
    emax = _fnum(row["emax"])
    if emin <= 0 and emax <= 0:
        issues.append({
            "code": "DB_INCOMPLETE",
            "message": "Skill has no emin/emax elemental damage fields in DB; cannot estimate direct damage.",
            "context": {"skill": row["skill"]},
        })
    base_min = _d2_scaled_component(emin, effective, row, "emin")
    base_max = _d2_scaled_component(emax, effective, row, "emax")
    assumptions.append("Damage estimate uses emin/emax + eminlev*/emaxlev* piecewise level brackets from game.db.")

    synergy_pct, synergy_notes = _synergy_bonus_percent(row, synergy_levels)
    assumptions.extend(synergy_notes)

    scaled_min = base_min * (1.0 + synergy_pct / 100.0)
    scaled_max = base_max * (1.0 + synergy_pct / 100.0)

    hitshift = int(_fnum(row["hitshift"]))
    display_scale = 2 ** (hitshift - 8)
    if hitshift != 8:
        assumptions.append(f"Applied hitshift display scale 2^({hitshift}-8) = {display_scale}.")
    scaled_min *= display_scale
    scaled_max *= display_scale

    resist_after = enemy_resist
    if sunder and resist_after > 95:
        resist_after = 95
        assumptions.append("Sunder enabled: enemy resistance above 95 was clamped to 95.")
    resist_after = max(min(resist_after, 99), -100)
    resist_mult = 1.0 - (resist_after / 100.0)

    final_min = scaled_min * resist_mult
    final_max = scaled_max * resist_mult

    return SkillDamageEstimate(
        skill_name=str(row["skill"]),
        class_code=str(row["charclass"]),
        skill_level=skill_level,
        plus_skills=plus_skills,
        effective_skill_level=effective,
        base_damage_min=round(base_min, 3),
        base_damage_max=round(base_max, 3),
        synergy_bonus_pct=round(synergy_pct, 3),
        enemy_resist_initial=enemy_resist,
        enemy_resist_after_mods=round(resist_after, 3),
        final_damage_min=round(final_min, 3),
        final_damage_max=round(final_max, 3),
        assumptions=assumptions,
        issues=issues,
    )


def _character_skill_levels(character_path: str) -> tuple[str, str, dict[str, int]]:
    char = CharacterParser().parse_file(character_path).model_dump(mode="json")
    class_name = str(char.get("character_type") or "")
    char_name = str(char.get("name") or "")
    levels: dict[str, int] = {}
    for sk in char.get("skills", []) or []:
        if isinstance(sk, dict):
            name = str(sk.get("name") or "").strip()
            lvl = int(sk.get("level") or 0)
            if name:
                levels[name] = lvl
    return class_name, char_name, levels


def _parse_synergy_args(raw_values: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for raw in raw_values:
        if "=" not in raw:
            raise ValueError(f"Invalid --synergy '{raw}'. Expected format: Skill Name=Level")
        skill, lvl = raw.split("=", 1)
        parsed[skill.strip()] = int(lvl.strip())
    return parsed


def _lookup_monster_by_hcidx(conn: sqlite3.Connection, hcidx: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM monstats WHERE x_hcidx = ?", (str(hcidx),)).fetchone()


def _resolve_pet_monster_for_summon(conn: sqlite3.Connection, summon_row: sqlite3.Row) -> tuple[sqlite3.Row | None, list[str]]:
    assumptions: list[str] = []
    pet_type = str(summon_row["pettype"] or "").strip().lower()
    if not pet_type:
        return None, assumptions

    pet_row = conn.execute("SELECT * FROM pettype WHERE pet_type = ?", (pet_type,)).fetchone()
    if pet_row is None:
        return None, assumptions

    name = str(summon_row["skill"] or "").lower()
    choices: list[tuple[str, int]] = []
    for i in range(1, 5):
        mclass = str(pet_row[f"mclass{i}"] or "").strip()
        override = str(pet_row[f"overridename{i}"] or "").strip()
        if not mclass:
            continue
        try:
            hcidx = int(mclass)
        except ValueError:
            continue
        choices.append((override.lower(), hcidx))

    if not choices:
        return None, assumptions

    # Prefer a matching override name by token, fallback first entry.
    matched_hcidx: int | None = None
    for override, hcidx in choices:
        if not override:
            continue
        key = override.replace("war", "").strip()
        if key and key in name:
            matched_hcidx = hcidx
            assumptions.append(f"Matched summon '{summon_row['skill']}' to pet override '{override}'.")
            break
    if matched_hcidx is None:
        matched_hcidx = choices[0][1]
        assumptions.append("Could not match summon name to pet override; used first pettype entry.")

    mon_row = _lookup_monster_by_hcidx(conn, matched_hcidx)
    return mon_row, assumptions


def _estimate_pet_count(summon_row: sqlite3.Row, synergy_levels: dict[str, int]) -> tuple[int, list[str]]:
    expr = str(summon_row["petmax"] or "").strip()
    assumptions: list[str] = []
    if not expr:
        return 1, assumptions

    # POC parser for common threshold pattern used by Warlock summons:
    # (skill('Demonic Mastery'.blvl)>=10)?3:((skill('Demonic Mastery'.blvl)>=5)?2:1)
    m = re.match(
        r"\(skill\('([^']+)'\.blvl\)>=([0-9]+)\)\?([0-9]+):\(\(skill\('\1'\.blvl\)>=([0-9]+)\)\?([0-9]+):([0-9]+)\)",
        expr,
    )
    if m:
        skill_name = m.group(1)
        high_req = int(m.group(2))
        high_val = int(m.group(3))
        low_req = int(m.group(4))
        low_val = int(m.group(5))
        base_val = int(m.group(6))
        lvl = int(synergy_levels.get(skill_name, 0))
        if lvl >= high_req:
            return high_val, assumptions
        if lvl >= low_req:
            return low_val, assumptions
        return base_val, assumptions

    assumptions.append("petmax formula not parsed; defaulted pet count to 1.")
    return 1, assumptions


def estimate_pet(
    conn: sqlite3.Connection,
    *,
    class_name: str,
    skill_name: str,
    skill_level: int,
    plus_skills: int,
    synergy_levels: dict[str, int],
) -> PetEstimate:
    issues: list[dict[str, Any]] = []
    assumptions: list[str] = []
    class_code = _canonical_class_code(class_name)
    row = _find_skill(conn, class_code, skill_name)
    if row is None:
        raise ValueError(f"Skill not found for class '{class_name}': {skill_name}")

    effective = max(skill_level + plus_skills, 1)
    pet_type = str(row["pettype"] or "")
    if not pet_type:
        issues.append({
            "code": "NOT_A_PET_SKILL",
            "message": "Skill does not define pettype; cannot estimate summon stats.",
            "context": {"skill": row["skill"]},
        })

    pet_row: sqlite3.Row | None = None
    if pet_type:
        pet_row, pet_notes = _resolve_pet_monster_for_summon(conn, row)
        assumptions.extend(pet_notes)

    pet_count, count_notes = _estimate_pet_count(row, synergy_levels)
    assumptions.extend(count_notes)

    min_d = 0.0
    max_d = 0.0
    min_hp = 0.0
    max_hp = 0.0
    pet_monster_id = ""
    if pet_row is not None:
        pet_monster_id = str(pet_row["id"])
        min_d = _fnum(pet_row["a1mind"])
        max_d = _fnum(pet_row["a1maxd"])
        min_hp = _fnum(pet_row["minhp"])
        max_hp = _fnum(pet_row["maxhp"])
        assumptions.append("Pet damage/HP uses monstats base fields (a1mind/a1maxd/minhp/maxhp) as a POC baseline.")
    elif pet_type:
        issues.append({
            "code": "DB_INCOMPLETE",
            "message": "Could not resolve summoned monster row from pettype/mclass mapping.",
            "context": {"skill": row["skill"], "pettype": pet_type},
        })

    dmg_bonus_pct = 0.0
    hp_bonus_pct = 0.0

    passive_dmg_expr = str(row["passivecalc1"] or "").strip()
    passive_hp_expr = str(row["passivecalc2"] or "").strip()
    if passive_dmg_expr:
        v, a, i = _eval_formula_expr(
            passive_dmg_expr,
            current_skill_row=row,
            current_skill_level=effective,
            conn=conn,
            extra_levels=synergy_levels,
        )
        dmg_bonus_pct = v
        assumptions.extend(a)
        issues.extend(i)
    if passive_hp_expr:
        v, a, i = _eval_formula_expr(
            passive_hp_expr,
            current_skill_row=row,
            current_skill_level=effective,
            conn=conn,
            extra_levels=synergy_levels,
        )
        hp_bonus_pct = v
        assumptions.extend(a)
        issues.extend(i)

    scaled_min = min_d * (1.0 + (dmg_bonus_pct / 100.0))
    scaled_max = max_d * (1.0 + (dmg_bonus_pct / 100.0))
    scaled_hp_min = min_hp * (1.0 + (hp_bonus_pct / 100.0))
    scaled_hp_max = max_hp * (1.0 + (hp_bonus_pct / 100.0))

    return PetEstimate(
        summon_skill=str(row["skill"]),
        class_code=str(row["charclass"]),
        skill_level=skill_level,
        plus_skills=plus_skills,
        effective_skill_level=effective,
        pet_type=pet_type,
        pet_monster_id=pet_monster_id,
        pet_count=pet_count,
        pet_base_damage_min=round(min_d, 3),
        pet_base_damage_max=round(max_d, 3),
        pet_base_hp_min=round(min_hp, 3),
        pet_base_hp_max=round(max_hp, 3),
        pet_damage_bonus_pct=round(dmg_bonus_pct, 3),
        pet_hp_bonus_pct=round(hp_bonus_pct, 3),
        pet_scaled_damage_min=round(scaled_min, 3),
        pet_scaled_damage_max=round(scaled_max, 3),
        pet_scaled_hp_min=round(scaled_hp_min, 3),
        pet_scaled_hp_max=round(scaled_hp_max, 3),
        assumptions=assumptions,
        issues=issues,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="POC skill damage calculator using game.db fields")
    parser.add_argument("--mode", choices=["direct", "pet"], default="direct", help="Estimate direct skill damage or pet summon baseline")
    parser.add_argument("--class", dest="class_name", required=True, help="Class name/code, e.g. warlock or war")
    parser.add_argument("--skill", dest="skill_name", required=True, help="Skill name")
    parser.add_argument("--skill-level", type=int, required=True, help="Hard points in selected skill")
    parser.add_argument("--plus-skills", type=int, default=0, help="+All/+Class/+Tree skill levels")
    parser.add_argument(
        "--synergy",
        action="append",
        default=[],
        help="Synergy contribution as Skill Name=Level (repeatable)",
    )
    parser.add_argument("--enemy-resist", type=float, default=0.0, help="Enemy resistance percent")
    parser.add_argument("--sunder", action="store_true", help="Apply sunder clamp (resists >95 become 95)")
    parser.add_argument("--character-path", type=str, default="", help="Optional .d2s path to auto-fill skill levels")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    synergies = _parse_synergy_args(args.synergy)
    character_meta: dict[str, Any] = {}
    if args.character_path:
        class_name_from_char, char_name, levels = _character_skill_levels(args.character_path)
        character_meta = {
            "character_name": char_name,
            "character_class": class_name_from_char,
            "character_path": args.character_path,
        }
        if not args.class_name:
            args.class_name = class_name_from_char
        if args.skill_name in levels and args.skill_level <= 0:
            args.skill_level = levels[args.skill_name]
        if args.mode == "direct":
            row = _find_skill(conn, _canonical_class_code(args.class_name), args.skill_name)
            if row is not None:
                for syn in _SKILL_RE.findall(str(row["edmgsympercalc"] or "")):
                    if syn not in synergies and syn in levels:
                        synergies[syn] = levels[syn]
                        character_meta.setdefault("auto_synergies", {})[syn] = levels[syn]
        if args.mode == "pet":
            for key in ["Demonic Mastery", "Blood Oath"]:
                if key not in synergies and key in levels:
                    synergies[key] = levels[key]
                    character_meta.setdefault("auto_synergies", {})[key] = levels[key]
    if args.mode == "pet":
        estimate = estimate_pet(
            conn,
            class_name=args.class_name,
            skill_name=args.skill_name,
            skill_level=args.skill_level,
            plus_skills=args.plus_skills,
            synergy_levels=synergies,
        )
    else:
        estimate = estimate_damage(
            conn,
            class_name=args.class_name,
            skill_name=args.skill_name,
            skill_level=args.skill_level,
            plus_skills=args.plus_skills,
            synergy_levels=synergies,
            enemy_resist=args.enemy_resist,
            sunder=args.sunder,
        )

    payload = estimate.__dict__
    if character_meta:
        payload["character_context"] = character_meta
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
