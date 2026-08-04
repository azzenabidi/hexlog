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
    """Create the app's data directories, migrating the legacy folder once."""
    # Only migrate when the new dir does not exist yet, so a fresh setup
    # never clobbers an already-populated install.
    if not os.path.exists(C.DATA_DIR) and os.path.isdir(C.LEGACY_DATA_DIR):
        try:
            shutil.copytree(C.LEGACY_DATA_DIR, C.DATA_DIR)
        except Exception:
            # Copy is best-effort; a partial failure still leaves a usable app.
            pass
    os.makedirs(C.MAPS_DIR, exist_ok=True)
    os.makedirs(C.TOKENS_DIR, exist_ok=True)


def load_data() -> dict:
    """Read the JSON store, falling back to a fresh template on any error."""
    ensure_dirs()
    try:
        with open(C.DATA_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        # A missing or corrupt file must not crash the app on startup.
        data = copy.deepcopy(C.DEFAULT_DATA)
    # Backfill keys added in newer versions for compatibility with old files.
    for key in C.DEFAULT_DATA:
        data.setdefault(key, [])
    _migrate_legacy_map_paths(data)
    return data


def save_data(data: dict) -> None:
    """Persist the whole store to disk as pretty-printed UTF-8 JSON."""
    ensure_dirs()
    with open(C.DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _migrate_legacy_map_paths(data: dict) -> None:
    """Rewrite legacy absolute map paths to basenames under the new layout."""
    legacy_prefix = C.LEGACY_DATA_DIR + os.sep
    for scene in data.get("scenes", []):
        mp = scene.get("map_path")
        if mp and os.path.isabs(mp) and mp.startswith(legacy_prefix):
            scene["map_path"] = os.path.basename(mp)


def next_color(entities) -> str:
    """Pick the next palette color, rotating so repeats look intentional."""
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
