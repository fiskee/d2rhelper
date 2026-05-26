from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TypedDict

from fastapi import WebSocket, WebSocketDisconnect

from d2rhelper.chat_store import get_chat_store
from d2rhelper.tools import TOOL_DEFINITIONS, CharacterContextStore, execute_tool_call

CHAT_MODE = os.getenv("D2RHELPER_CHAT_MODE", "tools")
CHAT_RUNTIME_EXCEPTIONS = (json.JSONDecodeError, TypeError, ValueError, RuntimeError, OSError)

_SYSTEM_PROMPT = (
    (Path(__file__).parent.parent / "data" / "system_prompt.md")
    .read_text(encoding="utf-8")
)

_TOOL_INSTRUCTIONS = """
## Available Tools

You have access to tools to query the player's character and stash data on demand. **Do NOT assume or guess what items the player has - always search first.**

- `get_character_overview()` - Quick snapshot: class, level, stats, skills, equipped items (each with id, name, quality, base, requirements, sockets, socketed contents, and top 5 properties), quests, waypoints, mercenary. **Call this at the start of every conversation.**
- `get_mercenary_overview()` - Mercenary name, type, skills, and gear (each item with id, name, quality, base, requirements, sockets, and top properties).
- `get_materials_summary()` - Compact inventory of ALL runes, gems, essences, and keys across personal + shared stashes. Returns counts: `{"runes": {"Sol": 3, "Tal": 1}, "gems": {"Perfect Topaz": 2}, ...}`. **Use this instead of search_stash when checking what runes/gems the player has.** Run this early when evaluating craftable runewords.
- `search_character_items(query)` - Search the player's equipped items, inventory, belt, and Horadric Cube. `query` can be a single keyword string OR an array of strings to batch multiple searches in one call (e.g. `["Spirit", "fire resist", "Sol rune"]`). Matches item names, runewords, bases, runes, gems, and property text. **Call before any gear recommendation.**
- `search_stash(query)` - Search all shared stash tabs (and other characters' stashes in "All characters" mode). Same single/multi-query behavior. **Call before suggesting runewords or anything requiring materials.** Batch related searches together - e.g. search for all runes needed for a runeword in one call.
- `get_item_details(item_id)` - Full stats for a specific item. Use the `id` from search results.

**Rules:**
- **Always call `get_character_overview()` first.**
- **Always call `search_character_items()` or `search_stash()` before making recommendations about gear, runewords, or item usage.** Never guess what the player has.
- Use simple keyword queries - search is case-insensitive and matches item names, codes, properties, and socketed contents.
- When recommending a runeword, search for the required runes AND a suitable base in one call each.
- Reference player-owned items with the `[Name](item:p:ID)` link format using the ID from search results.
"""

_TOOLS_SYSTEM_PROMPT = _SYSTEM_PROMPT
_ctx_start = _TOOLS_SYSTEM_PROMPT.find("=== YOUR CONTEXT ===")
_gm_start = _TOOLS_SYSTEM_PROMPT.find("## Game Mechanics")
if _ctx_start >= 0 and _gm_start > _ctx_start:
    _TOOLS_SYSTEM_PROMPT = (
        _TOOLS_SYSTEM_PROMPT[:_ctx_start]
        + _TOOL_INSTRUCTIONS
        + _TOOLS_SYSTEM_PROMPT[_gm_start:]
    )


class ChatContextPayload(TypedDict, total=False):
    chat_id: str
    chat_mode: str


def _parse_chat_context_payload(payload: str) -> ChatContextPayload:
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        "chat_id": str(data.get("chat_id", "")),
        "chat_mode": str(data.get("chat_mode", CHAT_MODE) or CHAT_MODE),
    }


def _history_suffix(chat_store: Any, chat_id: str | None) -> str:
    if not chat_id:
        return ""
    history = chat_store.get_messages(chat_id)
    if not history:
        return ""

    lines = ["\n\n--- Previous conversation ---\n"]
    for msg in history[-40:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}\n")
    lines.append("--- End of previous conversation ---\n")
    return "".join(lines)


async def _send_ws_error(ws: WebSocket, text: str) -> None:
    try:
        await ws.send_text(json.dumps({"text": text, "done": True}))
    except (RuntimeError, OSError, WebSocketDisconnect):
        return


async def _handle_message_tools(
    ws: WebSocket,
    client: Any,
    model_name: str,
    system_instruction: str,
    payload: str,
    contents: list[Any],
    context_store: CharacterContextStore,
    chat_store: Any,
    chat_id: str | None,
) -> None:
    import asyncio as _asyncio

    from google.genai import types

    contents.append(types.Content(parts=[types.Part(text=payload)], role="user"))

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[types.Tool(function_declarations=TOOL_DEFINITIONS)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    while True:
        await ws.send_text(json.dumps({"thinking": True, "done": False}))
        await _asyncio.sleep(0.02)

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )

        await ws.send_text(json.dumps({"thinking": False, "done": False}))
        await _asyncio.sleep(0.02)

        fc_list: list[Any] = list(getattr(response, "function_calls", None) or [])
        if not fc_list and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "function_calls"):
                fc_list = list(candidate.function_calls or [])

        if fc_list:
            candidate = response.candidates[0]
            if candidate.content:
                contents.append(candidate.content)

            fn_response_parts: list[Any] = []
            for fc in fc_list:
                await ws.send_text(json.dumps({
                    "tool_call": {"name": fc.name, "args": dict(fc.args) if fc.args else {}},
                    "done": False,
                }))
                await _asyncio.sleep(0.02)

                tool_ok = True
                tool_error = None
                try:
                    result = execute_tool_call(fc.name, dict(fc.args) if fc.args else {}, context_store)
                except (ValueError, TypeError, RuntimeError, OSError) as exc:
                    tool_ok = False
                    tool_error = str(exc)
                    result = {"error": str(exc)}

                await ws.send_text(json.dumps({
                    "tool_result": {
                        "name": fc.name,
                        "result": result,
                        "ok": tool_ok,
                        "error": tool_error,
                    },
                    "done": False,
                }))
                await _asyncio.sleep(0.02)

                fn_response_parts.append(types.Part(
                    function_response=types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response={"result": result},
                    )
                ))

            contents.append(types.Content(parts=fn_response_parts, role="tool"))
            continue

        full_text = getattr(response, "text", None) or ""
        if response.candidates and response.candidates[0].content:
            contents.append(response.candidates[0].content)

        await ws.send_text(json.dumps({"text": full_text, "done": False}))
        await _asyncio.sleep(0.02)
        await ws.send_text(json.dumps({"text": "", "done": True}))

        if chat_id and full_text:
            chat_store.add_message(chat_id, "assistant", full_text)
        break


async def handle_chat_websocket(ws: WebSocket) -> None:
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
    chat_store = get_chat_store()

    context_store: CharacterContextStore | None = None
    contents: list[types.Content] = []
    system_instruction: str = ""
    context_json = "{}"
    chat = None
    chat_id: str | None = None
    chat_mode: str = CHAT_MODE

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")
            payload = data.get("payload", "")

            if msg_type == "context":
                context_json = payload
                context_data = _parse_chat_context_payload(payload)
                chat_id = context_data.get("chat_id")
                chat_mode = context_data.get("chat_mode", CHAT_MODE)

                if chat_mode == "tools":
                    context_store = CharacterContextStore.from_json(payload)
                    system_instruction = _TOOLS_SYSTEM_PROMPT
                else:
                    system_instruction = _SYSTEM_PROMPT.replace("{CONTEXT_JSON}", context_json)

                system_instruction += _history_suffix(chat_store, chat_id)

                if chat_mode == "tools":
                    contents = []
                    chat = None
                else:
                    chat = client.chats.create(
                        model=model_name,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                        ),
                    )

                await ws.send_text(json.dumps({"done": True}))

            elif msg_type == "message":
                if chat_id:
                    if not chat_store.chat_exists(chat_id):
                        chat_store.create_chat(chat_id=chat_id)
                    chat_store.add_message(chat_id, "user", payload)

                if chat_mode == "tools" and context_store is not None:
                    await _handle_message_tools(ws, client, model_name, system_instruction, payload, contents, context_store, chat_store, chat_id)
                else:
                    if chat is None:
                        system_instruction = _SYSTEM_PROMPT.replace("{CONTEXT_JSON}", context_json)
                        chat = client.chats.create(
                            model=model_name,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                            ),
                        )

                    response_text = ""
                    response = chat.send_message_stream(payload)
                    for chunk in response:
                        if chunk.text:
                            response_text += chunk.text
                            await ws.send_text(json.dumps({"text": chunk.text, "done": False}))
                    await ws.send_text(json.dumps({"text": "", "done": True}))

                    if chat_id and response_text:
                        chat_store.add_message(chat_id, "assistant", response_text)

    except WebSocketDisconnect:
        return
    except CHAT_RUNTIME_EXCEPTIONS as exc:
        await _send_ws_error(ws, f"Error: {exc}")


__all__ = ["handle_chat_websocket"]
