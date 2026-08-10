"""Dice rolling for solo play: standard notation with advantage/disadvantage.

A roll parses D&D-style notation (e.g. "2d6+1", "1d20", "3d8-2") into a die
pool and a modifier. Advantage and disadvantage roll a second die for every
die in the pool and keep the better or worse individual die, matching how a
single d20 keeps the higher or lower roll. A Roll knows how to describe
itself for the journal so the same text can be shown and logged.

The engine is a pure function of the provided rolls; callers pass their own
rng for determinism or omit it to use the global random module.
"""

import random
import re
from dataclasses import dataclass

ADVANTAGE = "advantage"
DISADVANTAGE = "disadvantage"
MODES = (None, ADVANTAGE, DISADVANTAGE)

# (combo label, mode) so the journal bar and the engine share one mapping.
MODE_LABELS = (
    ("Normal", None),
    ("Advantage", ADVANTAGE),
    ("Disadvantage", DISADVANTAGE),
)

NOTATION_RE = re.compile(r"^\s*(\d+)d(\d+)\s*([+-]\s*\d+)?\s*$")


def parse_notation(notation):
    """Split dice notation into (die count, sides, modifier).

    Accepts "2d6+1", "1d20", "3d8 - 2", and plain "2d6"; rejects anything
    that is not an integer dice pool with an optional sign-modifier.
    """
    match = NOTATION_RE.match(notation)
    if not match:
        raise ValueError(f"Invalid dice notation: {notation!r}")
    count, sides = int(match.group(1)), int(match.group(2))
    modifier = int(match.group(3).replace(" ", "")) if match.group(3) else 0
    return count, sides, modifier


@dataclass(frozen=True)
class Roll:
    """One finished roll: its notation, individual dice, and total."""

    notation: str
    dice: tuple
    modifier: int
    total: int
    mode: str | None = None

    def description(self):
        """Human-readable journal line, e.g. "2d6+1 -> 9 (3 + 5 + 1)"."""
        inner = " + ".join(str(die) for die in self.dice)
        if self.modifier:
            sign = " - " if self.modifier < 0 else " + "
            inner += f"{sign}{abs(self.modifier)}"
        prefix = f"{self.mode} " if self.mode else ""
        return f"{self.notation} -> {self.total} ({prefix}{inner})"


def _die(sides, mode, rng):
    """One die: a single roll, or the better/worse of two under a mode."""
    first = rng.randint(1, sides)
    if mode is None:
        return first
    second = rng.randint(1, sides)
    if mode == ADVANTAGE:
        return max(first, second)
    return min(first, second)


def roll(notation, mode=None, rng=None):
    """Roll `notation` under an optional mode; returns a Roll.

    `mode` is None, ADVANTAGE, or DISADVANTAGE. `rng` defaults to the global
    random module; pass a scripted rng to make the outcome deterministic.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown roll mode: {mode!r}")
    count, sides, modifier = parse_notation(notation)
    rng = rng or random
    dice = tuple(_die(sides, mode, rng) for _ in range(count))
    return Roll(notation.strip(), dice, modifier, sum(dice) + modifier, mode)
