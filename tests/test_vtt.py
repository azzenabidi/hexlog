"""Tests for pure VTT helpers (no GUI required)."""

from hexlog.ui.vtt import kind_label, short_label


def test_short_label():
    assert short_label("") == "?"
    assert short_label("Al") == "Al"
    assert short_label("Goblin King") == "Goblin"
    assert short_label("BilboBaggins") == "B"


def test_kind_label():
    assert kind_label("npc") == "NPC"
    assert kind_label("location") == "Location"
    assert kind_label("character") == "Character"
