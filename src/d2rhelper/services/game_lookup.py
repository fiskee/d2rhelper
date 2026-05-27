from __future__ import annotations

from typing import Any

from d2rhelper.services.item_lookup import lookup_item_data


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


def _canon_class_code(class_name: str) -> str:
    key = class_name.strip().lower()
    return _CLASS_ALIASES.get(key, key)


def lookup_skill_data(gd: Any, skill_name: str, class_name: str = "") -> dict[str, Any] | None:
    q = skill_name.strip().lower()
    if not q:
        return None

    args: list[Any] = []
    sql = (
        "SELECT s.*, sd.skillpage, sd.skillrow, sd.skillcolumn, sd.str_name, sd.str_short, sd.str_long "
        "FROM skills s JOIN skilldesc sd ON s.skilldesc = sd.skilldesc "
        "WHERE LOWER(s.skill) = ?"
    )
    args.append(q)
    class_code = _canon_class_code(class_name) if class_name else ""
    if class_code:
        sql += " AND s.charclass = ?"
        args.append(class_code)
    sql += " LIMIT 1"

    row = gd.conn.execute(sql, tuple(args)).fetchone()
    if row is None:
        sql_like = (
            "SELECT s.*, sd.skillpage, sd.skillrow, sd.skillcolumn, sd.str_name, sd.str_short, sd.str_long "
            "FROM skills s JOIN skilldesc sd ON s.skilldesc = sd.skilldesc "
            "WHERE LOWER(s.skill) LIKE ?"
        )
        args_like: list[Any] = [f"%{q}%"]
        if class_code:
            sql_like += " AND s.charclass = ?"
            args_like.append(class_code)
        sql_like += " ORDER BY s.skill LIMIT 1"
        row = gd.conn.execute(sql_like, tuple(args_like)).fetchone()
        if row is None:
            return None

    item = dict(row)
    reqs = [str(item.get("reqskill1", "") or ""), str(item.get("reqskill2", "") or ""), str(item.get("reqskill3", "") or "")]
    prerequisites = [r for r in reqs if r]

    receives_from: list[dict[str, Any]] = []
    qname = str(item.get("skill", ""))
    sy_rows = gd.conn.execute("SELECT skill, edmgsympercalc FROM skills WHERE edmgsympercalc LIKE ?", (f"%skill('{qname}'.blvl)%",)).fetchall()
    for sy in sy_rows:
        expr = str(sy["edmgsympercalc"] or "")
        receives_from.append({"skill": str(sy["skill"]), "expression": expr})

    return {
        "name": str(item.get("skill", "")),
        "class_code": str(item.get("charclass", "")),
        "required_level": int(item.get("reqlevel") or 0),
        "tree": {
            "tab_index": int(item.get("skillpage") or 0),
            "row": int(item.get("skillrow") or 0),
            "column": int(item.get("skillcolumn") or 0),
        },
        "prerequisites": prerequisites,
        "description": str(item.get("str_long") or item.get("str_short") or item.get("str_name") or ""),
        "damage_formula": {
            "emin": item.get("emin", ""),
            "emax": item.get("emax", ""),
            "edmgsympercalc": item.get("edmgsympercalc", ""),
            "hitshift": item.get("hitshift", ""),
        },
        "synergy_sources": receives_from,
    }


def list_class_skills(gd: Any, class_name: str) -> dict[str, Any]:
    class_code = _canon_class_code(class_name)
    rows = gd.conn.execute(
        "SELECT s.skill, s.reqlevel, s.reqskill1, s.reqskill2, s.reqskill3, s.charclass, sd.skillpage, sd.skillrow, sd.skillcolumn "
        "FROM skills s JOIN skilldesc sd ON s.skilldesc = sd.skilldesc "
        "WHERE s.charclass = ? ORDER BY sd.skillpage, s.reqlevel, s.skill",
        (class_code,),
    ).fetchall()

    skills: list[dict[str, Any]] = []
    for r in rows:
        rr = dict(r)
        prereq = [x for x in [rr.get("reqskill1", ""), rr.get("reqskill2", ""), rr.get("reqskill3", "")] if x]
        skills.append(
            {
                "name": str(rr.get("skill", "")),
                "required_level": int(rr.get("reqlevel") or 0),
                "tree": {
                    "tab_index": int(rr.get("skillpage") or 0),
                    "row": int(rr.get("skillrow") or 0),
                    "column": int(rr.get("skillcolumn") or 0),
                },
                "prerequisites": [str(v) for v in prereq],
            }
        )

    return {
        "class_code": class_code,
        "total_skills": len(skills),
        "skills": skills,
    }


def lookup_game_item(gd: Any, name: str, item_type: str = "") -> dict[str, Any] | None:
    return lookup_item_data(gd, name, item_type)


__all__ = ["lookup_skill_data", "list_class_skills", "lookup_game_item"]
