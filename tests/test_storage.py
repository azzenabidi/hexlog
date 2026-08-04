"""Tests for the persistence layer. No GUI is required."""

import json
import os

import pytest

from hexlog import constants as C


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Point the storage layer at a throwaway directory."""
    # DATA_DIR must not exist yet so a fresh start creates it from scratch.
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


def test_next_color_prefers_unused(isolated_paths):
    from hexlog.storage import next_color

    assert next_color([]) == C.COLOR_PALETTE[0]
    assert next_color([{"color": C.COLOR_PALETTE[0]}]) == C.COLOR_PALETTE[1]


def test_next_color_rotates_when_palette_exhausted(isolated_paths):
    from hexlog.storage import next_color

    full = [{"color": c} for c in C.COLOR_PALETTE]
    assert next_color(full) in C.COLOR_PALETTE


def test_save_keeps_previous_backup(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    store.add(C.CHARACTERS, {"id": "v1", "name": "first"})
    store.save()
    store.add(C.CHARACTERS, {"id": "v2", "name": "second"})
    store.save()

    with open(C.DATA_FILE + ".bak", "r") as fh:
        backup = json.load(fh)
    assert [e["id"] for e in backup[C.CHARACTERS]] == ["v1"]
    with open(C.DATA_FILE, "r") as fh:
        current = json.load(fh)
    assert [e["id"] for e in current[C.CHARACTERS]] == ["v1", "v2"]


def test_load_recovers_from_backup_when_main_file_is_corrupt(isolated_paths):
    from hexlog.storage import Store

    store = Store()
    store.add(C.CHARACTERS, {"id": "v1", "name": "first"})
    store.save()
    store.add(C.CHARACTERS, {"id": "v2", "name": "second"})
    store.save()

    with open(C.DATA_FILE, "w") as fh:
        fh.write("{ this is not valid json")

    recovered = Store()
    assert [e["id"] for e in recovered[C.CHARACTERS]] == ["v1"]


def test_migrates_legacy_root_data_into_subdir(isolated_paths):
    from hexlog.storage import load_data

    legacy = C.LEGACY_DATA_DIR
    os.makedirs(os.path.join(legacy, "maps"), exist_ok=True)
    os.makedirs(os.path.join(legacy, "tokens"), exist_ok=True)
    with open(os.path.join(legacy, "data.json"), "w") as fh:
        json.dump({"characters": [{"id": "legacy"}]}, fh)
    with open(os.path.join(legacy, "data.json.bak"), "w") as fh:
        json.dump({"characters": []}, fh)

    data = load_data()
    assert data["characters"] == [{"id": "legacy"}]
    assert os.path.exists(C.DATA_FILE)
    assert not os.path.exists(os.path.join(legacy, "data.json"))
    assert os.path.isdir(C.MAPS_DIR)
    assert os.path.isdir(C.TOKENS_DIR)


def test_migrates_recent_subdir_layout(isolated_paths):
    from hexlog.storage import load_data

    recent = os.path.join(C.LEGACY_DATA_DIR, C.DATA_SUBDIR)
    os.makedirs(os.path.join(recent, "maps"), exist_ok=True)
    with open(os.path.join(recent, "data.json"), "w") as fh:
        json.dump({"characters": [{"id": "recent"}]}, fh)

    data = load_data()
    assert data["characters"] == [{"id": "recent"}]
    assert os.path.exists(C.DATA_FILE)
    assert not os.path.exists(recent)
    assert os.path.isdir(C.MAPS_DIR)


def test_does_not_migrate_when_subdir_data_already_exists(isolated_paths):
    from hexlog.storage import migrate_legacy_data, save_data

    legacy = C.LEGACY_DATA_DIR
    save_data({"characters": [{"id": "new"}]})
    os.makedirs(legacy, exist_ok=True)
    with open(os.path.join(legacy, "data.json"), "w") as fh:
        json.dump({"characters": [{"id": "legacy"}]}, fh)

    migrate_legacy_data()
    with open(C.DATA_FILE) as fh:
        assert json.load(fh)["characters"] == [{"id": "new"}]
