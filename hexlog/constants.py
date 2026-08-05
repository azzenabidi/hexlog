"""App-wide constants: names, paths, and shared defaults.

Paths follow the XDG convention: data lives under ~/.config/hexlog/ with a
dev copy for local development and a prod copy for the packaged AppImage. The
persistence layer in storage.py is the only module that reads and writes these
locations.
"""

import os
import uuid

APP_NAME = "Hexlog"
# Project homepage used in the About dialog.
GITHUB_URL = "https://github.com/azzenabidi/hexlog"


def data_subdir(environ=None) -> str:
    """Return the data directory name for this run: "prod" in an AppImage, else "dev".

    The AppImage runtime exports $APPIMAGE; anything else is treated as local
    development. HEXLOG_ENV (set by the packaged AppRun) overrides detection.
    """
    env = os.environ if environ is None else environ
    override = env.get("HEXLOG_ENV")
    if override in ("dev", "prod"):
        return override
    return "prod" if env.get("APPIMAGE") else "dev"


def config_root_dir(environ=None) -> str:
    """Return the base config directory: $XDG_CONFIG_HOME or ~/.config."""
    env = os.environ if environ is None else environ
    return env.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")


# App data lives under the user's config dir (~/.config/hexlog) so it follows
# the XDG convention. Local development uses a dev copy; the packaged AppImage
# release uses prod. LEGACY_DATA_DIR points at the pre-0.3.3 location.
APP_CONFIG_DIR = os.path.join(config_root_dir(), "hexlog")
DATA_SUBDIR = data_subdir()
DATA_DIR = os.path.join(APP_CONFIG_DIR, DATA_SUBDIR)
DATA_FILE = os.path.join(DATA_DIR, "data.json")
# Map images are copied here; scenes reference them by basename only.
MAPS_DIR = os.path.join(DATA_DIR, "maps")
# Character/NPC token images are copied here for the same reason.
TOKENS_DIR = os.path.join(DATA_DIR, "tokens")
LEGACY_DATA_DIR = os.path.join(os.path.expanduser("~"), ".hexlog")

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
SELECTION_COLOR = "#6c7cff"
TOKEN_DIAMETER = 46
TOKEN_MIN_DIAMETER = 12
TOKEN_MAX_DIAMETER = 256
ERROR_COLOR = "#e74c3c"


def new_id() -> str:
    """Generate a short, collision-free record id."""
    return uuid.uuid4().hex[:12]
