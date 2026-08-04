"""Tests for input validation rules (no GUI required)."""

from hexlog.validation import validate_name


def test_empty_name_is_rejected():
    assert validate_name("") == "Name cannot be empty."
    assert validate_name("   ") == "Name cannot be empty."


def test_valid_names_pass():
    assert validate_name("Gandalf") is None
    assert validate_name("  Aragorn the King  ") is None
    assert validate_name("Ara'bel") is None
    assert validate_name("Blade-of-Morning") is None
    assert validate_name("Red & Black") is None


def test_special_characters_are_rejected():
    assert validate_name("G@ndalf") is not None
    assert validate_name("Goblin*") is not None
    assert validate_name("name#1") is not None


def test_error_message_names_the_offending_characters():
    message = validate_name("G@ndalf!")
    assert "@" in message
    assert "!" in message
