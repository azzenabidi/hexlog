"""Tests for the journal's mention matching (no GUI required)."""

from hexlog.ui.notes import (
    MentionHighlighter,
    dialogue_caret_offset,
    mention_pattern,
    notes_mentioning,
    referenced_ids,
)


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


def test_notes_mentioning_orders_into_a_timeline():
    notes = [
        {"id": "n2", "title": "Fight", "timestamp": "2026-08-02 20:00", "text": "The Cat ambushed us."},
        {"id": "n1", "title": "Meet", "timestamp": "2026-08-01 09:00", "text": "We met Cat in the ruins."},
        {"id": "n3", "title": "Other", "timestamp": "2026-08-03 12:00", "text": "Nothing about it here."},
    ]
    entity = {"id": "e1", "name": "Cat"}
    ids = [n["id"] for n in notes_mentioning(notes, entity)]
    assert ids == ["n1", "n2"]


def test_notes_mentioning_matches_whole_words_only():
    notes = [{"id": "n1", "title": "T", "timestamp": "", "text": "A category of cats."}]
    assert notes_mentioning(notes, {"id": "e1", "name": "Cat"}) == []


def test_notes_mentioning_ignores_unnamed_entities():
    note = {"id": "n1", "title": "T", "timestamp": "", "text": "Anything"}
    assert notes_mentioning([note], {"id": "e1", "name": ""}) == []
    assert notes_mentioning([note], None) == []


def test_dialogue_caret_sits_between_the_quotes():
    for name in ("Al", "Goblin King", "Sir  <Bad>"):
        prefix = f"\n{name}: \""
        text = f"{prefix}\""
        offset = dialogue_caret_offset(name)
        assert offset == len(prefix)
        assert text[offset - 1] == '"'  # opening quote, just before the caret
        assert text[offset] == '"'  # closing quote, just after the caret


def test_highlighter_ignores_unnamed_entities():
    hl = MentionHighlighter(None, lambda: [{"id": "1", "name": ""}, {"id": "2", "name": "Marc"}])
    hl.refresh()
    assert [pattern for pattern, _ in hl.rules] == [mention_pattern("Marc")]


def test_highlighter_caches_patterns_by_name():
    entities = [{"id": "1", "name": "Cat"}, {"id": "2", "name": "Goblin King"}]
    hl = MentionHighlighter(None, lambda: entities)

    hl.refresh()
    cached = dict(hl._pattern_cache)
    assert set(cached) == {"Cat", "Goblin King"}

    # Rebuilding rules for the same names must reuse the cached patterns.
    hl.refresh()
    assert hl._pattern_cache == cached


def test_highlighter_drops_stale_patterns_on_rename():
    entities = [{"id": "1", "name": "Cat"}, {"id": "2", "name": "Goblin King"}]
    hl = MentionHighlighter(None, lambda: entities)
    hl.refresh()

    entities[0]["name"] = "Tiger"
    hl.refresh()
    assert set(hl._pattern_cache) == {"Tiger", "Goblin King"}
