"""Tests for the self-update engine. No GUI or network required."""

import json
import os

import pytest

from hexlog import constants as C
from hexlog.updater import (
    appimage_path,
    download_to,
    format_size,
    is_newer,
    latest_release,
    load_and_clear_release_notes,
    parse_version,
    replace_appimage,
    restart_command,
    save_release_notes,
)


class FakeResponse:
    """A minimal file-like HTTP response with a headers mapping."""

    def __init__(self, data=b"", content_length=None):
        self._data = data
        self._offset = 0
        total = content_length if content_length is not None else len(data)
        self.headers = {"Content-Length": str(total)}

    def read(self, n=-1):
        if n < 0 or n > len(self._data) - self._offset:
            n = len(self._data) - self._offset
        chunk = self._data[self._offset:self._offset + n]
        self._offset += len(chunk)
        return chunk


class FakeOpener:
    """A urlopen stand-in returning a canned response per URL."""

    def __init__(self, response, urls=None):
        self.response = response
        self.urls = urls if urls is not None else []

    def __call__(self, url):
        self.urls.append(url)
        return self.response


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Point the updater's notes stash at a throwaway directory."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr(C, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(C, "RELEASE_NOTES_FILE", str(data_dir / "release-notes.txt"))


def test_parse_version_normalizes_tags():
    assert parse_version("v0.5.0") == (0, 5, 0)
    assert parse_version("0.5.0") == (0, 5, 0)
    assert parse_version("v1.10.2") == (1, 10, 2)


def test_parse_version_rejects_garbage():
    with pytest.raises(ValueError):
        parse_version("latest")


def test_is_newer_compares_tuples():
    assert is_newer("v0.6.0", "0.5.0")
    assert not is_newer("v0.5.0", "0.5.0")
    assert not is_newer("v0.4.2", "0.5.0")


def test_latest_release_finds_the_appimage_asset():
    payload = {
        "tag_name": "v0.5.0",
        "name": "Hexlog 0.5.0",
        "body": "What's new.",
        "published_at": "2026-08-11T09:00:00Z",
        "html_url": "https://example.test/releases/v0.5.0",
        "assets": [
            {"name": "hexlog-0.5.0-x86_64.AppImage",
             "browser_download_url": "https://example.test/hexlog-0.5.0.AppImage",
             "size": 90_000_000},
        ],
    }
    opener = FakeOpener(FakeResponse(json.dumps(payload).encode()))
    release = latest_release("https://api.example.test/latest", opener)
    assert opener.urls == ["https://api.example.test/latest"]
    assert release.tag == "v0.5.0"
    assert release.name == "Hexlog 0.5.0"
    assert release.notes == "What's new."
    assert release.published_at == "2026-08-11T09:00:00Z"
    assert release.html_url == "https://example.test/releases/v0.5.0"
    assert release.appimage_url == "https://example.test/hexlog-0.5.0.AppImage"
    assert release.size == 90_000_000


def test_latest_release_defaults_missing_metadata():
    payload = {"tag_name": "v0.5.0", "body": "", "assets": []}
    release = latest_release(
        "https://api.example.test/latest", FakeOpener(FakeResponse(json.dumps(payload).encode()))
    )
    assert release.name == "v0.5.0"
    assert release.published_at == ""
    assert release.html_url == ""
    assert release.size == 0


def test_format_size_is_human_friendly():
    assert format_size(90 * 1024 * 1024) == "90 MB"
    assert format_size(5 * 1024 * 1024) == "5.0 MB"
    assert format_size(0) == "0.0 MB"


def test_latest_release_returns_none_without_an_appimage_asset():
    payload = {"tag_name": "v0.5.0", "body": "", "assets": []}
    release = latest_release("https://api.example.test/latest", FakeOpener(FakeResponse(json.dumps(payload).encode())))
    assert release is not None
    assert release.appimage_url is None


def test_latest_release_raises_on_unexpected_payload():
    opener = FakeOpener(FakeResponse(b"not json"))
    with pytest.raises(ValueError):
        latest_release("https://api.example.test/latest", opener)


def test_download_to_streams_and_reports_progress(tmp_path):
    dest = tmp_path / "new.AppImage"
    payload = b"x" * 200_000
    progress = []
    download_to("https://example.test/file", str(dest),
                FakeOpener(FakeResponse(payload)),
                lambda received, total: progress.append((received, total)))
    assert dest.read_bytes() == payload
    assert progress[-1] == (200_000, 200_000)
    assert progress[0][0] > 0


def test_download_to_raises_on_a_short_read(tmp_path):
    dest = tmp_path / "new.AppImage"
    response = FakeResponse(data=b"only some bytes", content_length=10_000)
    with pytest.raises(OSError):
        download_to("https://example.test/file", str(dest), FakeOpener(response))


def test_appimage_path_reads_the_environment():
    assert appimage_path({"APPIMAGE": "/opt/hexlog.AppImage"}) == "/opt/hexlog.AppImage"
    assert appimage_path({}) is None


def test_restart_command_targets_the_appimage():
    assert restart_command({"APPIMAGE": "/opt/hexlog.AppImage"}) == ["/opt/hexlog.AppImage"]


def test_replace_appimage_makes_executable_and_atomic(tmp_path):
    source = tmp_path / "new"
    target = tmp_path / "hexlog.AppImage"
    source.write_bytes(b"binary")
    replace_appimage(str(source), str(target))
    assert target.read_bytes() == b"binary"
    assert os.access(target, os.X_OK)


def test_save_and_load_clear_release_notes(isolated_paths):
    assert load_and_clear_release_notes() is None
    save_release_notes("What's new.")
    assert load_and_clear_release_notes() == "What's new."
    assert load_and_clear_release_notes() is None
