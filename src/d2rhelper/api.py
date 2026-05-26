from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from d2rhelper.chat_store import get_chat_store
from d2rhelper.game_data import GameData
from d2rhelper.models import ItemQuality
from d2rhelper.parser import CharacterParser
from d2rhelper.shared_stash_parser import SharedStashParser
from d2rhelper.casc import find_all_character_files, find_local_character_file, find_local_shared_stash_file

load_dotenv()

app = FastAPI(title="D2R Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_game_data: GameData | None = None
_autocomplete_cache: list[str] | None = None
_parse_cache: dict[str, dict[str, Any]] = {}
_parse_mtime: dict[str, float] = {}


def get_game_data() -> GameData:
    global _game_data
    if _game_data is None:
        _game_data = GameData.get_instance()
    return _game_data


def get_autocomplete_items() -> list[str]:
    global _autocomplete_cache
    if _autocomplete_cache is not None:
        return _autocomplete_cache

    gd = get_game_data()
    names: set[str] = set()

    for table in ("weapons", "armor", "misc"):
        rows = gd.conn.execute(f'SELECT "name" FROM "{table}" WHERE "name" != \'\'').fetchall()
        for row in rows:
            name = str(row["name"])
            if name:
                names.add(name)

    for row in gd.conn.execute('SELECT "index" FROM uniqueitems WHERE "spawnable" = \'1\'').fetchall():
        name = str(row["index"])
        if name:
            names.add(name)

    for row in gd.conn.execute('SELECT "index" FROM setitems').fetchall():
        name = str(row["index"])
        if name:
            names.add(name)

    for row in gd.conn.execute('SELECT "x_rune_name" FROM runes WHERE "complete" = \'1\'').fetchall():
        name = str(row["x_rune_name"])
        if name:
            names.add(name)

    _autocomplete_cache = sorted(names)
    return _autocomplete_cache


class ParseRequest(BaseModel):
    character_path: str
    stash_path: str | None = None


def _parse_files(character_path: str, stash_path: str | None = None) -> dict[str, Any]:
    cache_key = f"{character_path}::{stash_path or ''}"

    try:
        char_mtime = os.path.getmtime(character_path)
    except OSError:
        char_mtime = 0

    if cache_key in _parse_cache and _parse_mtime.get(cache_key) == char_mtime:
        return _parse_cache[cache_key]

    character = CharacterParser().parse_file(character_path)
    tabs = []
    if stash_path:
        try:
            tabs = SharedStashParser().parse_file(stash_path)
        except Exception:
            pass

    result = {
        "character": character.model_dump(mode="json"),
        "stash_tabs": [tab.model_dump(mode="json") for tab in tabs],
    }
    _parse_cache[cache_key] = result
    _parse_mtime[cache_key] = char_mtime
    return result


def _search_items(
    query: str,
    character_path: str,
    stash_path: str | None = None,
) -> list[dict[str, Any]]:
    data = _parse_files(character_path, stash_path)
    q = query.lower()
    results: list[dict[str, Any]] = []

    from d2rhelper.models import D2Character, SharedStashTab

    char = D2Character.model_validate(data["character"])
    tabs = [SharedStashTab.model_validate(t) for t in data["stash_tabs"]]

    quality_names = {v.value: v.name for v in ItemQuality}

    all_sources: list[tuple[Any, str, int | None]] = []
    all_sources.append((char.items, "character", None))
    all_sources.append((char.mercenary.items, "mercenary", None))
    for i, tab in enumerate(tabs):
        all_sources.append((tab.items, f"stash_tab_{i + 1}", i))

    for items, source, tab_idx in all_sources:
        for item in items:
            score = 0
            name = (item.display_name or item.item_name or "").lower()
            item_name = (item.item_name or "").lower()
            set_name = (item.set_name or "").lower()
            rw_name = (item.runeword_name or "").lower()
            uniq_name = (item.unique_name or "").lower()
            code = (item.code or "").lower()
            quality_str = quality_names.get(item.quality, "").lower()

            if name == q:
                score += 100
            elif name.startswith(q):
                score += 50
            elif q in name:
                score += 20

            if q in item_name:
                score += 15
            if q in set_name:
                score += 40
            if q in rw_name:
                score += 40
            if q in uniq_name:
                score += 40
            if q in code:
                score += 5
            if q in quality_str:
                score += 5

            for prop in item.properties:
                if (prop.display_text or "").lower().find(q) >= 0:
                    score += 30
                    break

            if score > 0:
                results.append({
                    "item": item.model_dump(mode="json"),
                    "source": source,
                    "tab_index": tab_idx,
                    "score": score,
                })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:50]


@app.get("/api/autocomplete")
async def autocomplete(q: str = "") -> JSONResponse:
    if len(q) < 2:
        return JSONResponse(content=[])
    items = get_autocomplete_items()
    ql = q.lower()
    matches = [name for name in items if ql in name.lower()]
    matches.sort(key=lambda n: (0 if n.lower().startswith(ql) else 1, n.lower()))
    return JSONResponse(content=matches[:10])


@app.get("/api/characters")
async def list_characters() -> JSONResponse:
    try:
        characters = find_all_character_files()
        stash_path = find_local_shared_stash_file()
        return JSONResponse(content={
            "characters": [c.model_dump(mode="json") for c in characters],
            "stash_path": str(stash_path) if stash_path else None,
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/parse")
async def parse(req: ParseRequest) -> JSONResponse:
    try:
        result = _parse_files(req.character_path, req.stash_path)
        return JSONResponse(content=result)
    except FileNotFoundError as e:
        return JSONResponse(content={"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/parse/auto")
async def parse_auto() -> JSONResponse:
    try:
        char_path = find_local_character_file()
        if char_path is None:
            return JSONResponse(
                content={"error": "Could not auto-detect local .d2s file"},
                status_code=404,
            )
        stash_path = find_local_shared_stash_file()
        result = _parse_files(str(char_path), str(stash_path) if stash_path else None)
        result["character_path"] = str(char_path)
        if stash_path:
            result["stash_path"] = str(stash_path)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/search")
async def search(
    q: str = "",
    character_path: str = "",
    character_paths: str = "",
    stash_path: str = "",
) -> JSONResponse:
    if not q or len(q) < 2:
        return JSONResponse(content=[])
    paths: list[str] = []
    if character_paths:
        try:
            paths = json.loads(character_paths)
        except json.JSONDecodeError:
            pass
    if character_path and character_path not in paths:
        paths.append(character_path)
    if not paths:
        return JSONResponse(content=[])
    try:
        all_results: list[dict[str, Any]] = []
        for cp in paths:
            all_results.extend(_search_items(q, cp, stash_path or None))
        all_results.sort(key=lambda r: r["score"], reverse=True)
        return JSONResponse(content=all_results[:50])
    except FileNotFoundError as e:
        return JSONResponse(content={"error": str(e)}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


_sets_cache: list[dict[str, Any]] | None = None


def get_sets() -> list[dict[str, Any]]:
    global _sets_cache
    if _sets_cache is not None:
        return _sets_cache

    gd = get_game_data()

    code_to_name: dict[str, str] = {}
    for table in ("weapons", "armor", "misc"):
        rows = gd.conn.execute(f'SELECT code, name FROM "{table}" WHERE name != \'\'').fetchall()
        for row in rows:
            code_to_name[row["code"]] = row["name"]

    rows = gd.conn.execute('SELECT "index", item, "set" FROM setitems WHERE "set" != \'\' ORDER BY "set", "index"').fetchall()

    sets: dict[str, dict[str, Any]] = {}
    for row in rows:
        set_name: str = row["set"]
        piece_name: str = row["index"]
        code: str = row["item"]
        base_name = code_to_name.get(code, code)

        if set_name not in sets:
            sets[set_name] = {
                "name": set_name,
                "items": [],
            }
        sets[set_name]["items"].append({
            "name": piece_name,
            "code": code,
            "base": base_name,
        })

    _sets_cache = list(sets.values())
    return _sets_cache


@app.get("/api/sets")
async def list_sets() -> JSONResponse:
    return JSONResponse(content=get_sets())


_SYSTEM_PROMPT = (
    (Path(__file__).parent / "data" / "system_prompt.md")
    .read_text(encoding="utf-8")
)


@app.websocket("/api/chat")
async def chat_websocket(ws: WebSocket) -> None:
    from google import genai
    from google.genai import types

    await ws.accept()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        await ws.send_text(json.dumps({"text": "GEMINI_API_KEY not configured.", "done": True}))
        await ws.close()
        return

    model_name = (os.getenv("GEMINI_MODEL") or "gemini-3.5-flash").strip() or "gemini-3.5-flash"
    client = genai.Client(api_key=api_key)
    store = get_chat_store()

    context_json = "{}"
    chat = None
    chat_id: str | None = None

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")
            payload = data.get("payload", "")

            if msg_type == "context":
                context_json = payload
                context_data: dict[str, Any] = {}
                try:
                    context_data = json.loads(payload)
                except (json.JSONDecodeError, TypeError):
                    pass
                chat_id = context_data.get("chat_id")

                system_instruction = _SYSTEM_PROMPT.replace("{CONTEXT_JSON}", context_json)

                if chat_id:
                    history = store.get_messages(chat_id)
                    if history:
                        lines = ["\n\n--- Previous conversation ---\n"]
                        for msg in history[-40:]:
                            role = "User" if msg["role"] == "user" else "Assistant"
                            lines.append(f"{role}: {msg['content']}\n")
                        lines.append("--- End of previous conversation ---\n")
                        system_instruction += "".join(lines)

                chat = client.chats.create(
                    model=model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    ),
                )

                await ws.send_text(json.dumps({"text": "Ready. Ask me about your character!", "done": True}))

            elif msg_type == "message":
                if chat is None:
                    system_instruction = _SYSTEM_PROMPT.replace("{CONTEXT_JSON}", context_json)
                    chat = client.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                        ),
                    )

                if chat_id:
                    if not store.chat_exists(chat_id):
                        store.create_chat(chat_id=chat_id)
                    store.add_message(chat_id, "user", payload)

                response_text = ""
                response = chat.send_message_stream(payload)
                for chunk in response:
                    if chunk.text:
                        response_text += chunk.text
                        await ws.send_text(json.dumps({"text": chunk.text, "done": False}))
                await ws.send_text(json.dumps({"text": "", "done": True}))

                if chat_id and response_text:
                    store.add_message(chat_id, "assistant", response_text)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await ws.send_text(json.dumps({"text": f"Error: {exc}", "done": True}))
        except Exception:
            pass


@app.get("/api/chats")
async def list_chats() -> JSONResponse:
    return JSONResponse(content=get_chat_store().list_chats())


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str) -> JSONResponse:
    store = get_chat_store()
    if store.chat_exists(chat_id):
        store.delete_chat(chat_id)
    return JSONResponse(content={"ok": True})


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


def _format_runeword(row: dict[str, Any], gd: Any) -> dict[str, Any]:
    codes = [row.get(f"t1code{i}", "") for i in range(1, 8)]
    params = [row.get(f"t1param{i}", "") or "" for i in range(1, 8)]
    mins = [row.get(f"t1min{i}", "") or "" for i in range(1, 8)]
    maxs = [row.get(f"t1max{i}", "") or "" for i in range(1, 8)]

    properties: list[str] = []
    for i in range(7):
        code = codes[i]
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
            params[i],
            mins[i],
            maxs[i],
        )
        if display:
            properties.append(display)

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
    codes = [row.get(f"prop{i}", "") for i in range(1, 13)]
    params = [row.get(f"par{i}", "") or "" for i in range(1, 13)]
    mins = [row.get(f"min{i}", "") or "" for i in range(1, 13)]
    maxs = [row.get(f"max{i}", "") or "" for i in range(1, 13)]

    properties: list[str] = []
    for i in range(12):
        code = codes[i]
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
            params[i],
            mins[i],
            maxs[i],
        )
        if display:
            properties.append(display)

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
    codes = [row.get(f"prop{i}", "") for i in range(1, 10)]
    params = [row.get(f"par{i}", "") or "" for i in range(1, 10)]
    mins = [row.get(f"min{i}", "") or "" for i in range(1, 10)]
    maxs = [row.get(f"max{i}", "") or "" for i in range(1, 10)]

    properties: list[str] = []
    for i in range(9):
        code = codes[i]
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
            params[i],
            mins[i],
            maxs[i],
        )
        if display:
            properties.append(display)

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


def _format_base_item(row: dict[str, Any], table: str, gd: Any) -> dict[str, Any]:
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
        cols = f'{common_cols}, mindam, maxdam, speed'
    elif table == "armor":
        cols = f'{common_cols}, minac, maxac, speed'
    elif table == "misc":
        cols = f'{common_cols}, speed'
    else:
        return None
    row = gd.conn.execute(
        f'SELECT {cols} FROM "{table}" WHERE LOWER("name") = ? AND "spawnable" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return dict(row)
    return None


@app.get("/api/items/lookup")
async def lookup_item(name: str = "", type: str = "") -> JSONResponse:
    if not name or len(name.strip()) < 2:
        return JSONResponse(content=None)

    gd = get_game_data()
    q = name.strip().lower()
    item_type = type.strip().lower()

    if item_type in ("rw", "runeword"):
        row = gd.conn.execute(
            'SELECT * FROM runes WHERE LOWER("x_rune_name") = ? AND "complete" = ?',
            (q, "1"),
        ).fetchone()
        if row:
            return JSONResponse(content=_format_runeword(dict(row), gd))
        return JSONResponse(content=None)

    if item_type in ("unq", "unique"):
        row = gd.conn.execute(
            'SELECT * FROM uniqueitems WHERE LOWER("index") = ? AND "spawnable" = ?',
            (q, "1"),
        ).fetchone()
        if row:
            return JSONResponse(content=_format_unique(dict(row), gd))
        return JSONResponse(content=None)

    if item_type in ("set",):
        row = gd.conn.execute(
            'SELECT * FROM setitems WHERE LOWER("index") = ? AND "spawnable" = ?',
            (q, "1"),
        ).fetchone()
        if row:
            return JSONResponse(content=_format_setitem(dict(row), gd))
        return JSONResponse(content=None)

    if item_type in ("base",):
        for table in ("weapons", "armor", "misc"):
            row = _query_base_item(gd, table, q)
            if row:
                return JSONResponse(content=_format_base_item(row, table, gd))
        return JSONResponse(content=None)

    # Auto-detect: prioritized search
    row = gd.conn.execute(
        'SELECT * FROM runes WHERE LOWER("x_rune_name") = ? AND "complete" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return JSONResponse(content=_format_runeword(dict(row), gd))

    row = gd.conn.execute(
        'SELECT * FROM uniqueitems WHERE LOWER("index") = ? AND "spawnable" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return JSONResponse(content=_format_unique(dict(row), gd))

    row = gd.conn.execute(
        'SELECT * FROM setitems WHERE LOWER("index") = ? AND "spawnable" = ?',
        (q, "1"),
    ).fetchone()
    if row:
        return JSONResponse(content=_format_setitem(dict(row), gd))

    for table in ("weapons", "armor", "misc"):
        row = _query_base_item(gd, table, q)
        if row:
            return JSONResponse(content=_format_base_item(row, table, gd))

    return JSONResponse(content=None)


_frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
