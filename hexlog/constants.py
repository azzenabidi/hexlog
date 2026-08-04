"""App-wide constants: names, paths, and shared defaults.

Paths are derived from the user's home directory so the app needs no
install-time configuration. The persistence layer in storage.py is the only
module that reads and writes these locations.
"""

import os
import uuid

APP_NAME = "Hexlog"
# Data lives under the user's home so the app needs no install-time setup.
DATA_DIR = os.path.join(os.path.expanduser("~"), ".hexlog")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
# Map images are copied here; scenes reference them by basename only.
MAPS_DIR = os.path.join(DATA_DIR, "maps")
# Character/NPC token images are copied here for the same reason.
TOKENS_DIR = os.path.join(DATA_DIR, "tokens")

# Cycled through when creating new characters so tokens start visually distinct.
COLOR_PALETTE = [
    "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c", "#3498db",
    "#9b59b6", "#e84393", "#16a085", "#d35400", "#8e44ad", "#2980b9",
]

# Canonical top-level keys of the JSON store.
CHARACTERS = "characters"
NPCS = "npcs"
LOCATIONS = "locations"
MONSTERS = "monsters"
NOTES = "notes"
SCENES = "scenes"

KINDS = (CHARACTERS, NPCS, LOCATIONS, MONSTERS, NOTES, SCENES)

# Template used for a fresh store; load_data() backfills any missing keys.
DEFAULT_DATA = {kind: [] for kind in KINDS}

# Shared filter string for image file dialogs.
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"

# Defaults and fallbacks shared across the UI.
DEFAULT_ENTITY_COLOR = "#888888"
HINT_TEXT_COLOR = "#6b6f78"
TOKEN_BORDER_COLOR = "#141414"
CANVAS_BACKGROUND = "#1f1f1f"
CANVAS_GRID_COLOR = "#333333"
TOKEN_DIAMETER = 46


def new_id() -> str:
    """Generate a short, collision-free record id."""
    return uuid.uuid4().hex[:12]
