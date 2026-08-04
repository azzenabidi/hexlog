# AGENTS.md

Guidance for AI coding agents working on Hexlog.

## Project overview

Hexlog is a solo RPG companion: a PySide6 desktop app for characters, NPCs,
locations, monster statblocks, a journal, and a lightweight VTT with draggable
tokens. Data is persisted as JSON under `~/.hexlog/`. There are no save buttons
— every edit autosaves through a debounced timer in `MainWindow`.

## Commands

```bash
./run.sh               # create venv if needed, then launch the app
./package.sh           # build a distributable PyInstaller app into dist/
.venv/bin/python -m pytest          # run the test suite
.venv/bin/flake8 .                  # lint (CI uses this, see below)
```

- Lint must pass flake8: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`
  (errors are fatal in CI) plus `flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127`.
- Tests must pass with `pytest`. Tests never instantiate a GUI; they target the
  pure layers (`storage`, `theme`) and monkeypatch `constants` paths.
- Always run lint and the full test suite before considering a change complete.

## Architecture

- `hexlog/constants.py` — app-wide constants; storage paths and JSON keys live
  here, not scattered through the app.
- `hexlog/storage.py` — the only module that touches disk. `Store` is the single
  data model shared by every tab; `Store.save()` persists everything.
- `hexlog/ui/` — one module per tab (`entities`, `notes`, `vtt`) plus `theme.py`
  and `main_window.py`. Tabs receive `(store, on_change)` and never persist
  directly; they call `on_change()` to schedule a save.
- `hexlog/ui/entities.py` — `EntityTab`, a generic CRUD tab subclassed for
  characters, NPCs, locations, and monsters.
- `tests/` — pytest tests with an `isolated_paths` fixture that redirects
  storage paths to a tmp dir via monkeypatch.

## Coding conventions

- Python 3.10+, PySide6 >= 6.6. No third-party deps beyond PySide6 and PyInstaller.
- Style: PEP 8, 127-column lines, complexity <= 10 (enforced by CI's flake8).
- Imports use absolute package paths: `from hexlog import constants as C`.
- Module-level docstrings describe what the module owns. Public classes and
  methods get a short docstring; private helpers usually skip one.
- Do NOT add code comments unless they explain a non-obvious decision
  (see `load_data()` in storage.py for the pattern).
- No type hints in UI code; light hints are fine in storage/constants.
- Guard against data-shape drift: when adding a field, backfill it in
  `load_data()` rather than assuming old JSON files match.

## PySide6 pitfalls (important)

- In PySide6 6.11 `QAction` moved from `QtWidgets` to `QtGui`. Import it as
  `from PySide6.QtGui import QAction`. Check what version is in `.venv`
  (`PYSIDE6_VERSION` from `PySide6.QtCore`) before assuming API locations.
- GUI code cannot run in headless CI; keep new logic testable without a QApplication.

## Do / don't

- Do: add tests for any new logic in storage or theme; reuse `isolated_paths`.
- Do: put new tunables (colors, delays, keys) in `constants.py`.
- Don't: add save buttons or direct disk I/O inside tabs.
- Don't: introduce new top-level JSON keys without updating `C.KINDS` and
  `DEFAULT_DATA`, and backfill in `load_data()`.
