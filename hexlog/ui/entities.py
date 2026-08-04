"""Editors for characters, NPCs, locations, and monster statblocks."""

import os
import shutil
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hexlog import constants as C
from hexlog.storage import next_color


class EntityTab(QWidget):
    """Generic master-detail editor for characters, NPCs and locations.

    The subclasses differ only in which extra text fields they expose and
    whether an image can be attached. Characters/NPCs use images for VTT
    tokens; locations keep a simple color-filled token.
    """

    def __init__(self, store, on_change, kind, extra_fields, list_label,
                 form_title, entity_label, enable_image=False):
        super().__init__()
        self.store = store  # shared Store; all reads/writes go through it
        # Callback fired after every mutation so the main window can persist.
        self.on_change = on_change
        self.kind = kind  # key into the store, e.g. "characters"
        self.extra_fields = extra_fields  # (attribute, label) pairs for extra form rows
        self.entity_label = entity_label
        self.enable_image = enable_image
        self.current_id = None  # id of the entity being edited; None means "new"

        root = QHBoxLayout(self)

        # --- Left pane: list of existing entities -------------------------
        left = QVBoxLayout()
        self.entity_list = QListWidget()
        self.entity_list.currentItemChanged.connect(self._on_select)
        self.add_btn = QPushButton(f"New {entity_label}")
        self.add_btn.clicked.connect(self._on_new)
        left.addWidget(QLabel(list_label))
        left.addWidget(self.entity_list, 1)
        left.addWidget(self.add_btn)
        root.addLayout(left, 1)

        # --- Right pane: editable detail form -----------------------------
        form_box = QGroupBox(form_title)
        form = QFormLayout(form_box)
        self.name_edit = QLineEdit()
        self.extra_edits = {}
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setFixedHeight(140)
        self.color = QColor("#888888")

        form.addRow("Name", self.name_edit)
        for attr, label in self.extra_fields:
            edit = QLineEdit()
            self.extra_edits[attr] = edit
            form.addRow(label, edit)
        form.addRow("Description", self.desc_edit)
        if self.enable_image:
            # An attached image is only *committed* on Save (see _save_image),
            # so a picked-then-abandoned image never writes to disk.
            self.image_name = None  # stored basename of the committed image
            self.pending_image = None  # absolute path picked but not yet saved
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

        btns = QHBoxLayout()
        self.save_btn = QPushButton(f"Save {entity_label}")
        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._on_delete)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.delete_btn)
        form.addRow(btns)

        self.status = QLabel(f"Create a {entity_label.lower()} to get started.")
        form.addRow(self.status)
        root.addWidget(form_box, 2)

    def _entities(self):
        """Shortcut to this tab's entity list in the shared store."""
        return self.store[self.kind]

    def _list_text(self, entity):
        """Format the list row: name plus the extra fields joined with ' / '."""
        extras = " / ".join(entity.get(attr) or "-" for attr, _ in self.extra_fields)
        return f"{entity['name']}  ({extras})"

    def refresh(self):
        """Full refresh of both the list and the detail form."""
        self.refresh_list()
        self.refresh_form()

    def refresh_list(self):
        """Rebuild the list widget, preserving the current selection if any."""
        # Signals are blocked during the rebuild so clearing/re-populating the
        # list doesn't fire a spurious selection-change on the form.
        self.entity_list.blockSignals(True)
        self.entity_list.clear()
        for entity in self._entities():
            item = QListWidgetItem(self._list_text(entity))
            # The entity id rides along in UserRole for selection lookup.
            item.setData(Qt.ItemDataRole.UserRole, entity["id"])
            item.setForeground(QColor(entity.get("color", "#888")))
            self.entity_list.addItem(item)
        self.entity_list.blockSignals(False)
        # Auto-select the first item only when nothing is currently selected
        # (e.g. first launch), so an in-progress new-entity form isn't hijacked.
        if self.entity_list.count() > 0 and self.current_id is None:
            self.entity_list.setCurrentRow(0)

    def refresh_form(self):
        """Populate the form from the selected entity, or reset for a new one."""
        if self.current_id is None:
            self.name_edit.clear()
            for edit in self.extra_edits.values():
                edit.clear()
            self.desc_edit.clear()
            self.color = QColor("#888888")
            if self.enable_image:
                self.image_name = None
                self.pending_image = None
                self._update_image_label()
            self.status.setText(f"Create a {self.entity_label.lower()} to get started.")
            return
        entity = self._find(self.current_id)
        if not entity:
            return
        self.name_edit.setText(entity.get("name", ""))
        for attr, _ in self.extra_fields:
            self.extra_edits[attr].setText(entity.get(attr, ""))
        self.desc_edit.setPlainText(entity.get("description", ""))
        self.color = QColor(entity.get("color", "#888888"))
        if self.enable_image:
            self.image_name = entity.get("image") or None
            self.pending_image = None  # loading a saved entity, nothing pending
            self._update_image_label()
        self.status.setText(f"Editing {entity['name']}")

    def _find(self, entity_id):
        return self.store.find(self.kind, entity_id)

    def _on_select(self, current, _previous):
        """Selection handler: switch the form to the newly selected entity."""
        if current is None:
            self.current_id = None
            return
        self.current_id = current.data(Qt.ItemDataRole.UserRole)
        self.refresh_form()

    def _on_new(self):
        """Reset the form to blank to prepare for creating a new entity."""
        self.current_id = None
        self.entity_list.setCurrentItem(None)
        self.name_edit.clear()
        for edit in self.extra_edits.values():
            edit.clear()
        self.desc_edit.clear()
        # Assign a palette color up front so the token has a sensible default.
        self.color = QColor(next_color(self._entities()))
        if self.enable_image:
            self.image_name = None
            self.pending_image = None
            self._update_image_label()
        self.name_edit.setFocus()
        self.status.setText(f"New {self.entity_label.lower()} - fill in the fields and press Save.")

    def _resolved_image(self):
        """Return an absolute path to the current image, or None if unusable."""
        path = self.pending_image or self.image_name
        if not path:
            return None
        if self.pending_image:
            return self.pending_image
        path = os.path.join(C.TOKENS_DIR, path)
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
        """Open a file dialog and stage the chosen image (saved on Save)."""
        path, _ = QFileDialog.getOpenFileName(self, "Choose token image", "", C.IMAGE_FILTER)
        if not path:
            return
        self.pending_image = path
        self._update_image_label()

    def _clear_image(self):
        """Discard any staged image and forget the stored one (on save)."""
        self.pending_image = None
        self.image_name = None
        self._update_image_label()

    def _save_image(self, entity):
        """Copy a staged image into TOKENS_DIR and record it on the entity.

        Images are stored under a random basename so two entities can use
        files with the same name, and so deleting a source file is safe.
        """
        if self.pending_image:
            ext = os.path.splitext(self.pending_image)[1]
            dest = os.path.join(C.TOKENS_DIR, f"{uuid.uuid4().hex[:8]}{ext}")
            try:
                shutil.copy(self.pending_image, dest)
            except Exception:
                # A failed copy shouldn't abort the whole save.
                return
            entity["image"] = os.path.basename(dest)
            self.image_name = os.path.basename(dest)
            self.pending_image = None
        elif not self.image_name:
            # Image was cleared (or never set) - drop the stored reference.
            entity.pop("image", None)

    def _on_save(self):
        """Create or update the entity from the current form values."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, C.APP_NAME, f"A {self.entity_label.lower()} needs a name.")
            return
        if self.current_id is None:
            entity = {
                "id": C.new_id(),  # short, collision-free id
                "name": name,
                "description": self.desc_edit.toPlainText().strip(),
                "color": self.color.name(),
            }
            for attr, _ in self.extra_fields:
                entity[attr] = self.extra_edits[attr].text().strip()
            self.store.add(self.kind, entity)
            self.current_id = entity["id"]
        else:
            entity = self._find(self.current_id)
            entity["name"] = name
            entity["description"] = self.desc_edit.toPlainText().strip()
            entity["color"] = self.color.name()
            for attr, _ in self.extra_fields:
                entity[attr] = self.extra_edits[attr].text().strip()
        if self.enable_image:
            self._save_image(entity)
        self.refresh_list()
        self.refresh_form()
        self.on_change()  # persist to disk
        self.status.setText(f"Saved {name}.")

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
            f"Delete {entity['name']}? Existing notes and tokens keep their text.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.remove(self.kind, self.current_id)
        self.current_id = None
        self.refresh()
        self.on_change()


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


class MonsterTab(QWidget):
    """Statblock editor for monsters: name, CR, link, AC/HP/speed/abilities."""

    def __init__(self, store, on_change):
        super().__init__()
        self.store = store
        self.on_change = on_change
        self.current_id = None

        root = QHBoxLayout(self)

        # --- Left pane: monster list ---------------------------------------
        left = QVBoxLayout()
        self.monster_list = QListWidget()
        self.monster_list.currentItemChanged.connect(self._on_select)
        self.add_btn = QPushButton("New Monster")
        self.add_btn.clicked.connect(self._on_new)
        self.delete_btn = QPushButton("Delete Monster")
        self.delete_btn.clicked.connect(self._on_delete)
        left.addWidget(QLabel("Monsters"))
        left.addWidget(self.monster_list, 1)
        left.addWidget(self.add_btn)
        left.addWidget(self.delete_btn)
        root.addLayout(left, 1)

        # --- Right pane: statblock form -------------------------------------
        form_box = QGroupBox("Monster Statblock")
        form = QFormLayout(form_box)
        self.name_edit = QLineEdit()
        self.cr_edit = QLineEdit()
        self.cr_edit.setPlaceholderText("e.g. 1/2, 3, 14")
        self.link_edit = QLineEdit()
        self.link_edit.setPlaceholderText("https://... (optional statblock link)")
        self.ac_edit = QLineEdit()
        self.hp_edit = QLineEdit()
        self.speed_edit = QLineEdit()
        self.abilities_edit = QLineEdit()
        self.abilities_edit.setPlaceholderText("e.g. STR 14, DEX 12, CON 14, INT 8, WIS 10, CHA 8")
        self.details_edit = QPlainTextEdit()
        self.details_edit.setFixedHeight(160)

        form.addRow("Name", self.name_edit)
        form.addRow("CR", self.cr_edit)
        form.addRow("Statblock Link", self.link_edit)
        form.addRow("AC", self.ac_edit)
        form.addRow("HP", self.hp_edit)
        form.addRow("Speed", self.speed_edit)
        form.addRow("Abilities", self.abilities_edit)
        form.addRow("Traits / Actions", self.details_edit)

        self.save_btn = QPushButton("Save Monster")
        self.save_btn.clicked.connect(self._on_save)
        form.addRow(self.save_btn)

        self.status = QLabel("Create a monster to get started.")
        form.addRow(self.status)
        root.addWidget(form_box, 2)

    def refresh(self):
        """Full refresh of the monster list and statblock form."""
        self.refresh_list()
        self.refresh_form()

    def refresh_list(self):
        """Rebuild the monster list, showing CR in the row label when set."""
        self.monster_list.blockSignals(True)
        self.monster_list.clear()
        for monster in self.store[C.MONSTERS]:
            cr = monster.get("cr", "")
            label = f"{monster['name']}  (CR {cr})" if cr else monster["name"]
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, monster["id"])
            self.monster_list.addItem(item)
        self.monster_list.blockSignals(False)
        if self.monster_list.count() > 0 and self.current_id is None:
            self.monster_list.setCurrentRow(0)

    def refresh_form(self):
        """Fill the form from the selected monster, or reset for a new one."""
        if self.current_id is None:
            self._clear_form()
            self.status.setText("Create a monster to get started.")
            return
        monster = self._find(self.current_id)
        if not monster:
            return
        self.name_edit.setText(monster.get("name", ""))
        self.cr_edit.setText(monster.get("cr", ""))
        self.link_edit.setText(monster.get("link", ""))
        self.ac_edit.setText(monster.get("ac", ""))
        self.hp_edit.setText(monster.get("hp", ""))
        self.speed_edit.setText(monster.get("speed", ""))
        self.abilities_edit.setText(monster.get("abilities", ""))
        self.details_edit.setPlainText(monster.get("details", ""))
        self.status.setText(f"Editing {monster['name']}")

    def _clear_form(self):
        for edit in (self.name_edit, self.cr_edit, self.link_edit,
                     self.ac_edit, self.hp_edit, self.speed_edit, self.abilities_edit):
            edit.clear()
        self.details_edit.clear()

    def _find(self, monster_id):
        return self.store.find(C.MONSTERS, monster_id)

    def _on_select(self, current, _previous):
        if current is None:
            self.current_id = None
            self._clear_form()
            return
        self.current_id = current.data(Qt.ItemDataRole.UserRole)
        self.refresh_form()

    def _on_new(self):
        self.current_id = None
        self.monster_list.setCurrentItem(None)
        self._clear_form()
        self.name_edit.setFocus()
        self.status.setText("New monster - fill in the fields and press Save Monster.")

    def _on_save(self):
        """Create or update a monster from the form values."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, C.APP_NAME, "A monster needs a name.")
            return
        values = {
            "name": name,
            "cr": self.cr_edit.text().strip(),
            "link": self.link_edit.text().strip(),
            "ac": self.ac_edit.text().strip(),
            "hp": self.hp_edit.text().strip(),
            "speed": self.speed_edit.text().strip(),
            "abilities": self.abilities_edit.text().strip(),
            "details": self.details_edit.toPlainText().strip(),
        }
        if self.current_id is None:
            monster = {"id": C.new_id(), **values}
            self.store.add(C.MONSTERS, monster)
            self.current_id = monster["id"]
        else:
            monster = self._find(self.current_id)
            monster.update(values)
        self.refresh_list()
        self.refresh_form()
        self.on_change()
        self.status.setText(f"Saved {name}.")

    def _on_delete(self):
        if self.current_id is None:
            return
        monster = self._find(self.current_id)
        answer = QMessageBox.question(
            self,
            C.APP_NAME,
            f"Delete monster '{monster['name']}'?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.remove(C.MONSTERS, self.current_id)
        self.current_id = None
        self.refresh()
        self.on_change()
