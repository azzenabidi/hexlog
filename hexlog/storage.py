"""Persistence layer: disk paths, load/save, and the shared Store model.

The Store is the single source of truth for the app's JSON document. Every
tab receives one Store instance and mutates it through the generic CRUD
helpers; the main window calls Store.save() whenever a tab reports a change.
"""

import copy
import json
import os
import shutil

from hexlog import constants as C


def ensure_dirs() -> None:
    """Create the app's data directories if they do not exist."""
    os.makedirs(C.MAPS_DIR, exist_ok=True)
    os.makedirs(C.TOKENS_DIR, exist_ok=True)


def _read_json(path):
    """Read a JSON file, returning None if it is missing or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def load_data() -> dict:
    """Read the JSON store, falling back to a fresh template on any error.

    A missing or corrupt main file must not crash the app on startup; when the
    main file is unreadable, the backup from the last good save is used first.
    """
    ensure_dirs()
    data = _read_json(C.DATA_FILE)
    if data is None:
        data = _read_json(C.DATA_FILE + ".bak")
    if not isinstance(data, dict):
        data = copy.deepcopy(C.DEFAULT_DATA)
    # Backfill keys added in newer versions for compatibility with old files.
    for key in C.DEFAULT_DATA:
        data.setdefault(key, [])
    return data


def save_data(data: dict) -> None:
    """Persist the whole store to disk as pretty-printed UTF-8 JSON.

    Writes atomically (temp file + rename) and keeps a one-generation backup,
    so a crash mid-save can never leave the user's data file half-written.
    """
    ensure_dirs()
    tmp_file = C.DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    if os.path.exists(C.DATA_FILE):
        shutil.copy2(C.DATA_FILE, C.DATA_FILE + ".bak")
    os.replace(tmp_file, C.DATA_FILE)


def next_color(entities) -> str:
    """Pick a palette color no existing entity uses, falling back to rotation.

    Preferring unused colors keeps each entity's token visually distinct even
    after others are deleted.
    """
    used = {e.get("color") for e in entities if e.get("color")}
    for color in C.COLOR_PALETTE:
        if color not in used:
            return color
    return C.COLOR_PALETTE[len(entities) % len(C.COLOR_PALETTE)]


class Store:
    """Central data model shared by every tab.

    Owns the JSON document, exposes generic CRUD plus lookup helpers, and
    handles persistence. The main window hands this single instance to all
    tabs and calls save() whenever a tab reports a change.
    """

    def __init__(self) -> None:
        self.data = load_data()

    def __getitem__(self, kind: str) -> list:
        """Return the list of records for a given kind key."""
        return self.data[kind]

    def find(self, kind: str, entity_id: str):
        """Return the record with `entity_id` in `kind`, or None."""
        for entity in self.data[kind]:
            if entity["id"] == entity_id:
                return entity
        return None

    def add(self, kind: str, entity: dict) -> None:
        """Append a new record to the end of its collection."""
        self.data[kind].append(entity)

    def prepend(self, kind: str, entity: dict) -> None:
        """Insert a record at the front of its collection (newest first)."""
        self.data[kind].insert(0, entity)

    def remove(self, kind: str, entity_id: str) -> None:
        """Drop the record with `entity_id` from its collection, if present."""
        self.data[kind] = [e for e in self.data[kind] if e["id"] != entity_id]

    def save(self) -> None:
        """Write the store to disk."""
        save_data(self.data)
