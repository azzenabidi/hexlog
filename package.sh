#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="hexlog"
PYTHON_MAJOR="3.12"
ARCH="$(uname -m)"

BUILD_DIR="build"
DIST_DIR="dist"
CACHE_DIR="$BUILD_DIR/cache"
APPDIR="$BUILD_DIR/AppDir"
TOOL_DIR="$BUILD_DIR/tools"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

info() { printf '\033[1;34m==> %s\033[0m\n' "$*"; }

if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to build an AppImage" >&2
    exit 1
fi

VERSION="$("$PYTHON_BIN" - <<'PY'
import re
text = open("hexlog/__init__.py", encoding="utf-8").read()
print(re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1))
PY
)"

info "Building $APP_NAME $VERSION for $ARCH as an AppImage"
mkdir -p "$CACHE_DIR" "$TOOL_DIR" "$DIST_DIR"

# ---------------------------------------------------------------------------
# 1. Python runtime (python-build-standalone)
# ---------------------------------------------------------------------------
PBS_URL="$("$PYTHON_BIN" packaging/pbs.py "$PYTHON_MAJOR" "$ARCH")"
PBS_TARBALL="$CACHE_DIR/${PBS_URL##*/}"
if [ ! -f "$PBS_TARBALL" ]; then
    info "Downloading python-build-standalone runtime"
    curl -fL --retry 3 -o "$PBS_TARBALL" "$PBS_URL"
fi

# ---------------------------------------------------------------------------
# 2. Assemble the AppDir
# ---------------------------------------------------------------------------
info "Assembling AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" \
         "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/icons/hicolor/512x512/apps"

info "Extracting Python runtime"
tar -xzf "$PBS_TARBALL" -C "$APPDIR/usr" --strip-components=1

info "Installing $APP_NAME and Python dependencies"
"$APPDIR/usr/bin/python3" -m pip install --no-cache-dir --quiet .

# ---------------------------------------------------------------------------
# 3. Icon, desktop entry and launcher
# ---------------------------------------------------------------------------
info "Rendering icon"
QT_QPA_PLATFORM=offscreen "$APPDIR/usr/bin/python3" packaging/make_icon.py "$BUILD_DIR/icon"
cp "$BUILD_DIR/icon/hexlog-256.png" "$APPDIR/hexlog.png"
cp "$BUILD_DIR/icon/hexlog-256.png" "$APPDIR/.DirIcon"
cp "$BUILD_DIR/icon/hexlog-256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/hexlog.png"
cp "$BUILD_DIR/icon/hexlog-512.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/hexlog.png"

cp packaging/hexlog.desktop "$APPDIR/hexlog.desktop"
cp packaging/hexlog.desktop "$APPDIR/usr/share/applications/hexlog.desktop"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export HEXLOG_ENV=prod
exec "$HERE/usr/bin/python3" -m hexlog "$@"
EOF
chmod +x "$APPDIR/AppRun"
ln -sf AppRun "$APPDIR/hexlog"

# ---------------------------------------------------------------------------
# 4. Build the AppImage
# ---------------------------------------------------------------------------
APPIMAGETOOL="$TOOL_DIR/appimagetool"
if [ ! -x "$APPIMAGETOOL" ]; then
    info "Downloading appimagetool"
    curl -fL --retry 3 -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

OUTPUT="$DIST_DIR/$APP_NAME-$VERSION-$ARCH.AppImage"
info "Building AppImage"
APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" --no-appstream "$APPDIR" "$OUTPUT"

info "Done: $OUTPUT"
