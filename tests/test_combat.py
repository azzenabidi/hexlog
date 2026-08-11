"""Tests for the pure combat engine (no GUI required)."""

from hexlog.combat import (
    apply_damage,
    apply_healing,
    combat_status,
    current_combatant,
    is_defeated,
    next_combatant,
    parse_hp,
    roll_initiative,
    set_active,
    toggle_condition,
)


class FakeRng:
    """A scripted rng: randint() returns the next queued value."""

    def __init__(self, values):
        self.values = list(values)

    def randint(self, low, high):
        return self.values.pop(0)


def token(token_id, name, max_hp=None):
    """A minimal scene-token dict."""
    return {"id": token_id, "name": name, "max_hp": max_hp,
            "hp": max_hp, "initiative": None, "conditions": []}


def test_parse_hp_reads_the_leading_integer():
    assert parse_hp("27") == 27
    assert parse_hp("32 (5d8+10)") == 32
    assert parse_hp(" 5 ") == 5


def test_parse_hp_returns_none_when_unparseable():
    assert parse_hp(None) is None
    assert parse_hp("") is None
    assert parse_hp("?") is None
    assert parse_hp("hp unknown") is None


def test_roll_initiative_assigns_rolls_and_sorts_descending():
    combatants = [token("a", "Goblin"), token("b", "Orc"), token("c", "Kobold")]
    ordered = roll_initiative(combatants, FakeRng([9, 15, 15]))
    assert [c["id"] for c in ordered] == ["b", "c", "a"]
    assert combatants[0]["initiative"] == 9
    assert combatants[1]["initiative"] == 15


def test_roll_initiative_breaks_ties_by_max_hp_then_name():
    combatants = [
        token("a", "Orc", max_hp=15),
        token("b", "Orc", max_hp=10),
        token("c", "Orc", max_hp=15),
    ]
    ordered = roll_initiative(combatants, FakeRng([10, 10, 10]))
    assert [c["id"] for c in ordered] == ["a", "c", "b"]


def test_roll_initiative_uses_global_random_by_default():
    combatant = token("a", "Goblin")
    ordered = roll_initiative([combatant])
    assert 1 <= combatant["initiative"] <= 20
    assert ordered == [combatant]


def test_apply_damage_floors_at_zero():
    combatant = token("a", "Orc", max_hp=15)
    combatant["hp"] = 15
    apply_damage(combatant, 5)
    assert combatant["hp"] == 10
    apply_damage(combatant, 99)
    assert combatant["hp"] == 0


def test_apply_damage_is_a_noop_without_hp():
    combatant = token("a", "Bystander")
    apply_damage(combatant, 5)
    assert combatant["hp"] is None


def test_apply_healing_caps_at_max_hp():
    combatant = token("a", "Orc", max_hp=15)
    combatant["hp"] = 3
    apply_healing(combatant, 5)
    assert combatant["hp"] == 8
    apply_healing(combatant, 99)
    assert combatant["hp"] == 15


def test_toggle_condition_adds_and_removes():
    combatant = token("a", "Orc", max_hp=15)
    toggle_condition(combatant, "bleeding")
    assert combatant["conditions"] == ["bleeding"]
    toggle_condition(combatant, "poisoned")
    assert combatant["conditions"] == ["bleeding", "poisoned"]
    toggle_condition(combatant, "bleeding")
    assert combatant["conditions"] == ["poisoned"]


def test_current_combatant_and_set_active():
    combatants = [token("a", "Orc", max_hp=15), token("b", "Kobold")]
    set_active(combatants, "b")
    assert current_combatant(combatants)["id"] == "b"
    assert combatants[0]["is_active"] is False
    set_active(combatants, "a")
    assert current_combatant(combatants)["id"] == "a"
    assert combatants[1]["is_active"] is False


def test_next_combatant_wraps_around():
    combatants = [token("a", "Orc"), token("b", "Kobold"), token("c", "Goblin")]
    assert next_combatant(combatants, "a")["id"] == "b"
    assert next_combatant(combatants, "c")["id"] == "a"
    assert next_combatant(combatants, "missing")["id"] == "a"
    assert next_combatant([], "a") is None


def test_is_defeated_and_status():
    live = token("a", "Orc", max_hp=15)
    assert not is_defeated(live)
    assert combat_status(live) == "15/15"
    apply_damage(live, 15)
    assert is_defeated(live)
    assert combat_status(live) == "Down"


def test_combat_status_shows_a_dash_without_hp():
    bystander = token("a", "Bystander")
    assert combat_status(bystander) == "-"
    assert not is_defeated(bystander)
