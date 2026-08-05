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
