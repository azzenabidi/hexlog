#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python executable '$PYTHON_BIN' not found" >&2
    exit 1
fi

if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sysconfig
import ctypes.util
print(sysconfig.get_config_var('LDLIBRARY') or '')
print(ctypes.util.find_library('python3.12') or '')
PY
then
    echo "The selected Python runtime does not expose a shared library required by PyInstaller." >&2
    exit 1
fi

"$PYTHON_BIN" -m pip install --user --break-system-packages -r requirements.txt

exec "$PYTHON_BIN" -m PyInstaller --noconfirm --clean --distpath dist --workpath build hexlog.spec "$@"
