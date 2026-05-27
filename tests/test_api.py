from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


FARMING_D2S = "tests/resources/Farming.d2s"
STASH_D2I = "tests/resources/ModernSharedStashSoftCoreV2.d2i"


@pytest.fixture(scope="module")
def client() -> "TestClient":
    from fastapi.testclient import TestClient

    from d2rhelper.api import app

    return TestClient(app)


def test_parse_character_success(client: "TestClient") -> None:
    resp = client.post("/api/parse", json={"character_path": FARMING_D2S})
    assert resp.status_code == 200
    data = resp.json()
    assert "character" in data
    assert data["character"]["name"] == "Farming"
    assert data["character"]["level"] == 63
    assert data["character"]["character_type"] == "Sorceress"
    assert len(data["character"]["items"]) == 42
    assert "stash_tabs" in data
    assert data["stash_tabs"] == []


def test_parse_character_with_stash(client: "TestClient") -> None:
    resp = client.post(
        "/api/parse",
        json={"character_path": FARMING_D2S, "stash_path": STASH_D2I},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["stash_tabs"]) == 6
    for tab in data["stash_tabs"]:
        assert "index" in tab
        assert "gold" in tab
        assert "items" in tab


def test_parse_character_not_found(client: "TestClient") -> None:
    resp = client.post("/api/parse", json={"character_path": "/nonexistent/file.d2s"})
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_parse_character_cache(client: "TestClient") -> None:
    a = client.post("/api/parse", json={"character_path": FARMING_D2S})
    b = client.post("/api/parse", json={"character_path": FARMING_D2S})
    assert a.json() == b.json()


def test_parse_auto_mocked(client: "TestClient", monkeypatch) -> None:
    detected_path = Path(FARMING_D2S).resolve()
    stash_path = Path(STASH_D2I).resolve()

    monkeypatch.setattr(
        "d2rhelper.api.find_local_character_file",
        lambda: detected_path,
    )
    monkeypatch.setattr(
        "d2rhelper.api.find_local_shared_stash_file",
        lambda: stash_path,
    )

    resp = client.post("/api/parse/auto")
    assert resp.status_code == 200
    data = resp.json()
    assert data["character_path"] == str(detected_path)
    assert data["stash_path"] == str(stash_path)
    assert data["character"]["name"] == "Farming"


def test_characters_list(client: "TestClient", monkeypatch, tmp_path: Path) -> None:
    char_a = tmp_path / "Save" / "HeroA.d2s"
    char_a.parent.mkdir()
    char_a.write_bytes(Path(FARMING_D2S).read_bytes())

    char_b = tmp_path / "Save" / "HeroB.d2s"
    char_b.write_bytes(Path(FARMING_D2S).read_bytes())

    monkeypatch.setattr(
        "d2rhelper.api.find_all_character_files",
        lambda: [],  # override import in api
    )
    monkeypatch.setattr(
        "d2rhelper.api.find_local_shared_stash_file",
        lambda: None,
    )

    from d2rhelper.models import CharacterInfo
    from d2rhelper.parser import CharacterParser

    def mock_find_all():
        paths = sorted([char_a, char_b], key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            CharacterInfo(**info)
            for p in paths
            if (info := CharacterParser.read_character_info(p)) is not None
        ]

    monkeypatch.setattr("d2rhelper.api.find_all_character_files", mock_find_all)

    resp = client.get("/api/characters")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["characters"]) == 2
    assert data["characters"][0]["name"] == "Farming"
    assert data["characters"][0]["level"] == 63
    assert data["characters"][1]["name"] == "Farming"
    assert data["stash_path"] is None


def test_characters_list_error(client: "TestClient", monkeypatch) -> None:
    monkeypatch.setattr(
        "d2rhelper.api.find_all_character_files",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    resp = client.get("/api/characters")
    assert resp.status_code == 500


def test_search_single_character(client: "TestClient") -> None:
    resp = client.get(
        "/api/search",
        params={"q": "blizzard", "character_path": FARMING_D2S},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)


def test_search_multi_character(client: "TestClient") -> None:
    resp = client.get(
        "/api/search",
        params={
            "q": "sword",
            "character_paths": json.dumps([FARMING_D2S, FARMING_D2S]),
            "stash_path": STASH_D2I,
        },
    )
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    for r in results:
        assert "item" in r
        assert "source" in r
        assert "score" in r
        assert r["score"] > 0


def test_search_stash_items(client: "TestClient") -> None:
    resp = client.get(
        "/api/search",
        params={"q": "rune", "character_path": FARMING_D2S, "stash_path": STASH_D2I},
    )
    assert resp.status_code == 200
    results = resp.json()
    rune_items = [r for r in results if r["source"].startswith("stash")]
    assert len(rune_items) > 0


def test_search_empty_query(client: "TestClient") -> None:
    resp = client.get("/api/search", params={"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_no_paths(client: "TestClient") -> None:
    resp = client.get("/api/search", params={"q": "shield"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_not_found(client: "TestClient") -> None:
    resp = client.get(
        "/api/search",
        params={"q": "xyzzy", "character_path": FARMING_D2S},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_autocomplete_short_query(client: "TestClient") -> None:
    resp = client.get("/api/autocomplete", params={"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_autocomplete_items(client: "TestClient") -> None:
    resp = client.get("/api/autocomplete", params={"q": "Hel"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_autocomplete_weapons(client: "TestClient") -> None:
    resp = client.get("/api/autocomplete", params={"q": "Crystal"})
    assert resp.status_code == 200
    data = resp.json()
    assert any("Crystal" in name for name in data)


def test_parse_cache_separation(client: "TestClient") -> None:
    a = client.post(
        "/api/parse",
        json={"character_path": FARMING_D2S, "stash_path": STASH_D2I},
    )
    b = client.post(
        "/api/parse",
        json={"character_path": FARMING_D2S},
    )
    assert a.json()["stash_tabs"] != b.json()["stash_tabs"]
    assert len(a.json()["stash_tabs"]) > len(b.json()["stash_tabs"])


def test_search_multi_character_results_sorted(client: "TestClient") -> None:
    resp = client.get(
        "/api/search",
        params={
            "q": "spirit",
            "character_paths": json.dumps([FARMING_D2S]),
        },
    )
    results = resp.json()
    if results:
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


def test_sets_endpoint(client: "TestClient") -> None:
    resp = client.get("/api/sets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "name" in data[0]
    assert "items" in data[0]


def test_lookup_item_short_name_returns_none(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "a"})
    assert resp.status_code == 200
    assert resp.json() is None


def test_lookup_item_runeword(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "Spirit", "type": "runeword"})
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["quality"] == "runeword"
    assert data["name"] == "Spirit"
    assert isinstance(data["runes"], list)
    assert len(data["runes"]) >= 4


def test_lookup_item_unique(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "The Oculus", "type": "unique"})
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["quality"] == "unique"
    assert data["name"] == "The Oculus"


def test_lookup_item_set(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "Tal Rasha's Adjudication", "type": "set"})
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["quality"] == "set"
    assert data["name"] == "Tal Rasha's Adjudication"


def test_lookup_item_base(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "Crystal Sword", "type": "base"})
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["quality"] == "base"
    assert data["name"] == "Crystal Sword"


def test_lookup_item_skill(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "Blizzard", "type": "skill"})
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["quality"] == "skill"
    assert data["name"] == "Blizzard"


def test_lookup_item_auto_detect(client: "TestClient") -> None:
    resp = client.get("/api/items/lookup", params={"name": "Spirit"})
    assert resp.status_code == 200
    data = resp.json()
    assert data is not None
    assert data["quality"] == "runeword"


def test_chats_list_and_delete(client: "TestClient", monkeypatch, tmp_path: Path) -> None:
    from d2rhelper.chat_store import ChatStore

    store = ChatStore(db_path=tmp_path / "chat-test.db")
    monkeypatch.setattr("d2rhelper.api.get_chat_store", lambda: store)

    chat_id = f"test-{uuid4()}"
    store.create_chat(chat_id=chat_id, title="Cleanup test")
    store.add_message(chat_id, "user", "hello")

    list_resp = client.get("/api/chats")
    assert list_resp.status_code == 200
    chats = list_resp.json()
    assert any(c["id"] == chat_id for c in chats)

    delete_resp = client.delete(f"/api/chats/{chat_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["ok"] is True

    list_resp_after = client.get("/api/chats")
    assert list_resp_after.status_code == 200
    chats_after = list_resp_after.json()
    assert all(c["id"] != chat_id for c in chats_after)


def test_chat_websocket_missing_api_key(client: "TestClient", monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with client.websocket_connect("/api/chat") as ws:
        payload = json.loads(ws.receive_text())
        assert payload["done"] is True
        assert "GEMINI_API_KEY not configured" in payload["text"]


def _install_fake_genai(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tools_mode: bool,
    tool_call_name: str = "get_character_overview",
    tool_call_args: dict | None = None,
) -> None:
    class FakePart:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeContent:
        def __init__(self, parts=None, role=None):
            self.parts = parts or []
            self.role = role

    class FakeTool:
        def __init__(self, function_declarations=None):
            self.function_declarations = function_declarations

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeAutomaticFunctionCallingConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeFunctionResponse:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeFunctionCall:
        def __init__(self, name: str, args: dict, call_id: str):
            self.name = name
            self.args = args
            self.id = call_id

    class FakeCandidate:
        def __init__(self, content=None, function_calls=None):
            self.content = content
            self.function_calls = function_calls or []

    class FakeResponse:
        def __init__(self, *, text: str = "", function_calls=None, content=None):
            self.text = text
            self.function_calls = function_calls or []
            self.candidates = [FakeCandidate(content=content, function_calls=function_calls or [])]

    class FakeModels:
        def __init__(self):
            self.calls = 0

        def generate_content(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                fn_call = FakeFunctionCall(tool_call_name, tool_call_args or {}, "fc-1")
                return FakeResponse(function_calls=[fn_call], content=FakeContent(parts=[], role="model"))
            return FakeResponse(text="Tool mode final response", content=FakeContent(parts=[], role="model"))

    class FakeChat:
        def send_message_stream(self, payload):
            class Chunk:
                def __init__(self, text: str):
                    self.text = text

            yield Chunk("Full context ")
            yield Chunk("final response")

    class FakeChats:
        def create(self, **kwargs):
            return FakeChat()

    class FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.models = FakeModels()
            self.chats = FakeChats()

    fake_types = types.SimpleNamespace(
        Part=FakePart,
        Content=FakeContent,
        Tool=FakeTool,
        GenerateContentConfig=FakeGenerateContentConfig,
        AutomaticFunctionCallingConfig=FakeAutomaticFunctionCallingConfig,
        FunctionResponse=FakeFunctionResponse,
    )
    fake_genai_module = types.SimpleNamespace(Client=FakeClient, types=fake_types)
    fake_google = types.SimpleNamespace(genai=fake_genai_module)

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai_module)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("D2RHELPER_CHAT_MODE", "tools" if tools_mode else "full_context")


def test_chat_websocket_tools_mode_flow(client: "TestClient", monkeypatch) -> None:
    _install_fake_genai(monkeypatch, tools_mode=True)

    context_payload = {
        "chat_id": f"ws-tools-{uuid4()}",
        "chat_mode": "tools",
        "character": None,
        "stash_tabs": [],
    }

    with client.websocket_connect("/api/chat") as ws:
        ws.send_text(json.dumps({"type": "context", "payload": json.dumps(context_payload)}))
        ack = json.loads(ws.receive_text())
        assert ack["done"] is True

        ws.send_text(json.dumps({"type": "message", "payload": "hello"}))

        saw_thinking_true = False
        saw_thinking_false = False
        saw_tool_call = False
        saw_tool_result = False
        final_text = ""

        while True:
            evt = json.loads(ws.receive_text())
            if evt.get("thinking") is True:
                saw_thinking_true = True
            if evt.get("thinking") is False:
                saw_thinking_false = True
            if "tool_call" in evt:
                saw_tool_call = True
                assert evt["tool_call"]["name"] == "get_character_overview"
            if "tool_result" in evt:
                saw_tool_result = True
                assert evt["tool_result"]["name"] == "get_character_overview"
                assert evt["tool_result"].get("ok") is True
            if "text" in evt:
                final_text += evt.get("text", "")
            if evt.get("done") is True:
                break

        assert saw_thinking_true
        assert saw_thinking_false
        assert saw_tool_call
        assert saw_tool_result
        assert "Tool mode final response" in final_text


def test_chat_websocket_full_context_flow(client: "TestClient", monkeypatch) -> None:
    _install_fake_genai(monkeypatch, tools_mode=False)

    context_payload = {
        "chat_id": f"ws-full-{uuid4()}",
        "chat_mode": "full_context",
        "character": None,
        "stash_tabs": [],
    }

    with client.websocket_connect("/api/chat") as ws:
        ws.send_text(json.dumps({"type": "context", "payload": json.dumps(context_payload)}))
        ack = json.loads(ws.receive_text())
        assert ack["done"] is True

        ws.send_text(json.dumps({"type": "message", "payload": "hello"}))
        text_acc = ""
        while True:
            evt = json.loads(ws.receive_text())
            if "text" in evt:
                text_acc += evt.get("text", "")
            if evt.get("done") is True:
                break

        assert "Full context final response" in text_acc


def test_chat_websocket_tools_mode_lookup_skill_tool(client: "TestClient", monkeypatch) -> None:
    _install_fake_genai(
        monkeypatch,
        tools_mode=True,
        tool_call_name="lookup_skill_data",
        tool_call_args={"skill_name": "Blizzard", "class_name": "sorceress"},
    )

    context_payload = {
        "chat_id": f"ws-lookup-{uuid4()}",
        "chat_mode": "tools",
        "character": None,
        "stash_tabs": [],
    }

    with client.websocket_connect("/api/chat") as ws:
        ws.send_text(json.dumps({"type": "context", "payload": json.dumps(context_payload)}))
        ack = json.loads(ws.receive_text())
        assert ack["done"] is True

        ws.send_text(json.dumps({"type": "message", "payload": "check blizzard data"}))

        saw_tool_call = False
        saw_tool_result = False

        while True:
            evt = json.loads(ws.receive_text())
            if "tool_call" in evt:
                saw_tool_call = True
                assert evt["tool_call"]["name"] == "lookup_skill_data"
            if "tool_result" in evt:
                saw_tool_result = True
                assert evt["tool_result"]["name"] == "lookup_skill_data"
                assert evt["tool_result"].get("ok") is True
                result = evt["tool_result"].get("result", {})
                assert result.get("ok") is True
                assert result.get("name") == "Blizzard"
            if evt.get("done") is True:
                break

        assert saw_tool_call
        assert saw_tool_result
