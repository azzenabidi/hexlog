"""Persistence layer: disk paths, load/save, and the shared Store model.

The Store is the single source of truth for the app's JSON document. Every
tab receives one Store instance and mutates it through the generic CRUD
helpers; the main window calls Store.save() whenever a tab reports a change.
"""

import copy
import json
import os
import shutil
import uuid

from hexlog import constants as C


def ensure_dirs() -> None:
    """Create the app's data directories if they do not exist."""
    os.makedirs(C.MAPS_DIR, exist_ok=True)
    os.makedirs(C.TOKENS_DIR, exist_ok=True)


def migrate_legacy_data() -> None:
    """One-time move of old data (~/.hexlog/) into the active config subdir.

    Data lived at ~/.hexlog/{dev,prod} for a short 0.3.3 pre-release and at
    ~/.hexlog/ (data.json, maps/, tokens/) before that. Existing files are
    moved into ~/.config/hexlog/{dev,prod} once so nothing appears lost.
    """
    if os.path.exists(C.DATA_FILE):
        return
    recent_dir = os.path.join(C.LEGACY_DATA_DIR, C.DATA_SUBDIR)
    if os.path.isdir(recent_dir):
        os.makedirs(os.path.dirname(C.DATA_DIR), exist_ok=True)
        shutil.move(recent_dir, C.DATA_DIR)
        return
    legacy_file = os.path.join(C.LEGACY_DATA_DIR, "data.json")
    if not os.path.exists(legacy_file):
        return
    os.makedirs(C.DATA_DIR, exist_ok=True)
    shutil.move(legacy_file, C.DATA_FILE)
    if os.path.exists(legacy_file + ".bak"):
        shutil.move(legacy_file + ".bak", C.DATA_FILE + ".bak")
    for name, target in (("maps", C.MAPS_DIR), ("tokens", C.TOKENS_DIR)):
        source = os.path.join(C.LEGACY_DATA_DIR, name)
        if os.path.isdir(source):
            shutil.move(source, target)


def _read_json(path):
    """Read a JSON file, returning None if it is missing or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _quarantine(path, suffix):
    """Copy an unreadable store file aside so a later save cannot overwrite it."""
    try:
        shutil.copy2(path, path + suffix)
    except OSError:
        pass  # nothing more we can do; the app must still start


def load_data():
    """Read the JSON store, falling back to a fresh template on any error.

    Returns a (data, warnings) pair: `data` is always a usable store and
    `warnings` describes any recovery performed. A corrupt or missing main file
    must not crash startup; the backup from the last good save is used first,
    and unreadable files are copied aside (data.json.corrupt) instead of being
    silently overwritten by the next autosave.
    """
    migrate_legacy_data()
    ensure_dirs()
    warnings = []
    data = _read_json(C.DATA_FILE)
    if data is None:
        if os.path.exists(C.DATA_FILE):
            _quarantine(C.DATA_FILE, ".corrupt")
            warnings.append(
                "data.json was unreadable; the original was kept as data.json.corrupt."
            )
        data = _read_json(C.DATA_FILE + ".bak")
        if data is not None:
            warnings.append("Recovered the last good copy from the backup.")
        elif os.path.exists(C.DATA_FILE + ".bak"):
            _quarantine(C.DATA_FILE + ".bak", ".corrupt")
            warnings.append(
                "The backup was unreadable too; it was kept as data.json.bak.corrupt."
            )
    if not isinstance(data, dict):
        data = copy.deepcopy(C.DEFAULT_DATA)
    # Backfill keys added in newer versions for compatibility with old files.
    for key in C.DEFAULT_DATA:
        data.setdefault(key, [])
    _backfill_scene_tokens(data)
    return data, warnings


def _backfill_scene_tokens(data) -> None:
    """Add combat fields to scene tokens written before they existed.

    Older scenes serialize tokens without an instance id or combat numbers;
    a fresh id keeps the combat tracker able to distinguish duplicate tokens
    of the same entity, and a token with a statblock starts at full HP.
    """
    for scene in data.get(C.SCENES, []):
        for token in scene.get("tokens", []):
            token.setdefault("id", C.new_id())
            token.setdefault("max_hp", None)
            token.setdefault("hp", token.get("max_hp"))
            token.setdefault("initiative", None)
            token.setdefault("conditions", [])
            token.setdefault("is_active", False)


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


def import_image(source_path, target_dir):
    """Copy an image under a fresh random basename, returning its file name.

    The random basename keeps identically named files from colliding, and
    None is returned when the copy fails so the caller can surface the error.
    """
    dest_name = f"{uuid.uuid4().hex[:8]}{os.path.splitext(source_path)[1]}"
    try:
        shutil.copy(source_path, os.path.join(target_dir, dest_name))
    except OSError:
        return None
    return dest_name


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
        self.data, self.warnings = load_data()

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
