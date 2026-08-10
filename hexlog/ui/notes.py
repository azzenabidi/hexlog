"""Journal: notes with dialogue/@mention insertion and highlighting.

Notes save themselves as you type (debounced through on_change), so there is
no explicit Save button. A compact toolbar inserts dialogue or @mentions for
any character, NPC, or location.
"""

import re
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut, QTextCharFormat
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hexlog import constants as C
from hexlog.ui.dialogs import confirm


def mention_pattern(name):
    """Compile the word-boundary pattern used to match an entity name."""
    return re.compile(r"\b" + re.escape(name) + r"\b")


def dialogue_caret_offset(name):
    """Offset of the caret after inserting `\\nName: ""`: between the quotes."""
    return len(f"\n{name}: \"")


def referenced_ids(entities, text):
    """Ids of entities whose name appears in the note text (whole-word match).

    Uses the same word-boundary rule as MentionHighlighter so the stored
    references and the visual highlighting never disagree.
    """
    return [e["id"] for e in entities if e.get("name") and mention_pattern(e["name"]).search(text)]


class MentionHighlighter:
    """Colors entity names appearing in the journal editor.

    Uses QTextEdit.ExtraSelection, which overlays formatting without
    modifying the underlying document text, so highlighting is purely visual.
    Compiled patterns are cached by name so re-highlighting only pays for
    regex compilation when an entity is added or renamed.
    """

    def __init__(self, edit, get_entities):
        self.edit = edit
        self.get_entities = get_entities  # callback returns the current entity lists
        self.rules = []  # (compiled regex, color) pairs
        self._pattern_cache = {}

    def refresh(self):
        """(Re)build regex rules from the current entities, reusing cached patterns."""
        self.rules = []
        entities = self.get_entities()
        live_names = set()
        for entity in entities:
            name = entity.get("name", "")
            if not name:
                continue
            live_names.add(name)
            pattern = self._pattern_cache.get(name)
            if pattern is None:
                pattern = mention_pattern(name)
                self._pattern_cache[name] = pattern
            self.rules.append((pattern, entity.get("color", C.DEFAULT_ENTITY_COLOR)))
        # Drop cached patterns for names that no longer exist to bound memory.
        for name in list(self._pattern_cache):
            if name not in live_names:
                del self._pattern_cache[name]

    def rehighlight(self):
        """Re-scan the editor text and apply all matching highlights."""
        self.refresh()
        selections = []
        text = self.edit.toPlainText()
        for pattern, color in self.rules:
            for match in pattern.finditer(text):
                selection = QTextEdit.ExtraSelection()
                cursor = self.edit.textCursor()
                cursor.setPosition(match.start())
                cursor.setPosition(match.end(), cursor.MoveMode.KeepAnchor)
                selection.cursor = cursor
                selection.format = QTextCharFormat()
                selection.format.setForeground(QColor(color))
                selection.format.setFontWeight(QFont.Weight.Bold)
                selections.append(selection)
        self.edit.setExtraSelections(selections)


class NotesTab(QWidget):
    """Journal: dated notes with dialogue/@mention insertion and highlighting."""

    def __init__(self, store, on_change):
        super().__init__()
        self.store = store
        self.on_change = on_change
        self.current_note_id = None
        self._syncing = False

        root = QHBoxLayout(self)

        # --- Left pane: filter + list of notes ----------------------------
        left = QVBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter notes...")
        self.filter_edit.textChanged.connect(self.refresh_note_list)
        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._on_note_select)
        self.note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self._show_context_menu)
        self.new_note_btn = QPushButton("New Note")
        self.new_note_btn.clicked.connect(self._on_new_note)
        left.addWidget(self.filter_edit)
        left.addWidget(self.note_list, 1)
        left.addWidget(self.new_note_btn)
        root.addLayout(left, 1)

        # --- Right pane: editor ---------------------------------------------
        right = QVBoxLayout()
        # Compact insertion toolbar: pick an entity, then insert dialogue or a
        # @mention. The old per-entity button wall is gone.
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Insert:"))
        self.mention_combo = QComboBox()
        self.mention_combo.setMinimumWidth(180)
        self.mention_combo.activated.connect(self._on_mention_target)
        self.dialogue_btn = QPushButton('"Name: ..."')
        self.dialogue_btn.clicked.connect(self._insert_dialogue)
        self.mention_btn = QPushButton("@mention")
        self.mention_btn.clicked.connect(self._insert_mention)
        toolbar.addWidget(self.mention_combo)
        toolbar.addWidget(self.dialogue_btn)
        toolbar.addWidget(self.mention_btn)
        toolbar.addStretch(1)
        right.addLayout(toolbar)

        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Session title or note heading")
        self.title_edit.textChanged.connect(self._autosave)
        title_row.addWidget(self.title_edit, 1)
        right.addLayout(title_row)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "Write your journal here. Matching character, NPC, and location names are highlighted."
        )
        self.editor.textChanged.connect(self._autosave)
        right.addWidget(self.editor, 1)

        self.status = QLabel("")
        right.addWidget(self.status)
        root.addLayout(right, 3)

        self.highlighter = MentionHighlighter(
            self.editor,
            lambda: self.store[C.CHARACTERS] + self.store[C.NPCS] + self.store[C.LOCATIONS],
        )
        # Highlighting and the @mention reference scan are the only O(text x
        # entities) work per keystroke, so both are debounced: typing stays
        # responsive and the scan only runs once the user pauses.
        self._scan_timer = QTimer(self)
        self._scan_timer.setSingleShot(True)
        self._scan_timer.setInterval(C.REHIGHLIGHT_DELAY_MS)
        self._scan_timer.timeout.connect(self._on_rehighlight_due)
        self.editor.textChanged.connect(self._schedule_rehighlight)

        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_new_note)
        self._delete_shortcut = QShortcut(
            QKeySequence(QKeySequence.StandardKey.Delete), self.note_list
        )
        self._delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._delete_shortcut.activated.connect(self._on_delete_note)

    def refresh(self):
        """Refresh the insertion toolbar, note list, and highlighting."""
        self.refresh_mention_bar()
        self.refresh_note_list()
        self.highlighter.rehighlight()
        self._rescan_references()

    def _schedule_rehighlight(self):
        """Restart the debounce timer after a keystroke."""
        self._scan_timer.start()

    def _on_rehighlight_due(self):
        """Run once typing pauses: refresh highlights and stored references."""
        self.highlighter.rehighlight()
        self._rescan_references()

    def _rescan_references(self):
        """Recompute the @mention references stored on the note being edited."""
        note = self._find_note(self.current_note_id) if self.current_note_id else None
        if note is None:
            return
        text = self.editor.toPlainText()
        note["char_ids"] = referenced_ids(self.store[C.CHARACTERS], text)
        note["npc_ids"] = referenced_ids(self.store[C.NPCS], text)
        note["loc_ids"] = referenced_ids(self.store[C.LOCATIONS], text)

    def refresh_mention_bar(self):
        """Rebuild the entity dropdown for dialogue/@mention insertion."""
        self.mention_combo.blockSignals(True)
        self.mention_combo.clear()
        for kind, entities in (
            ("", self.store[C.CHARACTERS]),
            ("NPC", self.store[C.NPCS]),
            ("Location", self.store[C.LOCATIONS]),
        ):
            for entity in entities:
                name = entity.get("name")
                if not name:
                    continue
                label = f"{kind}: {name}" if kind else name
                self.mention_combo.addItem(label, name)
        if self.mention_combo.count() == 0:
            self.mention_combo.addItem("No characters, NPCs, or locations yet", None)
            self.dialogue_btn.setEnabled(False)
            self.mention_btn.setEnabled(False)
        else:
            self.dialogue_btn.setEnabled(True)
            self.mention_btn.setEnabled(True)
        self.mention_combo.blockSignals(False)

    def _on_mention_target(self, _index):
        """Keep buttons enabled/disabled in sync with the combo selection."""
        enabled = self.mention_combo.currentData() is not None
        self.dialogue_btn.setEnabled(enabled)
        self.mention_btn.setEnabled(enabled)

    def _selected_name(self):
        return self.mention_combo.currentData()

    def _note_text(self, note):
        stamp = note.get("timestamp", "")
        title = note.get("title") or "Untitled"
        return f"{stamp}  {title}"

    def refresh_note_list(self):
        """Rebuild the note list, honoring the filter and current selection."""
        self.note_list.blockSignals(True)
        self.note_list.clear()
        query = self.filter_edit.text().strip().lower()
        for note in self.store[C.NOTES]:
            if query and query not in self._note_text(note).lower():
                continue
            item = QListWidgetItem(self._note_text(note))
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self.note_list.addItem(item)
        if self.note_list.count() == 0:
            if query:
                hint = QListWidgetItem("No matches for the current filter.")
            else:
                hint = QListWidgetItem("No notes yet - click New Note.")
            hint.setFlags(Qt.ItemFlag.NoItemFlags)
            hint.setForeground(QColor(C.HINT_TEXT_COLOR))
            self.note_list.addItem(hint)
        self.note_list.blockSignals(False)
        if self.current_note_id is not None:
            index = self._note_index(self.current_note_id)
            if index >= 0:
                self.note_list.blockSignals(True)
                self.note_list.setCurrentRow(index)
                self.note_list.blockSignals(False)

    def _refresh_note_label(self, note):
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == note["id"]:
                item.setText(self._note_text(note))
                return

    def _note_index(self, note_id):
        for i, note in enumerate(self.store[C.NOTES]):
            if note["id"] == note_id:
                return i
        return -1

    def _find_note(self, note_id):
        return self.store.find(C.NOTES, note_id)

    def _autosave(self):
        """Persist the current note (creating it on first keystroke).

        Reference ids are left for _rescan_references(), which runs on the
        debounce timer; scanning on every keystroke here is O(text x entities).
        """
        if self._syncing:
            return
        note = self._ensure_note()
        note["title"] = self.title_edit.text().strip()
        note["text"] = self.editor.toPlainText()
        note["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._refresh_note_label(note)
        self.on_change()

    def _ensure_note(self):
        """Return the note being edited, lazily creating a draft if needed."""
        if self.current_note_id is not None:
            return self._find_note(self.current_note_id)
        note = {
            "id": C.new_id(),
            "title": "",
            "text": "",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "char_ids": [],
            "npc_ids": [],
            "loc_ids": [],
        }
        self.store.prepend(C.NOTES, note)  # newest note first
        self.current_note_id = note["id"]
        self.refresh_note_list()
        index = self._note_index(note["id"])
        if index >= 0:
            self.note_list.blockSignals(True)
            self.note_list.setCurrentRow(index)
            self.note_list.blockSignals(False)
        self.on_change()
        return note

    def _insert_dialogue(self):
        """Insert a newline, `Name: "`, and place the cursor between the quotes.

        A single cursor is reused for both insertions and the final caret
        placement; the widget only learns about it via setTextCursor() at the
        end, so the caret does not depend on Qt syncing a cursor copy back.
        """
        name = self._selected_name()
        if not name:
            return
        cursor = self.editor.textCursor()
        start = cursor.position()
        cursor.insertText(f"\n{name}: \"")
        cursor.insertText("\"")
        cursor.setPosition(start + dialogue_caret_offset(name))
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()
        self.highlighter.rehighlight()

    def _insert_mention(self):
        name = self._selected_name()
        if not name:
            return
        self.editor.textCursor().insertText(f"@{name} ")
        self.editor.setFocus()
        self.highlighter.rehighlight()

    def _on_note_select(self, current, _previous):
        """Load the selected note's title and text into the editor."""
        note_id = None if current is None else current.data(Qt.ItemDataRole.UserRole)
        self.current_note_id = note_id
        self._syncing = True
        try:
            if note_id is None:
                self.editor.clear()
                self.title_edit.clear()
                self.status.setText("")
                return
            note = self._find_note(note_id)
            if not note:
                return
            self.editor.setPlainText(note.get("text", ""))
            self.title_edit.setText(note.get("title", ""))
            self.status.setText(f"Loaded note from {note.get('timestamp', '')}")
        finally:
            self._syncing = False

    def _on_new_note(self):
        self.current_note_id = None
        self.note_list.setCurrentItem(None)
        self._syncing = True
        try:
            self.editor.clear()
            self.title_edit.clear()
        finally:
            self._syncing = False
        self.title_edit.setFocus()
        self.status.setText("New note - start typing, it saves automatically.")

    def _on_delete_note(self):
        if self.current_note_id is None:
            return
        if not confirm(self, C.APP_NAME, "Delete this note?"):
            return
        self.store.remove(C.NOTES, self.current_note_id)
        self.current_note_id = None
        self.refresh_note_list()
        self._syncing = True
        try:
            self.editor.clear()
            self.title_edit.clear()
        finally:
            self._syncing = False
        self.status.setText("Note deleted.")
        self.on_change()

    def _show_context_menu(self, pos):
        """Right-click menu on the note list, targeting the row under the cursor."""
        menu = QMenu(self)
        menu.addAction("New Note", self._on_new_note)
        item = self.note_list.itemAt(pos)
        if item is not None and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            self.note_list.setCurrentItem(item)
            menu.addAction("Delete", self._on_delete_note)
        menu.exec(self.note_list.mapToGlobal(pos))
