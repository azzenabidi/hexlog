"""Tests for the generic entity tab's pure helpers (no GUI required)."""

from PySide6.QtGui import QColor

from hexlog import constants as C
from hexlog.ui.entities import draft_color


def test_draft_color_prefers_unused_palette_color():
    assert draft_color([]).name() == C.COLOR_PALETTE[0]
    assert draft_color([{"color": C.COLOR_PALETTE[0]}]).name() == C.COLOR_PALETTE[1]


def test_draft_color_returns_a_qcolor():
    assert isinstance(draft_color([]), QColor)
