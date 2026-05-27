from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from d2rhelper.chat_store import get_chat_store
from d2rhelper.services import (
    autocomplete_matches,
    get_game_data,
    get_parse_service,
    get_search_service,
    get_sets_service,
    handle_chat_websocket,
    lookup_item_data,
    search_items,
)
from d2rhelper.services.game_lookup import list_class_skills, lookup_skill_data
from d2rhelper.services.skill_damage import estimate_skill_damage
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

API_RESPONSE_EXCEPTIONS = (
    OSError,
    ValueError,
    RuntimeError,
)


def _error_response(exc: Exception, status_code: int = 500) -> JSONResponse:
    return JSONResponse(content={"error": str(exc)}, status_code=status_code)


class ParseRequest(BaseModel):
    character_path: str
    stash_path: str | None = None


class SkillDamageRequest(BaseModel):
    class_name: str
    skill_name: str
    skill_level: int
    plus_skills: int = 0
    synergy_levels: dict[str, int] = {}
    enemy_resist: float = 0.0
    sunder: bool = False


@app.get("/api/autocomplete")
async def autocomplete(q: str = "") -> JSONResponse:
    if len(q) < 2:
        return JSONResponse(content=[])
    items = get_search_service().get_autocomplete_items(get_game_data())
    return JSONResponse(content=autocomplete_matches(items, q))


@app.get("/api/characters")
async def list_characters() -> JSONResponse:
    try:
        characters = find_all_character_files()
        stash_path = find_local_shared_stash_file()
        return JSONResponse(content={
            "characters": [c.model_dump(mode="json") for c in characters],
            "stash_path": str(stash_path) if stash_path else None,
        })
    except API_RESPONSE_EXCEPTIONS as exc:
        return _error_response(exc)


@app.post("/api/parse")
async def parse(req: ParseRequest) -> JSONResponse:
    try:
        result = get_parse_service().parse_files(req.character_path, req.stash_path)
        return JSONResponse(content=result)
    except FileNotFoundError as exc:
        return _error_response(exc, status_code=404)
    except API_RESPONSE_EXCEPTIONS as exc:
        return _error_response(exc)


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
        result = get_parse_service().parse_files(str(char_path), str(stash_path) if stash_path else None)
        result["character_path"] = str(char_path)
        if stash_path:
            result["stash_path"] = str(stash_path)
        return JSONResponse(content=result)
    except API_RESPONSE_EXCEPTIONS as exc:
        return _error_response(exc)


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
            all_results.extend(search_items(q, get_parse_service().parse_files(cp, stash_path or None)))
        all_results.sort(key=lambda r: r["score"], reverse=True)
        return JSONResponse(content=all_results[:50])
    except FileNotFoundError as exc:
        return _error_response(exc, status_code=404)
    except API_RESPONSE_EXCEPTIONS as exc:
        return _error_response(exc)


@app.get("/api/sets")
async def list_sets() -> JSONResponse:
    return JSONResponse(content=get_sets_service().get_sets(get_game_data()))


@app.websocket("/api/chat")
async def chat_websocket(ws: WebSocket) -> None:
    await handle_chat_websocket(ws)


@app.get("/api/chats")
async def list_chats() -> JSONResponse:
    return JSONResponse(content=get_chat_store().list_chats())


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str) -> JSONResponse:
    store = get_chat_store()
    if store.chat_exists(chat_id):
        store.delete_chat(chat_id)
    return JSONResponse(content={"ok": True})


@app.get("/api/items/lookup")
async def lookup_item(name: str = "", type: str = "") -> JSONResponse:
    if not name or len(name.strip()) < 2:
        return JSONResponse(content=None)

    gd = get_game_data()
    return JSONResponse(content=lookup_item_data(gd, name, type))


@app.get("/api/skills/lookup")
async def lookup_skill(name: str = "", class_name: str = "") -> JSONResponse:
    if not name or len(name.strip()) < 2:
        return JSONResponse(content=None)
    gd = get_game_data()
    return JSONResponse(content=lookup_skill_data(gd, name, class_name))


@app.get("/api/skills/class")
async def list_skills_for_class(class_name: str = "") -> JSONResponse:
    if not class_name:
        return JSONResponse(content={"error": "class_name is required"}, status_code=400)
    gd = get_game_data()
    return JSONResponse(content=list_class_skills(gd, class_name))


@app.post("/api/skills/damage")
async def calculate_skill_damage(req: SkillDamageRequest) -> JSONResponse:
    gd = get_game_data()
    result = estimate_skill_damage(
        gd,
        class_name=req.class_name,
        skill_name=req.skill_name,
        skill_level=req.skill_level,
        plus_skills=req.plus_skills,
        synergy_levels=req.synergy_levels,
        enemy_resist=req.enemy_resist,
        sunder=req.sunder,
    )
    return JSONResponse(content=result)


_frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
