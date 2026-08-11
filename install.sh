#!/usr/bin/env bash
# Install Hexlog into the current user's local app folders.
#
# Usage:  ./install.sh [path/to/hexlog-*.AppImage]
#
# Without an argument it picks the newest hexlog-*.AppImage from the current
# directory or ~/Downloads. The AppImage is installed as ~/.local/bin/hexlog
# and a launcher (.desktop file) plus an app icon are added under
# ~/.local/share/ so it shows up in the application menu. The install uses a
# temp-file rename, so it also works while Hexlog is currently running.
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="hexlog"
BIN_DIR="${HOME}/.local/bin"
TARGET="$BIN_DIR/hexlog"
APPS_DIR="${HOME}/.local/share/applications"
ICON_256_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
ICON_512_DIR="${HOME}/.local/share/icons/hicolor/512x512/apps"

info() { printf '\033[1;34m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mError: %s\033[0m\n' "$*" >&2; exit 1; }

# --- Locate the AppImage ------------------------------------------------
SOURCE="${1:-}"
if [ -z "$SOURCE" ]; then
    for dir in "$PWD" "$HOME/Downloads"; do
        candidate="$(ls -t "$dir"/hexlog-*.AppImage 2>/dev/null | head -n1 || true)"
        if [ -n "$candidate" ]; then
            SOURCE="$candidate"
            break
        fi
    done
fi
[ -n "$SOURCE" ] || die "no AppImage found; pass one explicitly: ./install.sh /path/to/hexlog-*.AppImage"
[ -f "$SOURCE" ] || die "AppImage not found: $SOURCE"

# --- Install the binary ---------------------------------------------------
info "Installing $(basename "$SOURCE")"
mkdir -p "$BIN_DIR"
chmod +x "$SOURCE"
cp "$SOURCE" "$BIN_DIR/.$APP_NAME.new"
mv -f "$BIN_DIR/.$APP_NAME.new" "$TARGET"

# --- Launcher entry and icon ----------------------------------------------
mkdir -p "$APPS_DIR" "$ICON_256_DIR" "$ICON_512_DIR"
info "Installing desktop entry and icon"

icon_installed=false
extract_dir="$(mktemp -d)"
if ( cd "$extract_dir" && "$SOURCE" --appimage-extract "$APP_NAME.png" >/dev/null 2>&1 \
        && [ -f "$extract_dir/squashfs-root/$APP_NAME.png" ] ); then
    cp "$extract_dir/squashfs-root/$APP_NAME.png" "$ICON_256_DIR/$APP_NAME.png"
    cp "$extract_dir/squashfs-root/$APP_NAME.png" "$ICON_512_DIR/$APP_NAME.png"
    icon_installed=true
fi
rm -rf "$extract_dir"

cat > "$APPS_DIR/$APP_NAME.desktop" <<EOF
[Desktop Entry]
Name=Hexlog
Comment=Solo RPG companion for D&D-style play
Exec=$TARGET
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=Game;RolePlaying;
EOF

if [ "$icon_installed" = false ]; then
    info "Could not extract the icon; the launcher will use a generic icon."
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
fi

# --- Wrap up ---------------------------------------------------------------
echo
info "Installed: $TARGET"
info "Launch Hexlog from your application menu, or run '$TARGET'."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    info "Add $BIN_DIR to your PATH to run 'hexlog' from a terminal."
fi
