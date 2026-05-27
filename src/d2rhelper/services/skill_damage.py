from __future__ import annotations

import re
from typing import Any


_CLASS_ALIASES = {
    "amazon": "ama",
    "assassin": "ass",
    "barbarian": "bar",
    "druid": "dru",
    "necromancer": "nec",
    "paladin": "pal",
    "sorceress": "sor",
    "warlock": "war",
}

_SKILL_RE = re.compile(r"skill\('([^']+)'\.blvl\)")
_PAR_RE = re.compile(r"par(\d+)")


def _fnum(raw: Any) -> float:
    if raw in (None, ""):
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _canonical_class_code(class_name: str) -> str:
    key = class_name.strip().lower()
    return _CLASS_ALIASES.get(key, key)


def _find_skill_row(gd: Any, class_code: str, skill_name: str) -> dict[str, Any] | None:
    row = gd.conn.execute(
        'SELECT * FROM skills WHERE charclass = ? AND LOWER(skill) = ?',
        (class_code, skill_name.strip().lower()),
    ).fetchone()
    if row:
        return dict(row)
    row = gd.conn.execute(
        'SELECT * FROM skills WHERE charclass = ? AND LOWER(skill) LIKE ? ORDER BY skill LIMIT 1',
        (class_code, f"%{skill_name.strip().lower()}%"),
    ).fetchone()
    return dict(row) if row else None


def _scaled_component(base: float, level: int, row: dict[str, Any], prefix: str) -> float:
    if level <= 1:
        return base
    remaining = level - 1
    brackets = [
        (7, _fnum(row.get(f"{prefix}lev1"))),
        (8, _fnum(row.get(f"{prefix}lev2"))),
        (6, _fnum(row.get(f"{prefix}lev3"))),
        (6, _fnum(row.get(f"{prefix}lev4"))),
        (999, _fnum(row.get(f"{prefix}lev5"))),
    ]
    value = base
    for size, inc in brackets:
        if remaining <= 0:
            break
        steps = min(remaining, size)
        value += steps * inc
        remaining -= steps
    return value


def _synergy_bonus_percent(row: dict[str, Any], synergy_levels: dict[str, int]) -> tuple[float, list[str]]:
    expr = str(row.get("edmgsympercalc") or "").strip()
    if not expr:
        return 0.0, []
    notes: list[str] = []
    par_match = _PAR_RE.search(expr)
    if not par_match:
        return 0.0, ["No parN multiplier found in synergy expression; synergy treated as 0%."]
    par_idx = int(par_match.group(1))
    par_val = _fnum(row.get(f"param{par_idx}"))
    skills = _SKILL_RE.findall(expr)
    total_levels = 0
    missing: list[str] = []
    for name in skills:
        lvl = int(synergy_levels.get(name, 0))
        total_levels += max(lvl, 0)
        if name not in synergy_levels:
            missing.append(name)
    if missing:
        notes.append(
            "Missing explicit synergy levels for " + ", ".join(missing) + "; defaulted those skills to level 0."
        )
    return total_levels * par_val, notes


def estimate_skill_damage(
    gd: Any,
    *,
    class_name: str,
    skill_name: str,
    skill_level: int,
    plus_skills: int = 0,
    synergy_levels: dict[str, int] | None = None,
    enemy_resist: float = 0.0,
    sunder: bool = False,
) -> dict[str, Any]:
    synergy_levels = synergy_levels or {}
    assumptions: list[str] = []
    issues: list[dict[str, Any]] = []

    class_code = _canonical_class_code(class_name)
    row = _find_skill_row(gd, class_code, skill_name)
    if row is None:
        return {
            "ok": False,
            "error": f"Skill not found for class '{class_name}': {skill_name}",
        }

    effective = max(int(skill_level) + int(plus_skills), 1)
    emin = _fnum(row.get("emin"))
    emax = _fnum(row.get("emax"))
    if emin <= 0 and emax <= 0:
        issues.append(
            {
                "code": "DB_INCOMPLETE",
                "message": "Skill has no emin/emax elemental damage fields in DB; cannot estimate direct damage.",
                "context": {"skill": row.get("skill", "")},
            }
        )

    base_min = _scaled_component(emin, effective, row, "emin")
    base_max = _scaled_component(emax, effective, row, "emax")
    assumptions.append("Damage uses emin/emax + eminlev*/emaxlev* piecewise level brackets.")

    synergy_pct, synergy_notes = _synergy_bonus_percent(row, synergy_levels)
    assumptions.extend(synergy_notes)

    scaled_min = base_min * (1.0 + synergy_pct / 100.0)
    scaled_max = base_max * (1.0 + synergy_pct / 100.0)

    hitshift = int(_fnum(row.get("hitshift")))
    display_scale = 2 ** (hitshift - 8)
    if hitshift != 8:
        assumptions.append(f"Applied hitshift display scale 2^({hitshift}-8) = {display_scale}.")
    scaled_min *= display_scale
    scaled_max *= display_scale

    resist_after = float(enemy_resist)
    if sunder and resist_after > 95:
        resist_after = 95
        assumptions.append("Sunder enabled: enemy resistance above 95 was clamped to 95.")
    resist_after = max(min(resist_after, 99), -100)
    resist_mult = 1.0 - (resist_after / 100.0)

    final_min = scaled_min * resist_mult
    final_max = scaled_max * resist_mult

    return {
        "ok": True,
        "skill_name": str(row.get("skill", "")),
        "class_code": str(row.get("charclass", "")),
        "skill_level": int(skill_level),
        "plus_skills": int(plus_skills),
        "effective_skill_level": effective,
        "base_damage_min": round(base_min, 3),
        "base_damage_max": round(base_max, 3),
        "synergy_bonus_pct": round(synergy_pct, 3),
        "enemy_resist_initial": float(enemy_resist),
        "enemy_resist_after_mods": round(resist_after, 3),
        "final_damage_min": round(final_min, 3),
        "final_damage_max": round(final_max, 3),
        "assumptions": assumptions,
        "issues": issues,
    }


__all__ = ["estimate_skill_damage"]
