"""Mythic-inspired oracle: answers yes/no fate questions and spins twists.

A Fate Question rolls a d100 against a threshold chosen from the odds;
rolls at or below the threshold answer Yes, and very high or very low
rolls are exceptional. When the chaos roll comes in at or below the chaos
factor, a random event fires with a focus and a two-word meaning.

Everything here is a pure function of the provided rolls, so the engine
is deterministic under test; the dialog owns the randomness.
"""

from dataclasses import dataclass

# (label, threshold): a d100 at or below the threshold answers Yes. Ordered
# from impossible to certain so a UI can present them in that direction.
ODDS = (
    ("Impossible", 0),
    ("No Way", 5),
    ("Very Unlikely", 15),
    ("Unlikely", 25),
    ("50/50", 50),
    ("Likely", 75),
    ("Very Likely", 85),
    ("Near Sure Thing", 95),
    ("Has To Be", 99),
)

ODDS_LABELS = tuple(label for label, _ in ODDS)

# A roll at or below this is an exceptional yes, at or above this an
# exceptional no (Mythic's 1-5 / 96-100 bands).
EXCEPTIONAL_YES = 5
EXCEPTIONAL_NO = 96

# d100 ranges mapping to the focus of a random event.
EVENT_FOCUS = (
    (1, 8, "PC negative"),
    (9, 14, "PC positive"),
    (15, 22, "NPC negative"),
    (23, 28, "NPC positive"),
    (29, 36, "NPC action"),
    (37, 44, "NPC appearance"),
    (45, 52, "NPC altered"),
    (53, 60, "Ambiguous"),
    (61, 68, "Remote event"),
    (69, 76, "PC action"),
    (77, 84, "PC appearance"),
    (85, 92, "New NPC"),
    (93, 100, "PC altered"),
)

# A random event's meaning is a descriptor plus a subject: the tens digit of
# a d100 indexes one list and the ones digit the other.
EVENT_DESCRIPTORS = (
    "Abandoned", "Betrayed", "Confused", "Desperate", "Frozen",
    "Hidden", "Imprisoned", "Jubilant", "Quiet", "Shattered",
)

EVENT_SUBJECTS = (
    "a hope", "the party", "an old ally", "a rival", "the weather",
    "a rumor", "a treasure", "a path", "a ritual", "the dungeon",
)


@dataclass(frozen=True)
class OracleAnswer:
    """The outcome of a single fate question."""

    question: str
    odds: str
    roll: int
    answer: str
    event: str | None = None


def odds_threshold(odds):
    """The d100 threshold for an odds label; rolls at or below it answer Yes."""
    for label, threshold in ODDS:
        if label == odds:
            return threshold
    raise ValueError(f"Unknown odds level: {odds!r}")


def answer_for(roll, odds):
    """The verdict for a d100 `roll` under the given `odds`."""
    if roll <= EXCEPTIONAL_YES:
        return "Exceptional Yes"
    if roll >= EXCEPTIONAL_NO:
        return "Exceptional No"
    return "Yes" if roll <= odds_threshold(odds) else "No"


def event_focus(roll):
    """The random-event focus label for a d100 `roll`."""
    for low, high, label in EVENT_FOCUS:
        if low <= roll <= high:
            return label
    return "Ambiguous"


def event_meaning(roll):
    """A two-word meaning ('descriptor, subject') for a d100 `roll`."""
    return f"{EVENT_DESCRIPTORS[roll // 10]}, {EVENT_SUBJECTS[roll % 10]}"


def random_event(focus_roll, meaning_roll):
    """A full random-event twist from two d100 rolls."""
    return f"{event_focus(focus_roll)} — {event_meaning(meaning_roll)}"


def resolve(question, odds, roll, chaos_roll=None, chaos_factor=0,
            focus_roll=0, meaning_roll=0):
    """Answer a fate question, optionally including a random-event twist.

    A twist fires when `chaos_roll` is given and at or below `chaos_factor`;
    its focus and meaning come from `focus_roll` and `meaning_roll`.
    """
    event = None
    if chaos_roll is not None and chaos_roll <= chaos_factor:
        event = random_event(focus_roll, meaning_roll)
    return OracleAnswer(question, odds, roll, answer_for(roll, odds), event)
