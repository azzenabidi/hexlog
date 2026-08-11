"""Self-update support for the packaged AppImage build.

When Hexlog runs from an AppImage ($APPIMAGE is set) it can ask the GitHub
releases API for a newer build, download the AppImage asset, and atomically
replace the running file: the AppImage runtime runs from a mounted copy, so
overwriting the original on disk is safe while it is executing. The new
binary is made executable, the applied release's notes are stashed in the
data dir for the relaunched app to show, and the caller is handed a restart
command. All network and file work lives here as plain functions so it can
be tested without Qt or a running app; the dialog owns the threads.
"""

import json
import os
import re
import urllib.request
from dataclasses import dataclass

from hexlog import __version__, constants as C

RELEASES_URL = "https://api.github.com/repos/azzenabidi/hexlog/releases/latest"

# A release asset name like "hexlog-0.5.0-x86_64.AppImage".
APPIMAGE_PATTERN = re.compile(r"hexlog-.*\.AppImage")
VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")

DOWNLOAD_CHUNK = 64 * 1024


def open_url(url):
    """Fetch a URL with a descriptive User-Agent and a timeout."""
    request = urllib.request.Request(
        url, headers={"User-Agent": f"Hexlog/{__version__}"}
    )
    return urllib.request.urlopen(request, timeout=30)


def parse_version(tag):
    """Normalize a release tag like "v0.5.0" into a comparable (0, 5, 0)."""
    match = VERSION_RE.search(tag)
    if not match:
        raise ValueError(f"Not a version tag: {tag!r}")
    return tuple(int(part) for part in match.groups())


def is_newer(tag, current):
    """True when the release `tag` is a later version than `current`."""
    return parse_version(tag) > parse_version(current)


@dataclass(frozen=True)
class Release:
    """The latest release as reported by the GitHub API."""

    tag: str
    name: str
    notes: str
    published_at: str
    html_url: str
    appimage_url: str | None
    size: int = 0


def latest_release(releases_url, opener):
    """Fetch the newest release and the URL of its AppImage asset.

    `opener` is any callable that returns a file-like response with .read()
    (urllib's urlopen works; tests pass a fake). Raises when the response is
    not a release, or returns None when the release has no AppImage asset.
    """
    payload = json.load(opener(releases_url))
    if not isinstance(payload, dict) or "tag_name" not in payload:
        raise ValueError(f"Unexpected releases response: {payload}")
    asset = next(
        (
            a for a in payload.get("assets", [])
            if APPIMAGE_PATTERN.search(a.get("name", ""))
        ),
        None,
    )
    return Release(
        payload["tag_name"],
        payload.get("name") or payload["tag_name"],
        payload.get("body", ""),
        payload.get("published_at", ""),
        payload.get("html_url", ""),
        asset.get("browser_download_url") if asset else None,
        int(asset.get("size") or 0) if asset else 0,
    )


def format_size(num_bytes):
    """Human-friendly download size like '89 MB'."""
    mb = num_bytes / (1024 * 1024)
    if mb < 10:
        return f"{mb:.1f} MB"
    return f"{int(round(mb))} MB"


def download_to(url, dest_path, opener, progress=None):
    """Stream `url` to `dest_path`, reporting (received, total) bytes.

    `opener` mirrors urllib.urlopen; the response must expose .read() and a
    headers mapping with an optional "Content-Length". Raises on a short
    read so a truncated download is never mistaken for a success.
    """
    response = opener(url)
    total = int(response.headers.get("Content-Length") or 0)
    received = 0
    with open(dest_path, "wb") as out:
        while True:
            chunk = response.read(DOWNLOAD_CHUNK)
            if not chunk:
                break
            out.write(chunk)
            received += len(chunk)
            if progress:
                progress(received, total)
    if total and received != total:
        raise OSError(f"Incomplete download: got {received} of {total} bytes")


def appimage_path(environ=None):
    """The on-disk path of the running AppImage, or None in a dev install."""
    env = os.environ if environ is None else environ
    return env.get("APPIMAGE")


def replace_appimage(new_file, target):
    """Make `new_file` executable and atomically move it over `target`."""
    os.chmod(new_file, 0o755)
    os.replace(new_file, target)


def restart_command(environ=None):
    """The command that relaunches the installed AppImage."""
    return [appimage_path(environ)]


def save_release_notes(text):
    """Stash release notes so the relaunched app can show them once."""
    os.makedirs(C.DATA_DIR, exist_ok=True)
    with open(C.RELEASE_NOTES_FILE, "w", encoding="utf-8") as out:
        out.write(text)


def load_and_clear_release_notes():
    """Return stashed release notes, removing the file, or None if absent."""
    if not os.path.exists(C.RELEASE_NOTES_FILE):
        return None
    with open(C.RELEASE_NOTES_FILE, encoding="utf-8") as source:
        notes = source.read()
    try:
        os.remove(C.RELEASE_NOTES_FILE)
    except OSError:
        pass
    return notes or None
