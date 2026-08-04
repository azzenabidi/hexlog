# Hexlog

A solo RPG companion for D&D-style play — manage characters, NPCs, a journal, and map scenes with draggable tokens.

![PySide6](https://img.shields.io/badge/PySide6-%3E%3D6.6-41cd52)

## Features

- **Characters** — name, race, class, description, and a token color for maps.
- **NPCs** — same as characters but with a role, plus dashed-outline map tokens so they stand out.
- **Journal** — session notes with one-click dialogue and `@mention` insertion; character/NPC names are highlighted inline and references are tracked per note.
- **Maps & Scenes** — load a battle/area map image, drop character and NPC tokens on it, drag them around, and save the scene.

## Requirements

- Python 3.10+
- [PySide6](https://pypi.org/project/PySide6/) >= 6.6

## Run

```bash
./run.sh
```

`run.sh` creates a virtual environment and installs dependencies on first use.

## Data storage

Hexlog stores everything in `~/.hexlog/`:

```
~/.hexlog/
  data.json   # characters, NPCs, notes, scenes
  maps/       # map images copied here
```

On first run it automatically imports data saved by older builds that lived in `~/.solo_dnd/` (then keeps using `~/.hexlog/` going forward).

## Usage notes

- On the Maps tab: click a character/NPC in the dropdown, press **Add Token To Map**, then click the map to place it.
- Right-click a token to remove it; drag to reposition. Press **Save Scene** to persist token positions.
- `+` / `-` zoom, **Fit** to fit the map in the view.
