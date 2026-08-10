"""Tests for the pure dice engine (no GUI required)."""

import pytest

from hexlog.dice import (
    ADVANTAGE,
    DISADVANTAGE,
    MODE_LABELS,
    Roll,
    parse_notation,
    roll,
)


class FakeRng:
    """A scripted rng: randint() returns the next queued value."""

    def __init__(self, values):
        self.values = list(values)

    def randint(self, low, high):
        return self.values.pop(0)


def test_parse_notation_handles_modifier_and_whitespace():
    assert parse_notation("2d6+1") == (2, 6, 1)
    assert parse_notation("1d20") == (1, 20, 0)
    assert parse_notation(" 3d8 - 2 ") == (3, 8, -2)
    assert parse_notation("2d6") == (2, 6, 0)


def test_parse_notation_rejects_garbage():
    for bad in ("d6", "2d", "2x6", "abc", "2d6+", "-2d6", "2d6+1d4"):
        with pytest.raises(ValueError):
            parse_notation(bad)


def test_roll_sums_dice_and_modifier():
    assert roll("2d6+1", rng=FakeRng([3, 5])) == Roll("2d6+1", (3, 5), 1, 9)


def test_roll_supports_plain_pools():
    result = roll("3d8", rng=FakeRng([4, 6, 5]))
    assert result.total == 15
    assert result.modifier == 0


def test_roll_advantage_keeps_the_highest_die():
    assert roll("1d20", mode=ADVANTAGE, rng=FakeRng([12, 18])).total == 18


def test_roll_disadvantage_keeps_the_lowest_die():
    assert roll("1d20", mode=DISADVANTAGE, rng=FakeRng([18, 12])).total == 12


def test_roll_advantage_applies_per_die():
    result = roll("2d6", mode=ADVANTAGE, rng=FakeRng([1, 6, 3, 5]))
    assert result.dice == (6, 5)
    assert result.total == 11


def test_roll_rejects_unknown_modes():
    with pytest.raises(ValueError):
        roll("1d20", mode="bogus", rng=FakeRng([5]))


def test_roll_rejects_bad_notation():
    with pytest.raises(ValueError):
        roll("xyz", rng=FakeRng([5]))


def test_roll_uses_global_random_by_default():
    assert 1 <= roll("1d4").total <= 4


def test_roll_description_with_modifier():
    result = Roll("2d6+1", (3, 5), 1, 9)
    assert result.description() == "2d6+1 -> 9 (3 + 5 + 1)"


def test_roll_description_with_negative_modifier():
    result = Roll("3d8-2", (4, 6, 5), -2, 13)
    assert result.description() == "3d8-2 -> 13 (4 + 6 + 5 - 2)"


def test_roll_description_omits_zero_modifier():
    result = Roll("1d20", (18,), 0, 18)
    assert result.description() == "1d20 -> 18 (18)"


def test_roll_description_labels_advantage():
    result = Roll("1d20", (18,), 0, 18, mode=ADVANTAGE)
    assert result.description() == "1d20 -> 18 (advantage 18)"


def test_mode_labels_cover_normal_advantage_disadvantage():
    assert [label for label, _ in MODE_LABELS] == ["Normal", "Advantage", "Disadvantage"]
    assert [mode for _, mode in MODE_LABELS] == [None, ADVANTAGE, DISADVANTAGE]
