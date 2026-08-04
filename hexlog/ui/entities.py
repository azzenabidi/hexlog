"""Editors for characters, NPCs, locations, and monster statblocks.

Everything edits the shared Store directly and calls on_change() to trigger a
debounced save, so there are no explicit Save buttons - what you type is what
gets persisted the moment you pause.
"""

import os
import shutil
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hexlog import constants as C
from hexlog.storage import next_color
from hexlog.validation import validate_name


class EntityTab(QWidget):
    """Generic master-detail editor for characters, NPCs, locations, monsters.

    Subclasses differ only in which fields they expose and whether an image
    can be attached. Characters/NPCs use images for VTT tokens; locations
    keep a simple color-filled token.
    """

    def __init__(self, store, on_change, kind, extra_fields, list_label,
                 form_title, entity_label, enable_image=False,
                 desc_attr="description", desc_label="Description",
                 extra_placeholders=None):
        super().__init__()
        self.store = store  # shared Store; all reads/writes go through it
        # Callback fired after every mutation so the main window can persist.
        self.on_change = on_change
        self.kind = kind  # key into the store, e.g. "characters"
        self.extra_fields = extra_fields  # (attribute, label) pairs for extra form rows
        self.entity_label = entity_label
        self.enable_image = enable_image
        self.desc_attr = desc_attr  # store attribute holding the multiline text
        self.desc_label = desc_label
        self.extra_placeholders = extra_placeholders or {}
        self.current_id = None  # id of the entity being edited; None means "blank new form"
        self._syncing = False  # True while the form is being filled programmatically

        root = QHBoxLayout(self)

        # --- Left pane: filter + list of existing entities ---------------
        left = QVBoxLayout()
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(f"Filter {list_label.lower()}...")
        self.filter_edit.textChanged.connect(self.refresh_list)
        self.entity_list = QListWidget()
        self.entity_list.currentItemChanged.connect(self._on_select)
        self.entity_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entity_list.customContextMenuRequested.connect(self._show_context_menu)
        self.add_btn = QPushButton(f"New {entity_label}")
        self.add_btn.clicked.connect(self._on_new)
        left.addWidget(self.filter_edit)
        left.addWidget(self.entity_list, 1)
        left.addWidget(self.add_btn)
        root.addLayout(left, 1)

        # --- Right pane: editable detail form -----------------------------
        form_box = QGroupBox(form_title)
        form = QFormLayout(form_box)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(f"{entity_label} name")
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.extra_edits = {}
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setMinimumHeight(140)
        self.desc_edit.textChanged.connect(self._on_desc_changed)
        self.color = QColor(C.DEFAULT_ENTITY_COLOR)

        form.addRow("Name", self.name_edit)
        for attr, label in self.extra_fields:
            edit = QLineEdit()
            placeholder = self.extra_placeholders.get(attr)
            if placeholder:
                edit.setPlaceholderText(placeholder)
            edit.textChanged.connect(lambda t, a=attr: self._on_extra_changed(a, t))
            self.extra_edits[attr] = edit
            form.addRow(label, edit)
        form.addRow(self.desc_label, self.desc_edit)
        if self.enable_image:
            self.image_name = None  # stored basename of the committed image
            self.image_label = QLabel("No image")
            self.image_btn = QPushButton("Choose Image...")
            self.image_btn.clicked.connect(self._pick_image)
            self.image_clear_btn = QPushButton("Clear")
            self.image_clear_btn.clicked.connect(self._clear_image)
            img_row = QHBoxLayout()
            img_row.addWidget(self.image_label, 1)
            img_row.addWidget(self.image_btn)
            img_row.addWidget(self.image_clear_btn)
            form.addRow("Token Image", img_row)

        self.status = QLabel("")
        form.addRow(self.status)

        # Name validation messages live here so they never clobber the status.
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {C.ERROR_COLOR};")
        self.error_label.hide()
        form.addRow(self.error_label)

        root.addWidget(form_box, 2)

        # Shortcuts: Ctrl+N starts a new entity, Delete removes the selection
        # while the list has focus (so text editing is never hijacked).
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_new)
        self._delete_shortcut = QShortcut(
            QKeySequence(QKeySequence.StandardKey.Delete), self.entity_list
        )
        self._delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._delete_shortcut.activated.connect(self._on_delete)

    def _entities(self):
        """Shortcut to this tab's entity list in the shared store."""
        return self.store[self.kind]

    def _list_text(self, entity):
        """Format the list row: name plus the extra fields joined with ' / '."""
        name = entity.get("name") or "(unnamed)"
        extras = " / ".join(entity.get(attr) or "-" for attr, _ in self.extra_fields)
        return f"{name}  ({extras})"

    def refresh(self):
        """Full refresh of both the list and the detail form."""
        self.refresh_list()
        self.refresh_form()

    def refresh_list(self):
        """Rebuild the list widget, honoring the filter and current selection."""
        self.entity_list.blockSignals(True)
        self.entity_list.clear()
        query = self.filter_edit.text().strip().lower()
        for entity in self._entities():
            if query and query not in self._list_text(entity).lower():
                continue
            item = QListWidgetItem(self._list_text(entity))
            item.setData(Qt.ItemDataRole.UserRole, entity["id"])
            item.setForeground(QColor(entity.get("color", C.DEFAULT_ENTITY_COLOR)))
            self.entity_list.addItem(item)
        if self.entity_list.count() == 0:
            hint = QListWidgetItem(
                f"No {self.entity_label.lower()}s yet - click New {self.entity_label}."
            )
            hint.setFlags(Qt.ItemFlag.NoItemFlags)  # purely decorative
            hint.setForeground(QColor(C.HINT_TEXT_COLOR))
            self.entity_list.addItem(hint)
        self.entity_list.blockSignals(False)
        # Auto-select the first item only when nothing is selected yet, so an
        # in-progress new-entity form isn't hijacked by a refresh.
        if self.current_id is None and self.entity_list.count():
            first = self.entity_list.item(0)
            if first.flags() & Qt.ItemFlag.ItemIsSelectable:
                self.entity_list.setCurrentRow(0)

    def _refresh_item_label(self, entity):
        """Update just this entity's row without rebuilding the whole list."""
        for i in range(self.entity_list.count()):
            item = self.entity_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == entity["id"]:
                item.setText(self._list_text(entity))
                item.setForeground(QColor(entity.get("color", C.DEFAULT_ENTITY_COLOR)))
                return

    def refresh_form(self):
        """Populate the form from the selected entity, or reset for a new one.

        Programmatic fills are guarded by _syncing so the autosave handlers
        don't fire (and mutate the store) while we're just loading values.
        """
        self._syncing = True
        try:
            if self.current_id is None:
                self.name_edit.clear()
                for edit in self.extra_edits.values():
                    edit.clear()
                self.desc_edit.clear()
                self.color = QColor(C.DEFAULT_ENTITY_COLOR)
                if self.enable_image:
                    self.image_name = None
                    self._update_image_label()
                self._set_name_error(None)
                self.status.setText(
                    f"Create a {self.entity_label.lower()} - start typing, it saves automatically."
                )
                return
            entity = self._find(self.current_id)
            if not entity:
                return
            self.name_edit.setText(entity.get("name", ""))
            for attr, _ in self.extra_fields:
                self.extra_edits[attr].setText(entity.get(attr, ""))
            self.desc_edit.setPlainText(entity.get(self.desc_attr, ""))
            self.color = QColor(entity.get("color", C.DEFAULT_ENTITY_COLOR))
            if self.enable_image:
                self.image_name = entity.get("image") or None
                self._update_image_label()
            self._set_name_error(validate_name(self.name_edit.text()))
            self.status.setText(f"Editing {entity.get('name') or '(unnamed)'}")
        finally:
            self._syncing = False

    def _find(self, entity_id):
        return self.store.find(self.kind, entity_id)

    def _entity_index(self, entity_id):
        for i in range(self.entity_list.count()):
            if self.entity_list.item(i).data(Qt.ItemDataRole.UserRole) == entity_id:
                return i
        return -1

    def _select_id(self, entity_id):
        """Select a row by entity id without firing selection signals."""
        index = self._entity_index(entity_id)
        if index >= 0:
            self.entity_list.blockSignals(True)
            self.entity_list.setCurrentRow(index)
            self.entity_list.blockSignals(False)

    def _on_select(self, current, _previous):
        """Selection handler: switch the form to the newly selected entity."""
        entity_id = None if current is None else current.data(Qt.ItemDataRole.UserRole)
        self.current_id = entity_id
        self.refresh_form()

    def _on_new(self):
        """Reset the form to blank; the first keystroke creates the entity."""
        self.current_id = None
        self.entity_list.setCurrentItem(None)
        self.refresh_form()
        self.name_edit.setFocus()
        self.status.setText(
            f"New {self.entity_label.lower()} - start typing, it saves automatically."
        )

    def _ensure(self):
        """Return the entity being edited, lazily creating a draft if needed."""
        if self.current_id is not None:
            return self._find(self.current_id)
        entity = {
            "id": C.new_id(),
            "name": f"New {self.entity_label}",
            self.desc_attr: "",
            "color": QColor(next_color(self._entities())).name(),
        }
        for attr, _ in self.extra_fields:
            entity[attr] = ""
        self.store.add(self.kind, entity)
        self.current_id = entity["id"]
        self.refresh_list()
        self._select_id(entity["id"])
        self.on_change()
        return entity

    def _on_name_changed(self, text):
        if self._syncing:
            return
        entity = self._ensure()
        entity["name"] = text.strip()
        self._refresh_item_label(entity)
        self._set_name_error(validate_name(text))
        self.on_change()

    def _set_name_error(self, message):
        """Show or hide the name validation message."""
        if message:
            self.error_label.setText(message)
            self.error_label.show()
        else:
            self.error_label.clear()
            self.error_label.hide()

    def _on_extra_changed(self, attr, text):
        if self._syncing:
            return
        entity = self._ensure()
        entity[attr] = text.strip()
        self._refresh_item_label(entity)
        self.on_change()

    def _on_desc_changed(self):
        if self._syncing:
            return
        entity = self._ensure()
        entity[self.desc_attr] = self.desc_edit.toPlainText()
        self.on_change()

    def _resolved_image(self):
        """Return an absolute path to the current image, or None if unusable."""
        if not self.image_name:
            return None
        path = os.path.join(C.TOKENS_DIR, self.image_name)
        return path if os.path.exists(path) else None

    def _update_image_label(self):
        """Show a small thumbnail of the current image, or 'No image'."""
        path = self._resolved_image()
        pix = QPixmap(path) if path else QPixmap()
        if pix.isNull():
            self.image_label.setText("No image")
            self.image_label.setPixmap(QPixmap())
            return
        self.image_label.setText("")
        self.image_label.setPixmap(
            pix.scaled(
                40, 40,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _pick_image(self):
        """Pick an image, copy it into TOKENS_DIR, and attach it immediately."""
        path, _ = QFileDialog.getOpenFileName(self, "Choose token image", "", C.IMAGE_FILTER)
        if not path:
            return  # cancelled - never create a draft for a dismissed dialog
        if self.current_id is None:
            self._ensure()  # a draft is fine once an image is actually chosen
        ext = os.path.splitext(path)[1]
        dest = os.path.join(C.TOKENS_DIR, f"{uuid.uuid4().hex[:8]}{ext}")
        try:
            shutil.copy(path, dest)
        except OSError:
            # Surface the failure rather than silently dropping the choice.
            QMessageBox.warning(
                self, C.APP_NAME, "Could not copy the image into the app data folder."
            )
            return
        entity = self._find(self.current_id)
        entity["image"] = os.path.basename(dest)
        self.image_name = os.path.basename(dest)
        self._update_image_label()
        self.on_change()

    def _clear_image(self):
        """Remove the attached image from the entity immediately."""
        if self.current_id is None:
            return
        entity = self._find(self.current_id)
        entity.pop("image", None)
        self.image_name = None
        self._update_image_label()
        self.on_change()

    def _on_delete(self):
        """Remove the selected entity after confirmation."""
        if self.current_id is None:
            return
        entity = self._find(self.current_id)
        answer = QMessageBox.question(
            self,
            C.APP_NAME,
            # Notes/tokens reference entities by name text, so they are kept
            # even though the entity itself disappears.
            f"Delete {entity.get('name') or '(unnamed)'}? Existing notes and tokens keep their text.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.remove(self.kind, self.current_id)
        self.current_id = None
        self.refresh()
        self.on_change()

    def _show_context_menu(self, pos):
        """Right-click menu on the list: new, and delete for a real row."""
        menu = QMenu(self)
        menu.addAction(f"New {self.entity_label}", self._on_new)
        item = self.entity_list.itemAt(pos)
        if item is not None and item.flags() & Qt.ItemFlag.ItemIsSelectable:
            menu.addAction("Delete", self._on_delete)
        menu.exec(self.entity_list.mapToGlobal(pos))


class CharactersTab(EntityTab):
    """Entity editor for player characters (with race/class fields)."""

    def __init__(self, store, on_change):
        super().__init__(
            store,
            on_change,
            kind=C.CHARACTERS,
            extra_fields=[("race", "Race"), ("class", "Class")],
            list_label="Characters",
            form_title="Character Details",
            entity_label="Character",
            enable_image=True,
        )


class NPCsTab(EntityTab):
    """Entity editor for NPCs (with a role field)."""

    def __init__(self, store, on_change):
        super().__init__(
            store,
            on_change,
            kind=C.NPCS,
            extra_fields=[("role", "Role")],
            list_label="NPCs",
            form_title="NPC Details",
            entity_label="NPC",
            enable_image=True,
        )


class LocationsTab(EntityTab):
    """Entity editor for locations (with a type field)."""

    def __init__(self, store, on_change):
        super().__init__(
            store,
            on_change,
            kind=C.LOCATIONS,
            extra_fields=[("type", "Type")],
            list_label="Locations",
            form_title="Location Details",
            entity_label="Location",
        )


class MonsterTab(EntityTab):
    """Statblock editor for monsters; reuses the generic master-detail tab."""

    def __init__(self, store, on_change):
        super().__init__(
            store,
            on_change,
            kind=C.MONSTERS,
            extra_fields=[
                ("cr", "CR"),
                ("link", "Statblock Link"),
                ("ac", "AC"),
                ("hp", "HP"),
                ("speed", "Speed"),
                ("abilities", "Abilities"),
            ],
            extra_placeholders={
                "cr": "e.g. 1/2, 3, 14",
                "link": "https://... (optional statblock link)",
                "abilities": "e.g. STR 14, DEX 12, CON 14, INT 8, WIS 10, CHA 8",
            },
            list_label="Monsters",
            form_title="Monster Statblock",
            entity_label="Monster",
            desc_attr="details",
            desc_label="Traits / Actions",
        )

    def _list_text(self, monster):
        name = monster.get("name") or "(unnamed)"
        cr = monster.get("cr", "")
        return f"{name}  (CR {cr})" if cr else name
