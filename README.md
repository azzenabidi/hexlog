# Hexlog

A solo RPG companion for D&D-style play — manage characters, NPCs, locations, monster statblocks, a journal, and a virtual tabletop (VTT) with draggable tokens.

![PySide6](https://img.shields.io/badge/PySide6-%3E%3D6.6-41cd52)

## Features

- **Characters** — name, race, class, description, and an optional image used as a circular token on maps.
- **NPCs** — same as characters but with a role, plus dashed-outline map tokens so they stand out.
- **Locations** — name, type, and description; easily referenced in the journal.
- **Monsters** — statblock reference: name, CR, an optional link, and written details (AC, HP, speed, abilities, traits/actions).
- **Journal** — session notes with one-click dialogue and `@mention` insertion; character/NPC/location names are highlighted inline and references are tracked per note.
- **VTT** — load a battle/area map image, drop character and NPC tokens on it, drag them around, and save the scene.

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
  data.json   # characters, NPCs, locations, monsters, notes, scenes
  maps/       # map images copied here
  tokens/     # uploaded character/NPC token images copied here
```

On first run it automatically imports data saved by older builds that lived in `~/.solo_dnd/` (then keeps using `~/.hexlog/` going forward).

## Usage notes

- On the VTT tab: click a character or NPC in the dropdown, press **Add Token To Map**, then click the map to place it.
- Right-click a token to remove it; drag to reposition. Press **Save Scene** to persist token positions.
- `+` / `-` zoom, **Fit** to fit the map in the view.
