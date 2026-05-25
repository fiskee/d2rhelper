from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

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
