# Hexlog TODO — solo play features

Priority-ordered feature ideas for solo play, to review and decide on later.

## 1. Oracle / Yes-No (highest priority)
A Mythic-style oracle dialog: type a question, set odds (impossible -> certain),
get a roll plus a twist/flawed-result table. Turns Hexlog from a tracker into a
game engine.

## 2. Built-in dice roller that logs to the journal
Support notation like `2d6+1`, advantage/disadvantage, and "insert result into
note" so rolls stay in the session record.

## 3. Editable random tables
NPC names, encounters, loot, towns, quest hooks, weather. Make rolls able to
output existing data (e.g. encounter roll -> spawn a monster token on the VTT).

## 4. Combat tracker wired into the VTT
Solo combat is the most bookkeeping-heavy part. Turn order + HP/conditions,
seeded from scene tokens and monster statblocks (CR/HP already in the data model).

## 5. Progress clocks / quest tracking
Track goals as ticking clocks (Blades-in-the-Dark style). Visual countdowns
keep sessions directed; fits the autosave model.

## 6. "What do I know about X?" summary
`@mention` references are already tracked per note. Select an entity and see
every note it appears in, compiled into a timeline. Solo players lose track of
threads between sessions.

## 7. Session recap generator
Group today's notes (timestamps already autosave) into a readable recap for
reopening a campaign weeks later.

---

# Code quality / security / performance fixes

From a full codebase review (Aug 2026). Priority-ordered; all pure-quality
items are quick wins.

## 1. Preserve corrupt data files (data safety)
`hexlog/storage.py` `load_data()`: if both `data.json` and `.bak` are corrupt or
missing, the app starts empty and the next autosave overwrites the corrupt
files. Fix: copy the unreadable file to `data.json.corrupt` before falling
through, and surface a warning to the user.

## 2. Debounce journal highlighting and reference scan (performance)
`hexlog/ui/notes.py`: every keystroke runs `rehighlight()` (recompiles every
entity regex, scans full text) plus `referenced_ids()` (3 full-text scans).
O(text x entities) per keystroke; stutters on long notes + many entities.
Fix: short QTimer debounce (150-300 ms), cache compiled patterns (rebuild only
when entities change), and recompute `referenced_ids` only on autosave.

## 3. Cache VTT pixmaps (performance)
`hexlog/ui/vtt.py` `refresh_scene_view()` re-creates QPixmaps for the map and
every token on each tab switch. Fix: cache by file path/name so tab-switching
is instant on large maps.

## 4. Handle save failures gracefully
`hexlog/ui/main_window.py` `_flush()` calls `store.save()` with no try/except;
a disk-full/permission error raises inside the Qt timer slot with no feedback.
Fix: wrap in try/except and show a status-bar message.

## 5. Set PlainText on confirm dialogs (security hygiene)
Entity names interpolated into `QMessageBox.question()` use Qt's default
AutoText format, so a name containing `<...>` renders as HTML. Fix: set
`Qt.PlainText` (or `Qt.MarkdownText`) on delete-confirmation dialogs.

## 6. Validate images on import
`hexlog/ui/entities.py` `_pick_image()` copies whatever filename the dialog
matched without checking it decodes as an image. Fix: load with `QPixmap` and
reject + report immediately if null.

## 7. Prune orphaned files
Deleting an entity/scene or clearing an image never removes the copied file
from `TOKENS_DIR`/`MAPS_DIR`. Fix: prune-on-startup — delete files not
referenced by any record.

## 8. Verify dialogue insertion caret
`hexlog/ui/notes.py` `_insert_dialogue()` relies on Qt syncing the widget
cursor to a `textCursor()` copy, which is version-dependent. Fix: reuse one
cursor and call `setTextCursor()` at the end; add a manual test.

## 9. Cosmetic color drift
`hexlog/ui/entities.py` new-form color uses `DEFAULT_ENTITY_COLOR` while
`_ensure()` picks via `next_color()`; the form shows a color that never matches
the saved one. Fix: show `next_color()` in the blank form.

## 10. Revisit full-file JSON rewrite
Whole store rewritten on each 600 ms autosave. Fine at current scale; revisit
only if the journal grows to multi-MB.

---

# Release & versioning

Current process: bump `__version__` in `hexlog/__init__.py` -> commit "Bump
version to X.Y.Z" -> annotated tag `vX.Y.Z` -> build AppImage via `./package.sh`
-> upload assets to a GitHub release manually.

## Versioning policy (SemVer, pre-1.0)
- **PATCH (0.4.1)** — bug fixes, small polish, performance fixes.
- **MINOR (0.5.0)** — new features and breaking changes (oracle, dice roller, etc.).
- **MAJOR (1.0)** — first stable release; breaking changes bump MAJOR after 1.0.
- **Pre-releases** — `0.5.0-rc1` / `0.5.0-beta.1`, marked "pre-release" on GitHub
  so `/releases/latest` stays stable.

Two hard rules:
1. Version lives in exactly one place (`hexlog/__init__.py`); pyproject.toml and
   package.sh already read it from there.
2. Tag always equals `__version__` (e.g. tag `v0.5.0` on the bump commit).

## Planned automation
- **GitHub Actions release workflow**: trigger on tag push `v*`, build the
  AppImage on CI, `gh release create v0.5.0 <appimage> --generate-notes`.
  Replaces manual package.sh + upload, and guarantees the binary matches the tag.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`) so notes can be generated
  from `git log`.
- **Optional later**: `setuptools-scm` to derive `__version__` from tags and drop
  the manual bump commit.

---

# Recommended order — what to tackle first

Ties all three sections together. Do the phases in order; anything "deferred"
is low-value until a specific trigger hits.

## Phase 0 — Versioning policy (5 min, no code)
Adopt the SemVer rules + tag rule above. Document in the repo (this file).

## Phase 1 — Data-safety and correctness quick wins (one session)
Small, high-value, protect an existing campaign:
1. Preserve corrupt data files (code review #1)
2. Handle save failures gracefully (code review #4)
3. PlainText on confirm dialogs (code review #5)
4. Verify dialogue insertion caret (code review #8)
5. Cosmetic color drift (code review #9)

## Phase 2 — Performance for everyday solo play
6. Debounce journal highlighting + reference scan (code review #2)
7. Cache VTT pixmaps (code review #3)

## Phase 3 — Release automation
8. GitHub Actions release workflow (versioning section) — then release 0.5.0.

## Phase 4 — Solo-play features (the reason the app exists)
9. Oracle / Yes-No dialog (solo feature #1)
10. Dice roller that logs to the journal (solo feature #2)
11. Then work down the remaining solo features (combat tracker, clocks, etc.).

## Deferred (only when triggered)
- Validate images on import (#6) — when an import bug actually bites.
- Prune orphaned files (#7) — when storage growth is felt.
- Revisit full-file JSON rewrite (#10) — when the journal approaches multi-MB.
- setuptools-scm (#3 under versioning) — when manual bumps feel like friction.
