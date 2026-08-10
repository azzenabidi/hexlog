"""Shadowdark SoloDark oracle: answer yes/no fate questions with a d20.

Implements the Oracle from SoloDark (the official solo rules for
Shadowdark RPG by Kelsey Dionne / The Arcane Library). Decide the odds,
make an oracle check, and read the verdict:

* d20 result 1-9       No
* d20 result 10        Twist - roll a Prompt to learn its nature
* d20 result 11-20     Yes
* Natural 1 or 20      critical - the most extreme version ("No, and")
* odd result except 1  a "but" turnabout is attached to the verdict

Odds adjust the check itself: Unlikely or Impossible rolls with
disadvantage (2d20, keep the lowest), Likely or Certain with advantage
(2d20, keep the highest), and Even Chance is a single d20.

Everything here is a pure function of the provided rolls, so the engine
is deterministic under test; the dialog owns the randomness.
"""

from dataclasses import dataclass

# (label, kind): the kind tells roll_check() how many dice to roll and how
# to keep them. Ordered from unlikely to likely so a UI can present it so.
ODDS = (
    ("Unlikely or Impossible", "disadvantage"),
    ("Even Chance", "standard"),
    ("Likely or Certain", "advantage"),
)

ODDS_LABELS = tuple(label for label, _ in ODDS)

# d100 prompt table: a single roll picks one verb + noun pair to spark an
# idea or the nature of a twist. Index 0 is roll 01 and index 99 is roll 00.
PROMPTS = (
    ("Stop", "Freedom"), ("Tell", "Life"), ("Trust", "Battle"),
    ("Prevent", "Lie"), ("Deliver", "Vice"), ("Dismantle", "Memory"),
    ("Create", "Burden"), ("Resist", "Treachery"), ("Imbue", "Trial"),
    ("Befriend", "Risk"), ("Sneak", "Prosperity"), ("Disagree", "Time"),
    ("Illuminate", "Conflict"), ("Assemble", "Light"), ("Free", "Unnatural"),
    ("Combine", "Information"), ("Disrupt", "Hope"), ("Demand", "Journey"),
    ("Obstruct", "Mundane"), ("Push", "Hazard"), ("Arrive", "Family"),
    ("Slow", "Obstacle"), ("Overcome", "Doubt"), ("Block", "Freedom"),
    ("Consume", "Weakness"), ("Pursue", "Unknown"), ("Reward", "Glory"),
    ("Expand", "Friend"), ("Waste", "Discovery"), ("Capture", "Lead"),
    ("Weaken", "Storm"), ("Reveal", "Enemy"), ("Investigate", "Integrity"),
    ("Forbid", "Science"), ("Start", "Asset"), ("Surprise", "Crime"),
    ("Endure", "Wisdom"), ("Pull", "Justice"), ("Unleash", "Strife"),
    ("Avoid", "Disgust"), ("Advance", "Danger"), ("Agree", "Balance"),
    ("Deliver", "Nature"), ("Link", "Chaos"), ("Hinder", "Ambush"),
    ("Withhold", "Wealth"), ("Lose", "Thought"), ("Evolve", "Dark"),
    ("Fortify", "Connection"), ("Punish", "Door"), ("Ignite", "Fear"),
    ("Awaken", "Sorcery"), ("Defy", "Honor"), ("Conceal", "Spirit"),
    ("Invite", "Trust"), ("Break", "Loss"), ("Allow", "Failure"),
    ("Open", "Peril"), ("Repel", "Plan"), ("Activate", "Trick"),
    ("Gather", "Mind"), ("Give", "Pain"), ("Reverse", "Victory"),
    ("Warn", "Death"), ("Confront", "Control"), ("Betray", "Knowledge"),
    ("Secure", "Secret"), ("Darken", "Kindness"), ("Flee", "Exploration"),
    ("Win", "Surprise"), ("Scatter", "Magic"), ("Contain", "Animal"),
    ("Assist", "Way"), ("Take", "Essence"), ("Question", "Dream"),
    ("Drop", "Anger"), ("Accept", "Vision"), ("Sacrifice", "Safety"),
    ("Drain", "Result"), ("Hint", "Place"), ("Fumble", "Path"),
    ("Fall", "Nourishment"), ("Ascend", "Theft"), ("Protect", "Decay"),
    ("Escape", "Truth"), ("Defeat", "People"), ("Mend", "Help"),
    ("Acquire", "Gear"), ("Guide", "Idea"), ("Mislead", "Order"),
    ("Banish", "Success"), ("Uphold", "Barrier"), ("Build", "Goal"),
    ("Change", "Luck"), ("Revoke", "Identity"), ("Seek", "Harm"),
    ("Destroy", "Wilderness"), ("Uncover", "Motive"), ("Rest", "Shelter"),
    ("Release", "Power"),
)

PROMPT_LABELS = tuple(f"{verb} {noun}" for verb, noun in PROMPTS)


@dataclass(frozen=True)
class OracleAnswer:
    """The outcome of a single fate question."""

    question: str
    odds: str
    roll: int
    answer: str
    twist: str | None = None


def odds_kind(odds):
    """How the oracle check is rolled for a given odds label."""
    for label, kind in ODDS:
        if label == odds:
            return kind
    raise ValueError(f"Unknown odds level: {odds!r}")


def roll_check(kind, rng):
    """The d20 oracle check for a roll `kind`, using `rng` for randomness.

    `kind` is one of "standard", "disadvantage", or "advantage"; the last
    two roll twice and keep the lowest or highest respectively.
    """
    if kind == "disadvantage":
        return min(rng.randint(1, 20), rng.randint(1, 20))
    if kind == "advantage":
        return max(rng.randint(1, 20), rng.randint(1, 20))
    return rng.randint(1, 20)


def prompt(roll):
    """The verb-noun prompt for a d100 `roll` (00 reads as 100)."""
    if not 1 <= roll <= 100:
        raise ValueError(f"Prompt roll out of range: {roll!r}")
    return PROMPT_LABELS[roll - 1]


def answer_for(roll):
    """The verdict for a d20 oracle check `roll`."""
    if roll == 1:
        return "No, and"
    if roll == 20:
        return "Yes, and"
    if roll == 10:
        return "Twist"
    base = "Yes" if roll >= 11 else "No"
    if roll % 2:
        return f"{base}, but"
    return base


def resolve(question, odds, roll, twist_roll=None):
    """Answer a fate question from its final d20 oracle check `roll`.

    When the check lands on 10 (a twist) and `twist_roll` is given, the
    answer carries the prompt describing the twist's nature.
    """
    twist = prompt(twist_roll) if roll == 10 and twist_roll is not None else None
    return OracleAnswer(question, odds, roll, answer_for(roll), twist)
