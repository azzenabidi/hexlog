"""Tests for the Mythic-style oracle engine (no GUI required)."""

import pytest

from hexlog.oracle import (
    ODDS_LABELS,
    OracleAnswer,
    answer_for,
    event_focus,
    event_meaning,
    odds_threshold,
    random_event,
    resolve,
)
from hexlog.ui.oracle_dialog import format_answer


def test_odds_threshold_follows_the_scale():
    assert odds_threshold("Impossible") == 0
    assert odds_threshold("50/50") == 50
    assert odds_threshold("Has To Be") == 99


def test_odds_threshold_rejects_unknown_labels():
    with pytest.raises(ValueError):
        odds_threshold("Maybe?")


def test_answer_for_uses_odds_threshold():
    assert answer_for(30, "50/50") == "Yes"
    assert answer_for(50, "50/50") == "Yes"
    assert answer_for(51, "50/50") == "No"


def test_answer_for_marks_exceptional_rolls():
    assert answer_for(1, "50/50") == "Exceptional Yes"
    assert answer_for(5, "50/50") == "Exceptional Yes"
    assert answer_for(96, "50/50") == "Exceptional No"
    assert answer_for(100, "50/50") == "Exceptional No"


def test_answer_for_extremes_of_the_scale():
    assert answer_for(10, "Impossible") == "No"
    assert answer_for(80, "Has To Be") == "Yes"
    assert answer_for(100, "Has To Be") == "Exceptional No"


def test_event_focus_covers_all_ranges():
    assert event_focus(1) == "PC negative"
    assert event_focus(8) == "PC negative"
    assert event_focus(29) == "NPC action"
    assert event_focus(53) == "Ambiguous"
    assert event_focus(93) == "PC altered"
    assert event_focus(100) == "PC altered"


def test_event_meaning_splits_into_descriptor_and_subject():
    assert event_meaning(42) == "Frozen, an old ally"


def test_random_event_composes_focus_and_meaning():
    assert random_event(35, 42) == "NPC action — Frozen, an old ally"


def test_resolve_plain_answer_has_no_event():
    answer = resolve("Is the gate guarded?", "50/50", 30)
    assert answer == OracleAnswer("Is the gate guarded?", "50/50", 30, "Yes")
    assert answer.event is None


def test_resolve_fires_event_within_chaos_factor():
    answer = resolve("Is the gate guarded?", "50/50", 30,
                     chaos_roll=4, chaos_factor=5, focus_roll=35, meaning_roll=42)
    assert answer.answer == "Yes"
    assert answer.event == "NPC action — Frozen, an old ally"


def test_resolve_skips_event_outside_chaos_factor():
    answer = resolve("Is the gate guarded?", "50/50", 30,
                     chaos_roll=6, chaos_factor=5, focus_roll=35, meaning_roll=42)
    assert answer.event is None


def test_resolve_ignores_chaos_factor_without_a_chaos_roll():
    answer = resolve("Is the gate guarded?", "50/50", 30,
                     chaos_factor=5, focus_roll=35, meaning_roll=42)
    assert answer.event is None


def test_format_answer_includes_every_part():
    answer = OracleAnswer("Is the gate guarded?", "50/50", 30, "Yes",
                          event="NPC action — Frozen, an old ally")
    assert format_answer(answer) == (
        "Q: Is the gate guarded?\n"
        "Odds 50/50 - rolled 30: Yes\n"
        "Random event: NPC action — Frozen, an old ally"
    )


def test_format_answer_omits_missing_event():
    answer = OracleAnswer("Is the gate guarded?", "50/50", 30, "Yes")
    assert format_answer(answer) == (
        "Q: Is the gate guarded?\n"
        "Odds 50/50 - rolled 30: Yes"
    )


def test_odds_labels_order_matches_impossible_to_certain():
    assert ODDS_LABELS[0] == "Impossible"
    assert ODDS_LABELS[-1] == "Has To Be"
