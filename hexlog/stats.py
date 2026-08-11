"""Static codebase statistics for the Help > Nerd Stats dialog."""

import importlib.metadata
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
TESTS_DIR = PACKAGE_DIR.parent / "tests"

_CLASS_RE = re.compile(r"^\s*class\s+\w+")
_DEF_RE = re.compile(r"^\s*def\s+\w+")
_TEST_FN_RE = re.compile(r"^\s*(?:async\s+)?def\s+test_\w+")
_TEST_CLASS_RE = re.compile(r"^\s*class\s+Test\w+")
_NON_CODE_RE = re.compile(r"^\s*(#.*)?$")


@dataclass
class Stats:
    """Aggregated codebase counters shown in the Nerd Stats dialog."""

    lines: int = 0
    modules: int = 0
    classes: int = 0
    functions: int = 0
    test_functions: int = 0
    test_classes: int = 0
    external_packages: int = 0


def _py_files(root):
    """All .py files under root, sorted, skipping dot-directories."""
    files = (p for p in root.rglob("*.py") if not any(part.startswith(".") for part in p.parts))
    return sorted(files)


def external_package_count():
    """Number of installed packages that aren't Python stdlib modules."""
    stdlib = frozenset(sys.stdlib_module_names)
    count = 0
    for dist in importlib.metadata.distributions():
        name = (dist.metadata.get("Name") or "").lower().replace("_", "-")
        if name and name not in stdlib and name != "hexlog":
            count += 1
    return count


def _count_file(stats, path, counted):
    """Tally one Python file into `stats`; test counts only apply to tests."""
    if counted:
        stats.modules += 1
    for line in path.read_text(encoding="utf-8").splitlines():
        if not _NON_CODE_RE.match(line):
            stats.lines += 1
        if _CLASS_RE.match(line):
            stats.classes += 1
        if _DEF_RE.match(line):
            stats.functions += 1
        if not counted and _TEST_FN_RE.match(line):
            stats.test_functions += 1
        if not counted and _TEST_CLASS_RE.match(line):
            stats.test_classes += 1


def collect_stats(package_dir=None, tests_dir=None):
    """Count lines, modules, classes, functions, tests, and external packages."""
    package_dir = Path(package_dir or PACKAGE_DIR)
    tests_dir = Path(tests_dir or TESTS_DIR)
    stats = Stats()

    for root, counted in ((package_dir, True), (tests_dir, False)):
        if root.exists():
            for path in _py_files(root):
                _count_file(stats, path, counted)

    stats.external_packages = external_package_count()
    return stats
