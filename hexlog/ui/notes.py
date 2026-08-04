"""Journal: notes with dialogue/@mention insertion and highlighting."""

import re
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from hexlog import constants as C


class MentionHighlighter:
    """Colors entity names appearing in the journal editor.

    Uses QTextEdit.ExtraSelection, which overlays formatting without
    modifying the underlying document text, so highlighting is purely visual.
    """

    def __init__(self, edit, get_entities):
        self.edit = edit
        self.get_entities = get_entities  # callback returns the current entity lists
        self.rules = []  # (compiled regex, color) pairs

    def refresh(self):
        """(Re)build regex rules from the current entities."""
        self.rules = []
        for entity in self.get_entities():
            name = entity.get("name", "")
            if name:
                # Word boundaries keep "Al" from matching inside "Altar".
                self.rules.append(
                    (re.compile(r"\b" + re.escape(name) + r"\b"), entity.get("color", "#888"))
                )

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

        root = QHBoxLayout(self)

        # --- Left pane: list of notes ----------------------------------------
        left = QVBoxLayout()
        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._on_note_select)
        self.new_note_btn = QPushButton("New Note")
        self.new_note_btn.clicked.connect(self._on_new_note)
        self.delete_note_btn = QPushButton("Delete Note")
        self.delete_note_btn.clicked.connect(self._on_delete_note)
        left.addWidget(QLabel("Journal"))
        left.addWidget(self.note_list, 1)
        left.addWidget(self.new_note_btn)
        left.addWidget(self.delete_note_btn)
        root.addLayout(left, 1)

        # --- Right pane: editor ------------------------------------------------
        right = QVBoxLayout()
        # Scrollable strip of buttons for inserting dialogue/@mentions.
        self.char_bar = QWidget()
        self.char_bar_layout = QVBoxLayout(self.char_bar)
        self.char_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.char_scroll = QScrollArea()
        self.char_scroll.setWidget(self.char_bar)
        self.char_scroll.setWidgetResizable(True)
        self.char_scroll.setFixedHeight(120)

        top = QHBoxLayout()
        top.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Session title or note heading")
        top.addWidget(self.title_edit, 1)
        right.addWidget(self.char_scroll)
        right.addLayout(top)
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(
            "Write your journal here.\n"
            "Use the character/NPC/location buttons below to add dialogue or @mentions - matching names are highlighted."
        )
        right.addWidget(self.editor, 1)

        bottom = QHBoxLayout()
        self.save_btn = QPushButton("Save Note")
        self.save_btn.clicked.connect(self._on_save_note)
        self.clear_btn = QPushButton("Clear Editor")
        self.clear_btn.clicked.connect(self._on_clear_editor)
        bottom.addWidget(self.save_btn)
        bottom.addWidget(self.clear_btn)
        bottom.addStretch(1)
        self.status = QLabel("")
        bottom.addWidget(self.status)
        right.addLayout(bottom)
        root.addLayout(right, 3)

        self.highlighter = MentionHighlighter(
            self.editor,
            lambda: self.store[C.CHARACTERS] + self.store[C.NPCS] + self.store[C.LOCATIONS],
        )
        # Re-highlight on every keystroke to keep mentions current.
        self.editor.textChanged.connect(self.highlighter.rehighlight)

    def refresh(self):
        """Refresh the entity button bar, note list, and highlighting."""
        self.refresh_entity_bar()
        self.refresh_note_list()
        self.highlighter.rehighlight()

    def refresh_entity_bar(self):
        """Rebuild the dialogue/@mention buttons from the current entities."""
        # Tear down previous widgets explicitly or they leak as orphaned children.
        while self.char_bar_layout.count():
            item = self.char_bar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._add_entity_rows(self.store[C.CHARACTERS], prefix="")
        self._add_entity_rows(self.store[C.NPCS], prefix="NPC ")
        self._add_entity_rows(self.store[C.LOCATIONS], prefix="Location ")
        if not self.store[C.CHARACTERS] and not self.store[C.NPCS] and not self.store[C.LOCATIONS]:
            empty = QLabel(
                "No characters, NPCs, or locations yet - add them in the "
                "Characters/NPCs/Locations tabs to reference them here."
            )
            empty.setStyleSheet("color: #888;")
            self.char_bar_layout.addWidget(empty)

    def _add_entity_rows(self, entities, prefix=""):
        """Add one row of buttons per entity for quick insertion."""
        for entity in entities:
            row = QHBoxLayout()
            color = QColor(entity.get("color", "#888"))
            name_label = QLabel(prefix + entity["name"])
            name_label.setStyleSheet(f"color: {color.name()}; font-weight: bold;")
            dialogue_btn = QPushButton(f'{entity["name"]}: "...')
            mention_btn = QPushButton("@mention")
            # Lambdas capture n via a default arg so the entity name is bound
            # at click time rather than whichever name the loop ended on.
            dialogue_btn.clicked.connect(lambda _=False, n=entity["name"]: self._insert_dialogue(n))
            mention_btn.clicked.connect(lambda _=False, n=entity["name"]: self._insert_mention(n))
            row.addWidget(name_label)
            row.addWidget(dialogue_btn)
            row.addWidget(mention_btn)
            row.addStretch(1)
            container = QWidget()
            container.setLayout(row)
            self.char_bar_layout.addWidget(container)

    def refresh_note_list(self):
        """Rebuild the note list, restoring the current selection."""
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in self.store[C.NOTES]:
            stamp = note.get("timestamp", "")
            title = note.get("title") or "Untitled"
            item = QListWidgetItem(f"{stamp}  {title}")
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self.note_list.addItem(item)
        self.note_list.blockSignals(False)
        if self.current_note_id is not None:
            index = self._note_index(self.current_note_id)
            if index >= 0:
                self.note_list.setCurrentRow(index)

    def _note_index(self, note_id):
        for i, note in enumerate(self.store[C.NOTES]):
            if note["id"] == note_id:
                return i
        return -1

    def _find_note(self, note_id):
        return self.store.find(C.NOTES, note_id)

    def _insert_dialogue(self, name):
        """Insert a newline, `Name: "`, and place the cursor between the quotes."""
        text_cursor = self.editor.textCursor()
        text_cursor.insertText(f"\n{name}: \"")
        inner = self.editor.textCursor().position()
        text_cursor.insertText("\"")
        new_cursor = self.editor.textCursor()
        new_cursor.setPosition(inner)
        self.editor.setTextCursor(new_cursor)
        self.editor.setFocus()
        self.highlighter.rehighlight()

    def _insert_mention(self, name):
        self.editor.textCursor().insertText(f"@{name} ")
        self.editor.setFocus()
        self.highlighter.rehighlight()

    def _on_note_select(self, current, _previous):
        """Load the selected note's title and text into the editor."""
        if current is None:
            self.current_note_id = None
            self.editor.clear()
            self.title_edit.clear()
            return
        self.current_note_id = current.data(Qt.ItemDataRole.UserRole)
        note = self._find_note(self.current_note_id)
        self.editor.setPlainText(note.get("text", ""))
        self.title_edit.setText(note.get("title", ""))
        self.status.setText(f"Loaded note from {note.get('timestamp', '')}")

    def _on_new_note(self):
        self.current_note_id = None
        self.note_list.setCurrentItem(None)
        self.editor.clear()
        self.title_edit.clear()
        self.title_edit.setFocus()
        self.status.setText("New note - write below, then press Save Note.")

    def _on_clear_editor(self):
        self.editor.clear()

    def _on_save_note(self):
        """Create or update a note, recording which entities its text mentions."""
        text = self.editor.toPlainText().strip()
        if not text and not self.title_edit.text().strip():
            self.status.setText("Nothing to save.")
            return
        # A plain substring match (no word boundaries) keeps this lenient:
        # even partial or pluralized mentions count as references.
        char_refs = [
            ch["id"] for ch in self.store[C.CHARACTERS] if ch["name"] and ch["name"] in text
        ]
        npc_refs = [
            npc["id"] for npc in self.store[C.NPCS] if npc["name"] and npc["name"] in text
        ]
        loc_refs = [
            loc["id"] for loc in self.store[C.LOCATIONS] if loc["name"] and loc["name"] in text
        ]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = self.title_edit.text().strip()
        if self.current_note_id is None:
            note = {
                "id": C.new_id(),
                "title": title,
                "text": text,
                "timestamp": timestamp,
                "char_ids": char_refs,
                "npc_ids": npc_refs,
                "loc_ids": loc_refs,
            }
            self.store.prepend(C.NOTES, note)  # newest note first
            self.current_note_id = note["id"]
        else:
            note = self._find_note(self.current_note_id)
            note["title"] = title
            note["text"] = text
            note["timestamp"] = timestamp
            note["char_ids"] = char_refs
            note["npc_ids"] = npc_refs
            note["loc_ids"] = loc_refs
        self.refresh_note_list()
        self.on_change()
        self.status.setText(
            f"Saved. Referenced characters: {len(char_refs)}, NPCs: {len(npc_refs)}, locations: {len(loc_refs)}"
        )

    def _on_delete_note(self):
        if self.current_note_id is None:
            return
        answer = QMessageBox.question(self, C.APP_NAME, "Delete this note?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.remove(C.NOTES, self.current_note_id)
        self.current_note_id = None
        self.refresh_note_list()
        self.editor.clear()
        self.title_edit.clear()
        self.status.setText("Note deleted.")
        self.on_change()
