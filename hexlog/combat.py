"""Combat engine: initiative, HP, and conditions for VTT tokens.

Operates on plain dicts (the serialized shape of scene tokens) and mutates
them in place, so the rules are pure and deterministic under test with an
injected rng. Widgets own the display; this module owns the rules. Tokens
without a parsed max_hp (e.g. a character with no statblock) simply have no
combat numbers: damage/healing are no-ops and the status reads as a dash.
"""

import random


def parse_hp(value):
    """The leading integer of a statblock HP string, or None if unparseable.

    Handles "27", "32 (5d8+10)", and leading-dash variants; anything that
    does not start with a number (e.g. "?" or an empty field) is None so
    the UI can degrade honestly instead of inventing a hit total.
    """
    if value is None:
        return None
    digits = ""
    for char in str(value).strip():
        if not char.isdigit():
            break
        digits += char
    return int(digits) if digits else None


def initiative_sort_key(combatant):
    """Order combatants by initiative, then max HP, then name."""
    return (
        combatant.get("initiative", 0),
        combatant.get("max_hp") or 0,
        combatant.get("name", ""),
    )


def roll_initiative(combatants, rng=None):
    """Roll a d20 for every combatant and return them in acting order.

    Mutates each combatant's "initiative" in place; ties break by higher
    max HP, then alphabetically by name.
    """
    rng = rng or random
    for combatant in combatants:
        combatant["initiative"] = rng.randint(1, 20)
    return sorted(combatants, key=initiative_sort_key, reverse=True)


def apply_damage(combatant, amount):
    """Reduce hp by `amount`, flooring at 0. No-op without a max_hp."""
    if combatant.get("max_hp") is None:
        return
    current = combatant.get("hp", combatant["max_hp"])
    combatant["hp"] = max(0, current - amount)


def apply_healing(combatant, amount):
    """Restore hp by `amount`, capping at max_hp. No-op without a max_hp."""
    if combatant.get("max_hp") is None:
        return
    current = combatant.get("hp", combatant["max_hp"])
    combatant["hp"] = min(combatant["max_hp"], current + amount)


def toggle_condition(combatant, condition):
    """Add a condition string if absent, otherwise remove it."""
    conditions = combatant.setdefault("conditions", [])
    if condition in conditions:
        conditions.remove(condition)
    else:
        conditions.append(condition)


def current_combatant(combatants):
    """The combatant whose turn it is, or None when not in combat."""
    for combatant in combatants:
        if combatant.get("is_active"):
            return combatant
    return None


def set_active(combatants, token_id):
    """Flag exactly one combatant (by token id) as the current turn."""
    for combatant in combatants:
        combatant["is_active"] = combatant.get("id") == token_id


def next_combatant(combatants, token_id):
    """The combatant acting after `token_id`, wrapping to the first."""
    if not combatants:
        return None
    ids = [c.get("id") for c in combatants]
    if token_id not in ids:
        return combatants[0]
    return combatants[(ids.index(token_id) + 1) % len(combatants)]


def is_defeated(combatant):
    """True when a combatant with HP is at zero."""
    return combatant.get("max_hp") is not None and combatant.get("hp", 0) <= 0


def combat_status(combatant):
    """Short status line for a combat row: '12/25', 'Down', or a dash."""
    if combatant.get("max_hp") is None:
        return "-"
    current = combatant.get("hp", combatant["max_hp"])
    if current <= 0:
        return "Down"
    return f"{current}/{combatant['max_hp']}"
