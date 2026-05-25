from __future__ import annotations

from pathlib import Path

from d2rhelper import casc


def test_windows_saved_games_path_is_discovered_first(tmp_path: Path, monkeypatch) -> None:
    userprofile = tmp_path / "User"
    saved_games = userprofile / "Saved Games" / "Diablo II Resurrected"
    saved_games.mkdir(parents=True)
    expected = saved_games / "Hero.d2s"
    expected.write_bytes(b"x")

    other_root = tmp_path / "OtherRoot"
    other_root.mkdir()
    other = other_root / "Other.d2s"
    other.write_bytes(b"y")

    monkeypatch.setattr(casc.sys, "platform", "win32")
    monkeypatch.setenv("USERPROFILE", str(userprofile))
    monkeypatch.delenv("HOMEDRIVE", raising=False)
    monkeypatch.delenv("HOMEPATH", raising=False)
    monkeypatch.setattr(casc, "find_d2r_path", lambda: None)
    monkeypatch.setattr(casc, "_wine_prefix_search_roots", lambda: [other_root])

    files = casc.find_d2_save_files("d2s")

    assert files
    assert files[0] == expected
    assert other in files


def test_saved_games_near_d2r_is_not_steamuser_specific(tmp_path: Path) -> None:
    d2r_path = tmp_path / "prefix" / "drive_c" / "Program Files (x86)" / "Diablo II Resurrected"
    d2r_path.mkdir(parents=True)
    custom_user_saved = (
        tmp_path
        / "prefix"
        / "users"
        / "alice"
        / "Saved Games"
        / "Diablo II Resurrected"
    )
    custom_user_saved.mkdir(parents=True)

    paths = casc._saved_games_near_d2r(d2r_path)

    assert custom_user_saved in paths
