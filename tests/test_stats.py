"""Tests for the codebase statistics module."""

from hexlog.stats import Stats, collect_stats


def _write_tree(root):
    package = root / "hexlog"
    package.mkdir()
    (package / "__init__.py").write_text("VALUE = 1\n")
    (package / "widget.py").write_text(
        "class Widget:\n"
        "    def render(self):\n"
        "        return 1\n"
        "\n"
        "def helper():\n"
        "    pass\n"
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_widget.py").write_text(
        "def test_render():\n"
        "    assert True\n"
        "class TestWidget:\n"
        "    def test_other(self):\n"
        "        pass\n"
    )


def test_collect_stats_counts_source(tmp_path):
    _write_tree(tmp_path)
    stats = collect_stats(package_dir=tmp_path / "hexlog", tests_dir=tmp_path / "tests")
    assert stats.modules == 2
    assert stats.classes == 2
    assert stats.functions == 4
    assert stats.test_functions == 2
    assert stats.test_classes == 1
    assert stats.lines == 11


def test_collect_stats_skips_blank_and_comment_lines(tmp_path):
    (tmp_path / "hexlog").mkdir()
    (tmp_path / "hexlog" / "mod.py").write_text("# header\n\n\nx = 1\n   # trailing\n")
    stats = collect_stats(package_dir=tmp_path / "hexlog", tests_dir=tmp_path / "missing")
    assert stats.lines == 1


def test_collect_stats_counts_external_packages(tmp_path, monkeypatch):
    (tmp_path / "hexlog").mkdir()
    (tmp_path / "hexlog" / "mod.py").write_text("x = 1\n")
    monkeypatch.setattr("hexlog.stats.external_package_count", lambda: 42)
    stats = collect_stats(package_dir=tmp_path / "hexlog", tests_dir=tmp_path / "missing")
    assert stats.external_packages == 42


def test_stats_defaults():
    assert Stats().lines == 0
    assert Stats().modules == 0
