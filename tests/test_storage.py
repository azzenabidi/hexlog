"""Tests for the persistence layer. No GUI is required."""

import json
import os

import pytest

from hexlog import constants as C


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Point the storage layer at a throwaway directory."""
    # DATA_DIR must not exist yet so the legacy-migration path can be tested.
    data_dir = tmp_path / "data"
    monkeypatch.setattr(C, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(C, "DATA_FILE", str(data_dir / "data.json"))
    monkeypatch.setattr(C, "MAPS_DIR", str(data_dir / "maps"))
    monkeypatch.setattr(C, "TOKENS_DIR", str(data_dir / "tokens"))
    monkeypatch.setattr(C, "LEGACY_DATA_DIR", str(tmp_path / "legacy"))


def test_fresh_store_has_default_shape(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    for kind in C.KINDS:
        assert store[kind] == []
    assert os.path.isdir(C.MAPS_DIR)
    assert os.path.isdir(C.TOKENS_DIR)


def test_save_and_reload_roundtrip(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    entity = {"id": C.new_id(), "name": "Marc", "color": "#e74c3c"}
    store.add(C.CHARACTERS, entity)
    store.save()

    reloaded = Store()
    assert reloaded.find(C.CHARACTERS, entity["id"]) == entity


def test_find_returns_none_for_missing(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    assert store.find(C.NPCS, "does-not-exist") is None


def test_remove_removes_only_matching_id(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    store.add(C.NPCS, {"id": "aaa", "name": "A"})
    store.add(C.NPCS, {"id": "bbb", "name": "B"})
    store.remove(C.NPCS, "aaa")
    assert [e["id"] for e in store[C.NPCS]] == ["bbb"]


def test_prepend_puts_newest_first(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    store.prepend(C.NOTES, {"id": "first", "name": "oldest"})
    store.prepend(C.NOTES, {"id": "second", "name": "newest"})
    assert [n["id"] for n in store[C.NOTES]] == ["second", "first"]


def test_load_backfills_missing_keys(isolated_paths):
    from hexlog.storage import Store

    os.makedirs(C.DATA_DIR, exist_ok=True)
    with open(C.DATA_FILE, "w") as fh:
        json.dump({"characters": [{"id": "c1"}]}, fh)

    store = Store()
    assert store[C.CHARACTERS] == [{"id": "c1"}]
    for kind in (C.NPCS, C.LOCATIONS, C.MONSTERS, C.NOTES, C.SCENES):
        assert store[kind] == []


def test_legacy_migration_copies_and_rewrites_map_paths(isolated_paths):
    from hexlog import storage

    legacy_data = {
        "scenes": [{"id": "s1", "map_path": os.path.join(C.LEGACY_DATA_DIR, "maps", "m.png")}]
    }
    os.makedirs(C.LEGACY_DATA_DIR, exist_ok=True)
    with open(os.path.join(C.LEGACY_DATA_DIR, "data.json"), "w") as fh:
        json.dump(legacy_data, fh)

    data = storage.load_data()
    assert os.path.isdir(C.DATA_DIR)
    assert data["scenes"][0]["map_path"] == "m.png"


def test_next_color_rotates(isolated_paths):
    from hexlog.storage import next_color

    n = len(C.COLOR_PALETTE)
    first = next_color([])
    assert next_color(list(range(n))) == first
