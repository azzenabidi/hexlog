"""Tests for pure VTT helpers (no GUI required)."""

from hexlog import constants as C
from hexlog.ui.vtt import (
    kind_label,
    load_pixmap_cached,
    resize_diameter,
    short_label,
)


class FakePixmap:
    def __init__(self, valid=True):
        self.valid = valid

    def isNull(self):
        return not self.valid


def test_short_label():
    assert short_label("") == "?"
    assert short_label("Al") == "Al"
    assert short_label("Goblin King") == "Goblin"
    assert short_label("BilboBaggins") == "B"


def test_kind_label():
    assert kind_label("npc") == "NPC"
    assert kind_label("location") == "Location"
    assert kind_label("character") == "Character"


def test_resize_diameter_grows_with_drag():
    assert resize_diameter(0, 0, 30, 40) == 80


def test_resize_diameter_shrinks_toward_center():
    assert resize_diameter(0, 0, 15, 10) == 30


def test_resize_diameter_clamps_to_minimum():
    assert resize_diameter(0, 0, 2, 1) == C.TOKEN_MIN_DIAMETER


def test_resize_diameter_clamps_to_maximum():
    assert resize_diameter(0, 0, 500, 500) == C.TOKEN_MAX_DIAMETER


def test_resize_diameter_is_centered_and_symmetric():
    assert resize_diameter(10, 10, 50, 30) == resize_diameter(10, 10, 30, 50)
    assert resize_diameter(10, 10, 50, 30) == 80


def test_pixmap_cache_loads_each_path_once(monkeypatch):
    decoded = []
    monkeypatch.setattr("hexlog.ui.vtt._pixmap_cache", {})
    monkeypatch.setattr(
        "hexlog.ui.vtt.QPixmap", lambda path: decoded.append(path) or FakePixmap()
    )

    first = load_pixmap_cached("map.png")
    second = load_pixmap_cached("map.png")
    assert first is second
    assert decoded == ["map.png"]


def test_pixmap_cache_memoizes_separate_paths(monkeypatch):
    monkeypatch.setattr("hexlog.ui.vtt._pixmap_cache", {})
    monkeypatch.setattr(
        "hexlog.ui.vtt.QPixmap", lambda path: FakePixmap(path != "broken.png")
    )

    assert load_pixmap_cached("a.png") is not None
    assert load_pixmap_cached("broken.png") is None
    assert load_pixmap_cached("a.png") is not None


def test_pixmap_cache_returns_none_for_unreadable_file(monkeypatch):
    cache = {}
    monkeypatch.setattr("hexlog.ui.vtt._pixmap_cache", cache)
    monkeypatch.setattr("hexlog.ui.vtt.QPixmap", lambda path: FakePixmap(valid=False))

    assert load_pixmap_cached("missing.png") is None
    assert "missing.png" in cache
