"""Tests for the journal's mention matching (no GUI required)."""

from hexlog.ui.notes import dialogue_caret_offset, mention_pattern, referenced_ids


def test_referenced_matches_whole_words_only():
    entities = [{"id": "1", "name": "Cat"}, {"id": "2", "name": "Goblin King"}]
    assert referenced_ids(entities, "The Cat sat down.") == ["1"]
    assert referenced_ids(entities, "A category of goblins.") == []
    assert referenced_ids(entities, "Goblin King rules.") == ["2"]
    assert referenced_ids(entities, "nothing here") == []


def test_referenced_ignores_unnamed_entities():
    entities = [{"id": "1", "name": ""}, {"id": "2", "name": "Marc"}]
    assert referenced_ids(entities, "Marc") == ["2"]


def test_mention_pattern_uses_word_boundaries():
    assert mention_pattern("Cat").search("A Cat sat") is not None
    assert mention_pattern("Cat").search("category") is None


def test_dialogue_caret_sits_between_the_quotes():
    for name in ("Al", "Goblin King", "Sir  <Bad>"):
        prefix = f"\n{name}: \""
        text = f"{prefix}\""
        offset = dialogue_caret_offset(name)
        assert offset == len(prefix)
        assert text[offset - 1] == '"'  # opening quote, just before the caret
        assert text[offset] == '"'  # closing quote, just after the caret
