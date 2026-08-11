"""What do I know? dialog: every note mentioning an entity, as a timeline.

A focused lookup over the journal: pick any character, NPC, location, or
monster and see every note that names it, oldest first, with a preview of
each entry. The dialog is read-only, so browsing can never clobber a note.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from hexlog import constants as C
from hexlog.ui.notes import notes_mentioning


def entity_items(store):
    """(label, entity) pairs for the picker, one row per named entity."""
    items = []
    for kind, prefix in (
        (C.CHARACTERS, ""),
        (C.NPCS, "NPC: "),
        (C.LOCATIONS, "Location: "),
        (C.MONSTERS, "Monster: "),
    ):
        for entity in store[kind]:
            name = entity.get("name")
            if name:
                items.append((f"{prefix}{name}", entity))
    return items


class KnownDialog(QDialog):
    """Look up every journal note that mentions a chosen entity."""

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("What do I know?")
        self.resize(620, 520)
        self.store = store
        self._entities = []  # entity behind each combo index

        root = QVBoxLayout(self)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Entity:"))
        self.entity_combo = QComboBox()
        self.entity_combo.setMinimumWidth(220)
        self.entity_combo.currentIndexChanged.connect(self._on_entity_changed)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {C.HINT_TEXT_COLOR};")
        picker_row.addWidget(self.entity_combo, 1)
        picker_row.addWidget(self.count_label)
        root.addLayout(picker_row)

        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._on_note_changed)
        root.addWidget(self.note_list, 1)

        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Select a note to read the full entry.")
        root.addWidget(self.preview, 2)

        buttons = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._populate()

    def _populate(self):
        """Fill the entity picker and show results for the first entity."""
        pairs = entity_items(self.store)
        self.entity_combo.blockSignals(True)
        self.entity_combo.clear()
        self._entities = [entity for _label, entity in pairs]
        for label, _entity in pairs:
            self.entity_combo.addItem(label)
        self.entity_combo.blockSignals(False)
        if self._entities:
            self._on_entity_changed(0)
        else:
            self.count_label.setText("Add characters, NPCs, locations, or monsters first.")
            self._set_hint("No entities yet.")

    def _selected_entity(self):
        index = self.entity_combo.currentIndex()
        if 0 <= index < len(self._entities):
            return self._entities[index]
        return None

    def _on_entity_changed(self, _index):
        """Rebuild the timeline for the newly picked entity."""
        matches = notes_mentioning(self.store[C.NOTES], self._selected_entity())
        if matches:
            self.count_label.setText(f"appears in {len(matches)} note(s)")
        else:
            self.count_label.setText("no notes mention this entity")
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in matches:
            item = QListWidgetItem(self._note_text(note))
            item.setData(Qt.ItemDataRole.UserRole, note["id"])
            self.note_list.addItem(item)
        self.note_list.blockSignals(False)
        if matches:
            self.note_list.setCurrentRow(0)
        else:
            self._set_hint("No notes mention this entity.")
            self.preview.clear()

    def _note_text(self, note):
        stamp = note.get("timestamp", "")
        title = note.get("title") or "Untitled"
        return f"{stamp}  {title}"

    def _set_hint(self, text):
        """Show `text` as a non-selectable placeholder row in the timeline."""
        self.note_list.blockSignals(True)
        self.note_list.clear()
        hint = QListWidgetItem(text)
        hint.setFlags(Qt.ItemFlag.NoItemFlags)
        hint.setForeground(QColor(C.HINT_TEXT_COLOR))
        self.note_list.addItem(hint)
        self.note_list.blockSignals(False)

    def _on_note_changed(self, current, _previous):
        """Preview the selected note in the read-only pane."""
        if current is None:
            return
        note = self.store.find(C.NOTES, current.data(Qt.ItemDataRole.UserRole))
        if note is None:
            return
        self.preview.setPlainText(
            f"{self._note_text(note)}\n\n{note.get('text', '')}"
        )
