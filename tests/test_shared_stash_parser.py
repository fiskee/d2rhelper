from pathlib import Path

from d2rhelper.shared_stash_parser import SharedStashParser


def test_parse_modern_stash() -> None:
    fixture = Path("tests/resources/ModernSharedStashSoftCoreV2.d2i")
    tabs = SharedStashParser().parse_file(fixture)

    assert len(tabs) == 6
    assert all(tab.version == 105 for tab in tabs)
    assert tabs[0].length_in_bytes > 0


def test_stash_tab_item_counts() -> None:
    fixture = Path("tests/resources/ModernSharedStashSoftCoreV2.d2i")
    tabs = SharedStashParser().parse_file(fixture)

    assert tabs[0].item_count == 27
    assert tabs[0].gold == 2195
    assert tabs[1].item_count == 4
    assert tabs[1].gold == 0
    assert tabs[5].item_count == 55
    assert tabs[5].gold == 0


def test_materials_tab_has_stacks() -> None:
    fixture = Path("tests/resources/ModernSharedStashSoftCoreV2.d2i")
    tabs = SharedStashParser().parse_file(fixture)
    tab6 = tabs[5]
    assert len(tab6.items) == 55
    stacked = [it for it in tab6.items if it.stacks is not None]
    assert len(stacked) == 55
