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
    if cache_key in _parse_cache:
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

    context_json = "{}"
    chat = None

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")
            payload = data.get("payload", "")

            if msg_type == "context":
                context_json = payload
                system_instruction = _SYSTEM_PROMPT.replace("{CONTEXT_JSON}", context_json)
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

                response = chat.send_message_stream(payload)
                for chunk in response:
                    if chunk.text:
                        await ws.send_text(json.dumps({"text": chunk.text, "done": False}))
                await ws.send_text(json.dumps({"text": "", "done": True}))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await ws.send_text(json.dumps({"text": f"Error: {exc}", "done": True}))
        except Exception:
            pass


_frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
