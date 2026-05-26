from __future__ import annotations

from typing import Any


def _resolve_property_display(
    tooltip: str,
    param_desc: str,
    param: str,
    min_val: str,
    max_val: str,
) -> str:
    display = tooltip

    if "[Skill]" in display and param:
        display = display.replace("[Skill]", param)

    replacement = ""
    if min_val:
        if max_val and max_val != min_val:
            replacement = f"{min_val}-{max_val}"
        else:
            replacement = min_val
    elif param and "/" in param_desc and "per Level" in param_desc:
        parts = param_desc.split("/")
        divisor_str = parts[1].strip().split()[0] if len(parts) > 1 else "1"
        try:
            ratio = float(param) / float(divisor_str)
            formatted = f"{ratio:.4f}".rstrip("0").rstrip(".")
            replacement = f"[+{formatted} per Level]"
        except (ValueError, ZeroDivisionError):
            replacement = param_desc
    elif param:
        replacement = param

    if replacement:
        display = display.replace("#", replacement, 1)

    return display


def _get_base_name(gd: Any, code: str) -> str | None:
    for table in ("weapons", "armor", "misc"):
        row = gd.conn.execute(
            f'SELECT name FROM "{table}" WHERE code = ?',
            (code,),
        ).fetchone()
        if row:
            return row["name"]
    return None


def _get_rune_name(gd: Any, code: str) -> str:
    row = gd.conn.execute(
        "SELECT name FROM misc WHERE code = ? AND name LIKE '% Rune'",
        (code,),
    ).fetchone()
    if row:
        raw = row["name"]
        if raw.endswith(" Rune"):
            return raw[:-5]
        return raw
    return code


def _build_property_lines(
    gd: Any,
    row: dict[str, Any],
    *,
    code_prefix: str,
    param_prefix: str,
    min_prefix: str,
    max_prefix: str,
    count: int,
) -> list[str]:
    properties: list[str] = []
    for i in range(1, count + 1):
        code = row.get(f"{code_prefix}{i}", "")
        if not code:
            continue
        prop_row = gd.conn.execute(
            "SELECT x_tooltip, x_parameter FROM properties WHERE code = ?",
            (code,),
        ).fetchone()
        if not prop_row or not prop_row["x_tooltip"]:
            continue
        display = _resolve_property_display(
            prop_row["x_tooltip"],
            prop_row["x_parameter"] or "",
            row.get(f"{param_prefix}{i}", "") or "",
            row.get(f"{min_prefix}{i}", "") or "",
            row.get(f"{max_prefix}{i}", "") or "",
        )
        if display:
            properties.append(display)
    return properties


def _format_runeword(row: dict[str, Any], gd: Any) -> dict[str, Any]:
    properties = _build_property_lines(
        gd,
        row,
        code_prefix="t1code",
        param_prefix="t1param",
        min_prefix="t1min",
        max_prefix="t1max",
        count=7,
    )

    runes: list[str] = []
    for i in range(1, 7):
        rc = row.get(f"rune{i}", "")
        if rc:
            rune_name = _get_rune_name(gd, rc)
            runes.append(rune_name)

    return {
        "name": row.get("x_rune_name", ""),
        "quality": "runeword",
        "base_hint": f'{len(runes)}-Socket Item',
        "runes": runes,
        "properties": properties,
    }


def _format_unique(row: dict[str, Any], gd: Any) -> dict[str, Any]:
    properties = _build_property_lines(
        gd,
        row,
        code_prefix="prop",
        param_prefix="par",
        min_prefix="min",
        max_prefix="max",
        count=12,
    )

    base_code = row.get("code", "")
    base_name = _get_base_name(gd, base_code)

    return {
        "name": row.get("index", ""),
        "quality": "unique",
        "base_name": base_name,
        "base_code": base_code,
        "level_req": int(row["lvl_req"]) if row.get("lvl_req") else None,
        "properties": properties,
    }


def _format_setitem(row: dict[str, Any], gd: Any) -> dict[str, Any]:
    properties = _build_property_lines(
        gd,
        row,
        code_prefix="prop",
        param_prefix="par",
        min_prefix="min",
        max_prefix="max",
        count=9,
    )

    base_code = row.get("item", "")
    base_name = _get_base_name(gd, base_code)
    set_name = row.get("set", "")

    return {
        "name": row.get("index", ""),
        "quality": "set",
        "set_name": set_name,
        "base_name": base_name,
        "base_code": base_code,
        "level_req": int(row["lvl_req"]) if row.get("lvl_req") else None,
        "properties": properties,
    }


def _format_skill(row: dict[str, Any]) -> dict[str, Any]:
    class_name = str(row.get("charclass", "") or "")
    skill_desc = str(row.get("str_long", "") or row.get("str_short", "") or "")
    req_level = int(row["reqlevel"]) if row.get("reqlevel") else None

    return {
        "name": str(row.get("skill", "")),
        "quality": "skill",
        "class": class_name,
        "description": skill_desc,
        "level_req": req_level,
        "properties": [],
    }


def _format_base_item(row: dict[str, Any], table: str) -> dict[str, Any]:
    props: list[str] = []
    if table == "weapons":
        min_d = row.get("mindam")
        max_d = row.get("maxdam")
        if min_d and max_d:
            props.append(f"Damage: {min_d}-{max_d}")
        speed = row.get("speed")
        if speed:
            props.append(f"Speed: {speed}")
    elif table == "armor":
        min_ac = row.get("minac")
        max_ac = row.get("maxac")
        if min_ac and max_ac:
            props.append(f"Defense: {min_ac}-{max_ac}")
        speed = row.get("speed")
        if speed:
            props.append(f"Speed: {speed}")
    elif table == "misc":
        speed = row.get("speed")
        if speed:
            props.append(f"Speed: {speed}")

    reqs: list[str] = []
    if row.get("levelreq"):
        reqs.append(f"Lvl {row['levelreq']}")
    if row.get("reqstr"):
        reqs.append(f"Str {row['reqstr']}")
    if row.get("reqdex"):
        reqs.append(f"Dex {row['reqdex']}")
    if reqs:
        props.append("Req: " + ", ".join(reqs))

    sockets = row.get("gemsockets")
    if sockets and sockets != "0":
        props.append(f"Max Sockets: {sockets}")

    return {
        "name": row.get("name", ""),
        "quality": "base",
        "code": row.get("code", ""),
        "type": row.get("type", ""),
        "properties": props,
    }


def _query_base_item(gd: Any, table: str, q: str) -> dict[str, Any] | None:
    common_cols = 'name, code, type, levelreq, reqstr, reqdex, gemsockets'
    if table == "weapons":
        cols = f"{common_cols}, mindam, maxdam, speed"
    elif table == "armor":
        cols = f"{common_cols}, minac, maxac, speed"
    elif table == "misc":
        cols = f"{common_cols}, speed"
    else:
        return None
    row = gd.conn.execute(
        f'SELECT {cols} FROM "{table}" WHERE LOWER("name") = ? AND "spawnable" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return dict(row)
    return None


def lookup_item_data(gd: Any, name: str, item_type: str) -> dict[str, Any] | None:
    q = name.strip().lower()
    normalized_type = item_type.strip().lower()

    if normalized_type in ("rw", "runeword"):
        row = gd.conn.execute(
            'SELECT * FROM runes WHERE LOWER("x_rune_name") = ? AND "complete" = ?',
            (q, "1"),
        ).fetchone()
        return _format_runeword(dict(row), gd) if row else None

    if normalized_type in ("unq", "unique"):
        row = gd.conn.execute(
            'SELECT * FROM uniqueitems WHERE LOWER("index") = ? AND "spawnable" = ?',
            (q, "1"),
        ).fetchone()
        return _format_unique(dict(row), gd) if row else None

    if normalized_type in ("set",):
        row = gd.conn.execute(
            'SELECT * FROM setitems WHERE LOWER("index") = ? AND "spawnable" = ?',
            (q, "1"),
        ).fetchone()
        return _format_setitem(dict(row), gd) if row else None

    if normalized_type in ("base",):
        for table in ("weapons", "armor", "misc"):
            row = _query_base_item(gd, table, q)
            if row:
                return _format_base_item(row, table)
        return None

    if normalized_type in ("skill",):
        row = gd.conn.execute(
            'SELECT s.*, sd.str_name, sd.str_short, sd.str_long FROM skills s '
            'JOIN skilldesc sd ON s.skilldesc = sd.skilldesc '
            'WHERE LOWER(s.skill) = ?',
            (q,),
        ).fetchone()
        return _format_skill(dict(row)) if row else None

    row = gd.conn.execute(
        'SELECT * FROM runes WHERE LOWER("x_rune_name") = ? AND "complete" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return _format_runeword(dict(row), gd)

    row = gd.conn.execute(
        'SELECT * FROM uniqueitems WHERE LOWER("index") = ? AND "spawnable" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return _format_unique(dict(row), gd)

    row = gd.conn.execute(
        'SELECT * FROM setitems WHERE LOWER("index") = ? AND "spawnable" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return _format_setitem(dict(row), gd)

    for table in ("weapons", "armor", "misc"):
        row = _query_base_item(gd, table, q)
        if row:
            return _format_base_item(row, table)

    return None


__all__ = ["lookup_item_data"]
