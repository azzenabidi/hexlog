"""Tests for the Shadowdark SoloDark oracle engine (no GUI required)."""

import pytest

from hexlog.oracle import (
    ODDS_LABELS,
    OracleAnswer,
    answer_for,
    odds_kind,
    prompt,
    resolve,
    roll_check,
)
from hexlog.ui.oracle_dialog import format_answer


class FakeRng:
    """A scripted rng: randint() returns the next queued value."""

    def __init__(self, values):
        self.values = list(values)

    def randint(self, low, high):
        return self.values.pop(0)


def test_odds_kind_maps_the_three_levels():
    assert odds_kind("Unlikely or Impossible") == "disadvantage"
    assert odds_kind("Even Chance") == "standard"
    assert odds_kind("Likely or Certain") == "advantage"


def test_odds_kind_rejects_unknown_labels():
    with pytest.raises(ValueError):
        odds_kind("Maybe?")


def test_roll_check_standard_uses_a_single_roll():
    assert roll_check("standard", FakeRng([7])) == 7


def test_roll_check_disadvantage_keeps_the_lowest():
    assert roll_check("disadvantage", FakeRng([18, 5])) == 5


def test_roll_check_advantage_keeps_the_highest():
    assert roll_check("advantage", FakeRng([8, 14])) == 14


def test_answer_for_verdicts_by_band():
    assert answer_for(1) == "No, and"
    assert answer_for(6) == "No"
    assert answer_for(9) == "No, but"
    assert answer_for(10) == "Twist"
    assert answer_for(12) == "Yes"
    assert answer_for(15) == "Yes, but"
    assert answer_for(20) == "Yes, and"


def test_answer_for_odd_rolls_get_a_but():
    assert answer_for(3) == "No, but"
    assert answer_for(5) == "No, but"
    assert answer_for(11) == "Yes, but"
    assert answer_for(19) == "Yes, but"


def test_answer_for_even_rolls_have_no_turnabout():
    assert answer_for(2) == "No"
    assert answer_for(8) == "No"
    assert answer_for(14) == "Yes"
    assert answer_for(18) == "Yes"


def test_prompt_picks_verb_and_noun_rows():
    assert prompt(1) == "Stop Freedom"
    assert prompt(24) == "Block Freedom"
    assert prompt(42) == "Agree Balance"
    assert prompt(99) == "Rest Shelter"
    assert prompt(100) == "Release Power"


def test_prompt_rejects_out_of_range_rolls():
    with pytest.raises(ValueError):
        prompt(0)
    with pytest.raises(ValueError):
        prompt(101)


def test_resolve_plain_answer_has_no_twist():
    answer = resolve("Is the gate guarded?", "Even Chance", 14)
    assert answer == OracleAnswer("Is the gate guarded?", "Even Chance", 14, "Yes")
    assert answer.twist is None


def test_resolve_twist_fires_only_on_a_roll_of_ten():
    answer = resolve("Is the gate guarded?", "Even Chance", 10, twist_roll=42)
    assert answer.answer == "Twist"
    assert answer.twist == "Agree Balance"


def test_resolve_ignores_twist_roll_outside_a_ten():
    answer = resolve("Is the gate guarded?", "Even Chance", 12, twist_roll=42)
    assert answer.twist is None


def test_resolve_twist_needs_a_twist_roll():
    answer = resolve("Is the gate guarded?", "Even Chance", 10)
    assert answer.twist is None


def test_format_answer_includes_every_part():
    answer = OracleAnswer("Is the gate guarded?", "Even Chance", 10, "Twist",
                          twist="Agree Balance")
    assert format_answer(answer) == (
        "Q: Is the gate guarded?\n"
        "Odds Even Chance - rolled 10: Twist\n"
        "Twist: Agree Balance"
    )


def test_format_answer_omits_missing_twist():
    answer = OracleAnswer("Is the gate guarded?", "Even Chance", 14, "Yes")
    assert format_answer(answer) == (
        "Q: Is the gate guarded?\n"
        "Odds Even Chance - rolled 14: Yes"
    )


def test_odds_labels_order_matches_the_booklet():
    assert ODDS_LABELS == (
        "Unlikely or Impossible",
        "Even Chance",
        "Likely or Certain",
    )
