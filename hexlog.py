#!/usr/bin/env python3
"""Hexlog - solo RPG companion: characters, NPCs, locations, journal, and VTT scenes."""

import copy
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QPen,
    QPixmap,
    QTextCharFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Hexlog"
DATA_DIR = os.path.join(os.path.expanduser("~"), ".hexlog")
LEGACY_DATA_DIR = os.path.join(os.path.expanduser("~"), ".solo_dnd")
DATA_FILE = os.path.join(DATA_DIR, "data.json")
MAPS_DIR = os.path.join(DATA_DIR, "maps")

COLOR_PALETTE = [
    "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c", "#3498db",
    "#9b59b6", "#e84393", "#16a085", "#d35400", "#8e44ad", "#2980b9",
]

DEFAULT_DATA = {"characters": [], "npcs": [], "locations": [], "monsters": [], "notes": [], "scenes": []}


def ensure_dirs():
    if not os.path.exists(DATA_DIR) and os.path.isdir(LEGACY_DATA_DIR):
        try:
            shutil.copytree(LEGACY_DATA_DIR, DATA_DIR)
        except Exception:
            pass
    os.makedirs(MAPS_DIR, exist_ok=True)


def load_data():
    ensure_dirs()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        data = copy.deepcopy(DEFAULT_DATA)
    for key in DEFAULT_DATA:
        data.setdefault(key, [])
    for scene in data.get("scenes", []):
        mp = scene.get("map_path")
        if mp and os.path.isabs(mp) and mp.startswith(LEGACY_DATA_DIR + os.sep):
            scene["map_path"] = os.path.basename(mp)
    return data


def save_data(data):
    ensure_dirs()
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def next_color(entities):
    return COLOR_PALETTE[len(entities) % len(COLOR_PALETTE)]


def short_label(name):
    if not name:
        return "?"
    word = name.strip().split()[0]
    if len(word) <= 7:
        return word
    words = name.strip().split()
    return "".join(w[0] for w in words[:2])


def kind_label(kind):
    if kind == "npc":
        return "NPC"
    if kind == "location":
        return "Location"
    return "Character"


class MentionHighlighter:
    def __init__(self, edit, get_entities):
        self.edit = edit
        self.get_entities = get_entities
        self.rules = []

    def refresh(self):
        self.rules = []
        for entity in self.get_entities():
            name = entity.get("name", "")
            if name:
                self.rules.append(
                    (re.compile(r"\b" + re.escape(name) + r"\b"), entity.get("color", "#888"))
                )

    def rehighlight(self):
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


class EntityTab(QWidget):
    def __init__(self, data, on_change, kind, extra_fields, list_label, form_title, entity_label):
        super().__init__()
        self.data = data
        self.on_change = on_change
        self.kind = kind
        self.extra_fields = extra_fields
        self.entity_label = entity_label
        self.current_id = None

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self.entity_list = QListWidget()
        self.entity_list.currentItemChanged.connect(self._on_select)
        self.add_btn = QPushButton(f"New {entity_label}")
        self.add_btn.clicked.connect(self._on_new)
        left.addWidget(QLabel(list_label))
        left.addWidget(self.entity_list, 1)
        left.addWidget(self.add_btn)
        root.addLayout(left, 1)

        form_box = QGroupBox(form_title)
        form = QFormLayout(form_box)
        self.name_edit = QLineEdit()
        self.extra_edits = {}
        self.desc_edit = QPlainTextEdit()
        self.desc_edit.setFixedHeight(140)
        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(70)
        self.color_btn.clicked.connect(self._pick_color)
        self.color = QColor("#888888")

        form.addRow("Name", self.name_edit)
        for attr, label in self.extra_fields:
            edit = QLineEdit()
            self.extra_edits[attr] = edit
            form.addRow(label, edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Token Color", self.color_btn)

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
        self._update_color_button()

    def _entities(self):
        return self.data[self.kind]

    def _list_text(self, entity):
        extras = " / ".join(entity.get(attr) or "-" for attr, _ in self.extra_fields)
        return f"{entity['name']}  ({extras})"

    def refresh(self):
        self.refresh_list()
        self.refresh_form()

    def refresh_list(self):
        self.entity_list.blockSignals(True)
        self.entity_list.clear()
        for entity in self._entities():
            item = QListWidgetItem(self._list_text(entity))
            item.setData(Qt.ItemDataRole.UserRole, entity["id"])
            item.setForeground(QColor(entity.get("color", "#888")))
            self.entity_list.addItem(item)
        self.entity_list.blockSignals(False)
        if self.entity_list.count() > 0 and self.current_id is None:
            self.entity_list.setCurrentRow(0)

    def refresh_form(self):
        if self.current_id is None:
            self.name_edit.clear()
            for edit in self.extra_edits.values():
                edit.clear()
            self.desc_edit.clear()
            self.color = QColor("#888888")
            self._update_color_button()
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
        self._update_color_button()
        self.status.setText(f"Editing {entity['name']}")

    def _find(self, entity_id):
        for entity in self._entities():
            if entity["id"] == entity_id:
                return entity
        return None

    def _on_select(self, current, _previous):
        if current is None:
            self.current_id = None
            return
        self.current_id = current.data(Qt.ItemDataRole.UserRole)
        self.refresh_form()

    def _on_new(self):
        self.current_id = None
        self.entity_list.setCurrentItem(None)
        self.name_edit.clear()
        for edit in self.extra_edits.values():
            edit.clear()
        self.desc_edit.clear()
        self.color = QColor(next_color(self._entities()))
        self._update_color_button()
        self.name_edit.setFocus()
        self.status.setText(f"New {self.entity_label.lower()} - fill in the fields and press Save.")

    def _pick_color(self):
        chosen = QColorDialog.getColor(self.color, self, "Choose token color")
        if chosen.isValid():
            self.color = chosen
            self._update_color_button()

    def _update_color_button(self):
        self.color_btn.setStyleSheet(
            f"background-color: {self.color.name()}; border: 1px solid #333; border-radius: 4px;"
        )

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_NAME, f"A {self.entity_label.lower()} needs a name.")
            return
        if self.current_id is None:
            entity = {
                "id": uuid.uuid4().hex[:12],
                "name": name,
                "description": self.desc_edit.toPlainText().strip(),
                "color": self.color.name(),
            }
            for attr, _ in self.extra_fields:
                entity[attr] = self.extra_edits[attr].text().strip()
            self._entities().append(entity)
            self.current_id = entity["id"]
        else:
            entity = self._find(self.current_id)
            entity["name"] = name
            entity["description"] = self.desc_edit.toPlainText().strip()
            entity["color"] = self.color.name()
            for attr, _ in self.extra_fields:
                entity[attr] = self.extra_edits[attr].text().strip()
        self.refresh_list()
        self.refresh_form()
        self.on_change()
        self.status.setText(f"Saved {name}.")

    def _on_delete(self):
        if self.current_id is None:
            return
        entity = self._find(self.current_id)
        answer = QMessageBox.question(
            self,
            APP_NAME,
            f"Delete {entity['name']}? Existing notes and tokens keep their text.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.data[self.kind] = [e for e in self._entities() if e["id"] != self.current_id]
        self.current_id = None
        self.refresh()
        self.on_change()


class CharactersTab(EntityTab):
    def __init__(self, data, on_change):
        super().__init__(
            data,
            on_change,
            kind="characters",
            extra_fields=[("race", "Race"), ("class", "Class")],
            list_label="Characters",
            form_title="Character Details",
            entity_label="Character",
        )


class NPCsTab(EntityTab):
    def __init__(self, data, on_change):
        super().__init__(
            data,
            on_change,
            kind="npcs",
            extra_fields=[("role", "Role")],
            list_label="NPCs",
            form_title="NPC Details",
            entity_label="NPC",
        )


class LocationsTab(EntityTab):
    def __init__(self, data, on_change):
        super().__init__(
            data,
            on_change,
            kind="locations",
            extra_fields=[("type", "Type")],
            list_label="Locations",
            form_title="Location Details",
            entity_label="Location",
        )


class MonsterTab(QWidget):
    def __init__(self, data, on_change):
        super().__init__()
        self.data = data
        self.on_change = on_change
        self.current_id = None

        root = QHBoxLayout(self)

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
        self.refresh_list()
        self.refresh_form()

    def refresh_list(self):
        self.monster_list.blockSignals(True)
        self.monster_list.clear()
        for monster in self.data["monsters"]:
            cr = monster.get("cr", "")
            label = f"{monster['name']}  (CR {cr})" if cr else monster["name"]
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, monster["id"])
            self.monster_list.addItem(item)
        self.monster_list.blockSignals(False)
        if self.monster_list.count() > 0 and self.current_id is None:
            self.monster_list.setCurrentRow(0)

    def refresh_form(self):
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
        for monster in self.data["monsters"]:
            if monster["id"] == monster_id:
                return monster
        return None

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
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, APP_NAME, "A monster needs a name.")
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
            monster = {"id": uuid.uuid4().hex[:12], **values}
            self.data["monsters"].append(monster)
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
            APP_NAME,
            f"Delete monster '{monster['name']}'?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.data["monsters"] = [m for m in self.data["monsters"] if m["id"] != self.current_id]
        self.current_id = None
        self.refresh()
        self.on_change()


class TokenItem(QGraphicsRectItem):
    def __init__(self, entity_id, kind, name, color, diameter=46):
        super().__init__(-diameter / 2, -diameter / 2, diameter, diameter)
        self.entity_id = entity_id
        self.kind = kind
        self.name = name
        self.diameter = diameter
        self._label = short_label(name)
        self.setBrush(QBrush(QColor(color)))
        pen = QPen(QColor("#141414"), 2)
        if kind == "npc":
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(1)
        self.setToolTip(
            f"{kind_label(kind)}: {name}\n(drag to move, right-click to remove)"
        )

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        rect = QRectF(-self.diameter / 2, -self.diameter / 2, self.diameter, self.diameter)
        if self.kind == "location":
            painter.drawRect(rect)
        else:
            painter.drawEllipse(rect)
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSizeF(max(6.0, self.diameter * 0.22))
        painter.setFont(font)
        fm = QFontMetricsF(font)
        label = self._label
        if fm.horizontalAdvance(label) > self.diameter * 0.9:
            label = label[:2]
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "name": self.name,
            "color": self.brush().color().name(),
            "x": self.pos().x(),
            "y": self.pos().y(),
            "diameter": self.diameter,
        }


class MapView(QGraphicsView):
    def __init__(self, map_tab):
        super().__init__()
        self.map_tab = map_tab
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setScene(self.map_tab.scene)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, TokenItem):
                self.map_tab.remove_token(item)
            return
        if self.map_tab.pending_entity is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.map_tab.place_token(self.map_tab.pending_entity, scene_pos)
            self.map_tab.pending_entity = None
            self.map_tab.status.setText(
                "Click a character or NPC in the menu, then click the map to place."
            )
            return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class MapsTab(QWidget):
    def __init__(self, data, on_change):
        super().__init__()
        self.data = data
        self.on_change = on_change
        self.current_scene_id = None
        self.pending_entity = None
        self.scene = QGraphicsScene(self)
        self.background_item = None

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self.scene_list = QListWidget()
        self.scene_list.currentItemChanged.connect(self._on_scene_select)
        self.new_scene_btn = QPushButton("New Scene")
        self.new_scene_btn.clicked.connect(self._on_new_scene)
        self.rename_scene_btn = QPushButton("Rename Scene")
        self.rename_scene_btn.clicked.connect(self._on_rename_scene)
        self.delete_scene_btn = QPushButton("Delete Scene")
        self.delete_scene_btn.clicked.connect(self._on_delete_scene)
        left.addWidget(QLabel("Scenes"))
        left.addWidget(self.scene_list, 1)
        left.addWidget(self.new_scene_btn)
        left.addWidget(self.rename_scene_btn)
        left.addWidget(self.delete_scene_btn)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        toolbar = QHBoxLayout()
        self.load_map_btn = QPushButton("Load Map Image...")
        self.load_map_btn.clicked.connect(self._load_map)
        self.entity_menu = QComboBox()
        self.add_token_btn = QPushButton("Add Token To Map")
        self.add_token_btn.clicked.connect(self._on_add_token)
        self.save_scene_btn = QPushButton("Save Scene")
        self.save_scene_btn.clicked.connect(self._on_save_scene)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(lambda: self.view.scale(1 / 1.2, 1 / 1.2))
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(self.load_map_btn)
        toolbar.addWidget(self.entity_menu)
        toolbar.addWidget(self.add_token_btn)
        toolbar.addWidget(self.save_scene_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.fit_btn)
        right.addLayout(toolbar)

        self.view = MapView(self)
        self.view.setScene(self.scene)
        right.addWidget(self.view, 1)

        self.status = QLabel("Create a scene, load a map image, then place character or NPC tokens.")
        right.addWidget(self.status)
        root.addLayout(right, 4)

    def refresh(self):
        self.refresh_scene_list()
        self.refresh_entities()
        self.refresh_scene_view()

    def refresh_entities(self):
        current = self.entity_menu.currentData()
        self.entity_menu.blockSignals(True)
        self.entity_menu.clear()
        for ch in self.data["characters"]:
            self.entity_menu.addItem(
                f"{ch['name']} ({ch.get('race', '-')} / {ch.get('class', '-')})",
                dict(ch, kind="character"),
            )
        for npc in self.data["npcs"]:
            self.entity_menu.addItem(
                f"NPC: {npc['name']} ({npc.get('role', '-')})",
                dict(npc, kind="npc"),
            )
        if current is not None:
            index = self.entity_menu.findData(current)
            if index >= 0:
                self.entity_menu.setCurrentIndex(index)
        self.entity_menu.blockSignals(False)

    def refresh_scene_list(self):
        self.scene_list.blockSignals(True)
        self.scene_list.clear()
        for scene in self.data["scenes"]:
            item = QListWidgetItem(scene.get("name", "Unnamed scene"))
            item.setData(Qt.ItemDataRole.UserRole, scene["id"])
            self.scene_list.addItem(item)
        self.scene_list.blockSignals(False)
        if self.current_scene_id is not None:
            index = self._scene_index(self.current_scene_id)
            if index >= 0:
                self.scene_list.setCurrentRow(index)

    def _scene_index(self, scene_id):
        for i, scene in enumerate(self.data["scenes"]):
            if scene["id"] == scene_id:
                return i
        return -1

    def _find_scene(self, scene_id):
        for scene in self.data["scenes"]:
            if scene["id"] == scene_id:
                return scene
        return None

    def refresh_scene_view(self):
        self.scene.clear()
        self.background_item = None
        scene = self._find_scene(self.current_scene_id) if self.current_scene_id else None
        if scene is None:
            self.scene.setSceneRect(0, 0, 800, 600)
            self.scene.addRect(0, 0, 800, 600, QPen(QColor("#333")), QBrush(QColor("#1f1f1f")))
            self.status.setText("No scene selected. Create or pick a scene, then load a map image.")
            return
        map_path = scene.get("map_path")
        if map_path and not os.path.isabs(map_path):
            map_path = os.path.join(MAPS_DIR, map_path)
        if map_path and os.path.exists(map_path):
            pixmap = QPixmap(map_path)
            if not pixmap.isNull():
                self.background_item = self.scene.addPixmap(pixmap)
                self.scene.setSceneRect(QRectF(pixmap.rect()))
        else:
            self.scene.setSceneRect(0, 0, 1000, 700)
            self.scene.addRect(0, 0, 1000, 700, QPen(QColor("#333")), QBrush(QColor("#1f1f1f")))
        for token in scene.get("tokens", []):
            self._restore_token(token)
        self.status.setText(f"Scene '{scene.get('name')}' - drag tokens, right-click to remove.")

    def _restore_token(self, token):
        item = TokenItem(
            token.get("entity_id", token.get("char_id")),
            token.get("kind", "character"),
            token.get("name", "?"),
            token.get("color", "#888"),
            token.get("diameter", 46),
        )
        item.setPos(token.get("x", 0), token.get("y", 0))
        self.scene.addItem(item)

    def _on_scene_select(self, current, _previous):
        if current is None:
            self.current_scene_id = None
        else:
            self.current_scene_id = current.data(Qt.ItemDataRole.UserRole)
        self.refresh_scene_view()

    def _on_new_scene(self):
        name, ok = QInputDialog.getText(self, "New Scene", "Scene name:")
        if not ok or not name.strip():
            return
        scene = {"id": uuid.uuid4().hex[:12], "name": name.strip(), "map_path": None, "tokens": []}
        self.data["scenes"].append(scene)
        self.current_scene_id = scene["id"]
        self.refresh_scene_list()
        self.refresh_scene_view()
        self.on_change()

    def _on_rename_scene(self):
        scene = self._find_scene(self.current_scene_id) if self.current_scene_id else None
        if scene is None:
            return
        name, ok = QInputDialog.getText(self, "Rename Scene", "Scene name:", text=scene["name"])
        if ok and name.strip():
            scene["name"] = name.strip()
            self.refresh_scene_list()
            self.refresh_scene_view()
            self.on_change()

    def _on_delete_scene(self):
        if self.current_scene_id is None:
            return
        scene = self._find_scene(self.current_scene_id)
        answer = QMessageBox.question(self, APP_NAME, f"Delete scene '{scene['name']}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.data["scenes"] = [s for s in self.data["scenes"] if s["id"] != self.current_scene_id]
        self.current_scene_id = None
        self.refresh_scene_list()
        self.refresh_scene_view()
        self.on_change()

    def _load_map(self):
        if self.current_scene_id is None:
            QMessageBox.information(self, APP_NAME, "Create a scene first, then load a map image.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose map image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)",
        )
        if not path:
            return
        dest = os.path.join(MAPS_DIR, f"{uuid.uuid4().hex[:8]}{os.path.splitext(path)[1]}")
        shutil.copy(path, dest)
        scene = self._find_scene(self.current_scene_id)
        scene["map_path"] = os.path.basename(dest)
        self.refresh_scene_view()
        self._fit_view()
        self.on_change()

    def _on_add_token(self):
        if self.current_scene_id is None:
            QMessageBox.information(self, APP_NAME, "Create a scene first.")
            return
        entity = self.entity_menu.currentData()
        if entity is None:
            QMessageBox.information(self, APP_NAME, "Add some characters or NPCs first.")
            return
        if self.pending_entity is None:
            self.pending_entity = entity
            self.status.setText(f"Place '{entity['name']}' by clicking the map. Right-click to cancel.")
        else:
            self.pending_entity = None
            self.status.setText("Placement cancelled.")

    def place_token(self, entity, scene_pos):
        item = TokenItem(entity["id"], entity.get("kind", "character"), entity["name"], entity["color"])
        item.setPos(scene_pos)
        self.scene.addItem(item)
        self.status.setText(f"Placed {entity['name']}. Drag to reposition, right-click to remove.")

    def remove_token(self, item):
        self.scene.removeItem(item)
        self.status.setText(f"Removed {item.name}.")

    def _fit_view(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _on_save_scene(self):
        if self.current_scene_id is None:
            return
        scene = self._find_scene(self.current_scene_id)
        tokens = []
        for item in self.scene.items():
            if isinstance(item, TokenItem):
                tokens.append(item.to_dict())
        scene["tokens"] = tokens
        self.on_change()
        self.status.setText(f"Scene '{scene['name']}' saved with {len(tokens)} token(s).")


class NotesTab(QWidget):
    def __init__(self, data, on_change):
        super().__init__()
        self.data = data
        self.on_change = on_change
        self.current_note_id = None

        root = QHBoxLayout(self)

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

        right = QVBoxLayout()
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
            lambda: self.data["characters"] + self.data["npcs"] + self.data["locations"],
        )
        self.editor.textChanged.connect(self.highlighter.rehighlight)

    def refresh(self):
        self.refresh_entity_bar()
        self.refresh_note_list()
        self.highlighter.rehighlight()

    def refresh_entity_bar(self):
        while self.char_bar_layout.count():
            item = self.char_bar_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._add_entity_rows(self.data["characters"], prefix="")
        self._add_entity_rows(self.data["npcs"], prefix="NPC ")
        self._add_entity_rows(self.data["locations"], prefix="Location ")
        if not self.data["characters"] and not self.data["npcs"] and not self.data["locations"]:
            empty = QLabel(
                "No characters, NPCs, or locations yet - add them in the Characters/NPCs/Locations tabs to reference them here."
            )
            empty.setStyleSheet("color: #888;")
            self.char_bar_layout.addWidget(empty)

    def _add_entity_rows(self, entities, prefix=""):
        for entity in entities:
            row = QHBoxLayout()
            color = QColor(entity.get("color", "#888"))
            name_label = QLabel(prefix + entity["name"])
            name_label.setStyleSheet(f"color: {color.name()}; font-weight: bold;")
            dialogue_btn = QPushButton(f'{entity["name"]}: "...')
            dialogue_btn.clicked.connect(lambda _=False, n=entity["name"]: self._insert_dialogue(n))
            mention_btn = QPushButton("@mention")
            mention_btn.clicked.connect(lambda _=False, n=entity["name"]: self._insert_mention(n))
            row.addWidget(name_label)
            row.addWidget(dialogue_btn)
            row.addWidget(mention_btn)
            row.addStretch(1)
            container = QWidget()
            container.setLayout(row)
            self.char_bar_layout.addWidget(container)

    def refresh_note_list(self):
        self.note_list.blockSignals(True)
        self.note_list.clear()
        for note in self.data["notes"]:
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
        for i, note in enumerate(self.data["notes"]):
            if note["id"] == note_id:
                return i
        return -1

    def _find_note(self, note_id):
        for note in self.data["notes"]:
            if note["id"] == note_id:
                return note
        return None

    def _insert_dialogue(self, name):
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
        text = self.editor.toPlainText().strip()
        if not text and not self.title_edit.text().strip():
            self.status.setText("Nothing to save.")
            return
        char_refs = [
            ch["id"] for ch in self.data["characters"] if ch["name"] and ch["name"] in text
        ]
        npc_refs = [
            npc["id"] for npc in self.data["npcs"] if npc["name"] and npc["name"] in text
        ]
        loc_refs = [
            loc["id"] for loc in self.data["locations"] if loc["name"] and loc["name"] in text
        ]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = self.title_edit.text().strip()
        if self.current_note_id is None:
            note = {
                "id": uuid.uuid4().hex[:12],
                "title": title,
                "text": text,
                "timestamp": timestamp,
                "char_ids": char_refs,
                "npc_ids": npc_refs,
                "loc_ids": loc_refs,
            }
            self.data["notes"].insert(0, note)
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
        answer = QMessageBox.question(self, APP_NAME, "Delete this note?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.data["notes"] = [n for n in self.data["notes"] if n["id"] != self.current_note_id]
        self.current_note_id = None
        self.refresh_note_list()
        self.editor.clear()
        self.title_edit.clear()
        self.status.setText("Note deleted.")
        self.on_change()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 780)
        self.data = load_data()

        self.tabs = QTabWidget()
        self.characters_tab = CharactersTab(self.data, self.save_and_refresh)
        self.npcs_tab = NPCsTab(self.data, self.save_and_refresh)
        self.locations_tab = LocationsTab(self.data, self.save_and_refresh)
        self.monsters_tab = MonsterTab(self.data, self.save_and_refresh)
        self.notes_tab = NotesTab(self.data, self.save_and_refresh)
        self.maps_tab = MapsTab(self.data, self.save_and_refresh)
        self.tabs.addTab(self.characters_tab, "Characters")
        self.tabs.addTab(self.npcs_tab, "NPCs")
        self.tabs.addTab(self.locations_tab, "Locations")
        self.tabs.addTab(self.monsters_tab, "Monsters")
        self.tabs.addTab(self.notes_tab, "Journal")
        self.tabs.addTab(self.maps_tab, "VTT")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self.statusBar().showMessage(
            "Hexlog - characters, NPCs, locations, monsters, journal, VTT tokens. Data saved to ~/.hexlog/"
        )
        self.refresh()

    def save_and_refresh(self):
        save_data(self.data)
        self.refresh()

    def refresh(self):
        self.characters_tab.refresh()
        self.npcs_tab.refresh()
        self.locations_tab.refresh()
        self.monsters_tab.refresh()
        self.notes_tab.refresh()
        self.maps_tab.refresh()

    def _on_tab_changed(self, index):
        if index == 4:
            self.notes_tab.refresh()
        elif index == 5:
            self.maps_tab.refresh()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
