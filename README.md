# Hexlog

A solo RPG companion for D&D-style play. Manage characters, NPCs, locations,
monster statblocks, a journal, and a virtual tabletop (VTT) with draggable
tokens.

![PySide6](https://img.shields.io/badge/PySide6-%3E%3D6.6-41cd52)
![CI](https://img.shields.io/github/actions/workflow/status/azzenabidi/hexlog/python-app.yml)

## Features

- **Characters**: name, race, class, description, and an optional image used
  as a circular token on maps.
- **NPCs**: like characters, plus a role and dashed-outline map tokens that
  stand out from player tokens.
- **Locations**: name, type, and description; easily referenced in the
  journal.
- **Monsters**: statblock reference with name, CR, an optional link, and
  written details (AC, HP, speed, abilities, traits/actions).
- **Journal**: session notes with dialogue and `@mention` insertion, inline
  name highlighting, and built-in dice for the common RPG notations. The
  **What do I know?** button shows every note that names a character, NPC,
  location, or monster, presented as a timeline.
- **VTT**: organize maps into named scenes, load a battle or area map image,
  and drop character and NPC tokens on it. Drag to reposition or pull the
  corner handle to resize; positions and sizes autosave. A built-in
  **combat tracker** runs initiative, hit points, and conditions.
- **Oracle**: a solo-play oracle in the Tools menu, with answers you can log
  straight into the journal.
- **Updates**: **Check for Updates** in the Help menu finds a newer build,
  downloads it, and relaunches Hexlog in place.
- **Theme toggle**: switch between dark and light themes from the toolbar.
- **Nerd Stats**: Help ▸ Nerd Stats shows codebase trivia: lines of code,
  modules, classes, test cases, and external packages.

## Requirements

- Python 3.10+
- [PySide6](https://pypi.org/project/PySide6/) >= 6.6

## Getting started

For local development:

```bash
./run.sh
```

`run.sh` creates a virtual environment and installs dependencies on first
use.

## Install the AppImage

Download the latest AppImage from the
[releases page](https://github.com/azzenabidi/hexlog/releases). The bundled
installer copies it to `~/.local/bin/hexlog` and registers it in your
application menu:

```bash
./install.sh ~/Downloads/hexlog-*.AppImage
```

Or skip the installer and run the AppImage directly:

```bash
chmod +x hexlog-*.AppImage
./hexlog-*.AppImage
```

No Python or PySide6 installation is required; the AppImage bundles
everything. Once installed, the **Check for Updates** entry in the Help menu
offers and applies future releases without touching a terminal.

## Data storage

Hexlog follows the XDG convention and stores everything under
`~/.config/hexlog/`. Local development uses the `dev` copy, while the
packaged AppImage release uses `prod`, so the two never share data:

```
~/.config/hexlog/
  dev/ or prod/
    data.json   # characters, NPCs, locations, monsters, notes, scenes
    maps/       # map images copied here
    tokens/     # uploaded character/NPC token images copied here
```

On first run Hexlog creates the active subdirectory fresh; data from older
releases (which lived in `~/.hexlog/`) is moved in automatically.

## Usage

- Everything autosaves as you type or drag; there are no Save buttons.
  `Ctrl+N` starts a new record. Right-click a list for New/Delete (or press
  `Delete` while a list is focused).
- On the VTT tab: create a scene, pick a character or NPC in the dropdown,
  press **Add Token To Map**, then click the map to place it. Right-click
  cancels a pending placement.
- Drag a token to reposition, or drag its corner handle to resize; both
  autosave. Right-click a token to remove it.
- Right-click the scene list for New/Rename/Delete (or press `Delete` while
  it is focused).
- `+` / `-` zoom; **Fit** fits the map in the view.
- To run combat: place the tokens you want on the map, then press
  **Start Combat** in the tracker below. **Next Turn** cycles to the next
  combatant by initiative; **- HP** / **+ HP** adjust the selected token's
  hit points, and **Toggle** adds or removes a condition.
- In the Journal, pick a character, NPC, location, or monster from the
  dropdown and press **What do I know?** to read every note that mentions
  it, oldest first.
- **Tools ▸ Oracle** answers solo-play questions; **Log to journal** drops
  the answer into the current note.

## License

Hexlog is released under the [MIT License](LICENSE).
