# Hexlog

A solo RPG companion for D&D-style play — manage characters, NPCs, locations, monster statblocks, a journal, and a virtual tabletop (VTT) with draggable tokens.

![PySide6](https://img.shields.io/badge/PySide6-%3E%3D6.6-41cd52)
![CI](https://img.shields.io/github/actions/workflow/status/azzenabidi/hexlog/python-app.yml)

## Features

- **Characters** — name, race, class, description, and an optional image used as a circular token on maps.
- **NPCs** — same as characters but with a role, plus dashed-outline map tokens so they stand out.
- **Locations** — name, type, and description; easily referenced in the journal.
- **Monsters** — statblock reference: name, CR, an optional link, and written details (AC, HP, speed, abilities, traits/actions).
- **Journal** — session notes with dialogue and `@mention` insertion; character/NPC/location names are highlighted inline and references are tracked per note.
- **VTT** — load a battle/area map image, drop character and NPC tokens on it, drag them around. Token positions autosave.
- **Theme toggle** — switch between dark and light themes from the toolbar at runtime.

## Requirements

- Python 3.10+
- [PySide6](https://pypi.org/project/PySide6/) >= 6.6

## Run

For local development:

```bash
./run.sh
```

`run.sh` creates a virtual environment and installs dependencies on first use.

For packaging a distributable desktop app as an AppImage:

```bash
./package.sh
```

This bundles a self-contained Python runtime ([python-build-standalone](https://github.com/astral-sh/python-build-standalone)), the app and its PySide6 dependencies, and produces `dist/hexlog-<version>-<arch>.AppImage`. Just download that file, make it executable, and run it:

```bash
chmod +x dist/hexlog-*.AppImage
./dist/hexlog-*.AppImage
```

The build downloads the Python runtime and `appimagetool` once and caches them under `build/`.

## Data storage

Hexlog stores everything in `~/.hexlog/`:

```
~/.hexlog/
  data.json   # characters, NPCs, locations, monsters, notes, scenes
  maps/       # map images copied here
  tokens/     # uploaded character/NPC token images copied here
```

On first run Hexlog creates `~/.hexlog/` fresh; it never imports data from any other location.

## Usage notes

- Everything autosaves as you type or drag - there are no Save buttons. `Ctrl+N` starts a new record; right-click a list for New/Delete (or press `Delete` while a list is focused).
- On the VTT tab: click a character or NPC in the dropdown, press **Add Token To Map**, then click the map to place it. Positions are saved automatically.
- Right-click a token to remove it; drag to reposition.
- `+` / `-` zoom, **Fit** to fit the map in the view.
