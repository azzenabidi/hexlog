"""Virtual tabletop: token items, the map view, and scene management."""

import os
import shutil
import uuid

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hexlog import constants as C


def short_label(name):
    """Derive a compact token label: first word, or initials of the first two."""
    if not name:
        return "?"
    word = name.strip().split()[0]
    if len(word) <= 7:
        return word
    words = name.strip().split()
    return "".join(w[0] for w in words[:2])


def kind_label(kind):
    """Human-readable name of an entity kind for tooltips/status text."""
    if kind == "npc":
        return "NPC"
    if kind == "location":
        return "Location"
    return "Character"


def resize_diameter(center_x, center_y, drag_x, drag_y,
                    minimum=C.TOKEN_MIN_DIAMETER, maximum=C.TOKEN_MAX_DIAMETER):
    """New token diameter for a corner drag from the token center to `drag`.

    The handle grows the token symmetrically around its center, so the new
    diameter is twice the larger of the horizontal/vertical offset.
    """
    half = max(abs(drag_x - center_x), abs(drag_y - center_y))
    return max(minimum, min(maximum, int(2 * half)))


class TokenItem(QGraphicsRectItem):
    """A movable token on the VTT scene.

    Renders either the entity's image (characters/NPCs) clipped into the
    token's shape, or a plain colored circle/rect with an abbreviated label.
    The bounding rect is centered on the origin so setPos() places the
    token's center exactly where the user clicked.
    """

    def __init__(self, entity_id, kind, name, color, diameter=C.TOKEN_DIAMETER, image=None):
        super().__init__(-diameter / 2, -diameter / 2, diameter, diameter)
        self.entity_id = entity_id
        self.kind = kind
        self.name = name
        self.diameter = diameter
        self.image = image
        self._label = short_label(name)
        # Load the pixmap once at construction rather than every paint().
        self._pixmap = None
        if image:
            path = image if os.path.isabs(image) else os.path.join(C.TOKENS_DIR, image)
            if os.path.exists(path):
                pix = QPixmap(path)
                if not pix.isNull():
                    self._pixmap = pix
        self.setBrush(QBrush(QColor(color)))
        pen = QPen(QColor(C.TOKEN_BORDER_COLOR), 2)
        # NPCs use a dashed outline to visually stand apart from characters.
        if kind == "npc":
            pen.setStyle(Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self._resizing = False
        self._drag_center = None
        self.setZValue(1)  # tokens stay above the background map
        self.setToolTip(
            f"{kind_label(kind)}: {name}\n(drag to move, right-click to remove)"
        )

    def set_diameter(self, diameter):
        """Resize the token around its center, keeping its position fixed."""
        self.diameter = int(diameter)
        self.setRect(QRectF(-self.diameter / 2, -self.diameter / 2, self.diameter, self.diameter))
        self.update()

    def _handle_rect(self):
        """Square grab-handle drawn at the token's bottom-right corner."""
        size = max(10.0, self.diameter * 0.18)
        half = self.diameter / 2.0
        return QRectF(half - size / 2, half - size / 2, size, size)

    def _draw_handle(self, painter):
        if not self.isSelected():
            return
        painter.save()
        painter.setPen(QPen(QColor(C.TOKEN_BORDER_COLOR), 1))
        painter.setBrush(QColor("white"))
        painter.drawRect(self._handle_rect())
        painter.restore()

    def hoverMoveEvent(self, event):
        if self._handle_rect().contains(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.unsetCursor()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._handle_rect().contains(event.pos()):
            # The built-in move drag would fight the handle drag, so the token
            # is pinned in place while it is being resized around its center.
            self._resizing = True
            self._drag_center = self.scenePos()
            self.setSelected(True)
            self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, False)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            self.set_diameter(
                resize_diameter(
                    self._drag_center.x(), self._drag_center.y(),
                    event.scenePos().x(), event.scenePos().y(),
                )
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._drag_center = None
            self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(-self.diameter / 2, -self.diameter / 2, self.diameter, self.diameter)
        # Locations are drawn as squares; everything else as circles.
        if self.kind == "location":
            clip = QPainterPath()
            clip.addRect(rect)
        else:
            clip = QPainterPath()
            clip.addEllipse(rect)
        if self._pixmap is not None:
            # Image mode: clip to the shape, draw the image centered with
            # aspect preserved, then a plain border on top.
            painter.save()
            painter.setClipPath(clip)
            pix = self._pixmap
            scaled = pix.scaled(
                rect.width(), rect.height(),
                # Cover-crop: scale up until the whole token is filled, then
                # clip the overflow with the shape so there is no letterboxing.
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(
                int(rect.center().x() - scaled.width() / 2),
                int(rect.center().y() - scaled.height() / 2),
                scaled,
            )
            painter.restore()
            painter.setPen(self.pen())
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.kind == "location":
                painter.drawRect(rect)
            else:
                painter.drawEllipse(rect)
            self._draw_handle(painter)
            return
        # Fallback mode: colored shape with a short centered label.
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
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
        # Truncate to two chars if the label would overflow the token.
        if fm.horizontalAdvance(label) > self.diameter * 0.9:
            label = label[:2]
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        self._draw_handle(painter)

    def to_dict(self):
        """Serialize the token's current state for scene persistence."""
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "name": self.name,
            "color": self.brush().color().name(),
            "x": self.pos().x(),
            "y": self.pos().y(),
            "diameter": self.diameter,
            "image": self.image,
        }


class MapView(QGraphicsView):
    """View over the VTT scene, handling click-to-place and wheel zoom."""

    def __init__(self, map_tab):
        super().__init__()
        self.map_tab = map_tab
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setScene(self.map_tab.scene)
        self.setBackgroundBrush(QBrush(QColor(C.CANVAS_BACKGROUND)))

    def mousePressEvent(self, event):
        # Right-click on a token removes it.
        if event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, TokenItem):
                self.map_tab.remove_token(item)
            return
        # When a placement is pending, the next left-click drops the token.
        if self.map_tab.pending_entity is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.map_tab.place_token(self.map_tab.pending_entity, scene_pos)
            self.map_tab.pending_entity = None
            self.map_tab.status.setText(
                "Click a character or NPC in the menu, then click the map to place."
            )
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # A drag may have moved a token - persist its new position.
        super().mouseReleaseEvent(event)
        self.map_tab._sync_scene_tokens()
        self.map_tab.on_change()

    def wheelEvent(self, event):
        """Zoom in/out around the view center via the scroll wheel."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class MapsTab(QWidget):
    """VTT tab: manage scenes, load map images, and place/drag tokens."""

    def __init__(self, store, on_change):
        super().__init__()
        self.store = store
        self.on_change = on_change
        self.current_scene_id = None
        self.pending_entity = None  # set while waiting for a click to place a token
        self.scene = QGraphicsScene(self)
        self.background_item = None

        root = QHBoxLayout(self)

        # --- Left pane: scene management ------------------------------------
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

        # --- Right pane: map canvas and toolbar -----------------------------
        right = QVBoxLayout()
        toolbar = QHBoxLayout()
        self.load_map_btn = QPushButton("Load Map Image...")
        self.load_map_btn.clicked.connect(self._load_map)
        self.entity_menu = QComboBox()
        self.add_token_btn = QPushButton("Add Token To Map")
        self.add_token_btn.clicked.connect(self._on_add_token)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(lambda: self.view.scale(1.2, 1.2))
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(lambda: self.view.scale(1 / 1.2, 1 / 1.2))
        self.fit_btn = QPushButton("Fit")
        self.fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(self.load_map_btn)
        toolbar.addWidget(self.entity_menu)
        toolbar.addWidget(self.add_token_btn)
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
        """Refresh the scene list, entity menu, and the current scene view."""
        self.refresh_scene_list()
        self.refresh_entities()
        self.refresh_scene_view()

    def refresh_entities(self):
        """Populate the token dropdown with all characters and NPCs."""
        current = self.entity_menu.currentData()
        self.entity_menu.blockSignals(True)
        self.entity_menu.clear()
        for ch in self.store[C.CHARACTERS]:
            # The full entity dict rides along as item data so the pending
            # placement has everything it needs (id, name, color, image).
            self.entity_menu.addItem(
                f"{ch['name']} ({ch.get('race', '-')} / {ch.get('class', '-')})",
                dict(ch, kind="character"),
            )
        for npc in self.store[C.NPCS]:
            self.entity_menu.addItem(
                f"NPC: {npc['name']} ({npc.get('role', '-')})",
                dict(npc, kind="npc"),
            )
        # Restore the previous selection by value if it still exists.
        if current is not None:
            index = self.entity_menu.findData(current)
            if index >= 0:
                self.entity_menu.setCurrentIndex(index)
        self.entity_menu.blockSignals(False)

    def refresh_scene_list(self):
        """Rebuild the scene list, restoring the current selection."""
        self.scene_list.blockSignals(True)
        self.scene_list.clear()
        for scene in self.store[C.SCENES]:
            item = QListWidgetItem(scene.get("name", "Unnamed scene"))
            item.setData(Qt.ItemDataRole.UserRole, scene["id"])
            self.scene_list.addItem(item)
        if self.scene_list.count() == 0:
            hint = QListWidgetItem("No scenes yet - click New Scene.")
            hint.setFlags(Qt.ItemFlag.NoItemFlags)
            hint.setForeground(QColor(C.HINT_TEXT_COLOR))
            self.scene_list.addItem(hint)
        self.scene_list.blockSignals(False)
        if self.current_scene_id is not None:
            index = self._scene_index(self.current_scene_id)
            if index >= 0:
                self.scene_list.setCurrentRow(index)

    def _scene_index(self, scene_id):
        for i, scene in enumerate(self.store[C.SCENES]):
            if scene["id"] == scene_id:
                return i
        return -1

    def _find_scene(self, scene_id):
        return self.store.find(C.SCENES, scene_id)

    def refresh_scene_view(self):
        """Rebuild the QGraphicsScene for the current scene (map + tokens)."""
        self.scene.clear()
        self.background_item = None
        scene = self._find_scene(self.current_scene_id) if self.current_scene_id else None
        if scene is None:
            # Placeholder canvas so the view is never empty.
            self.scene.setSceneRect(0, 0, 800, 600)
            self.scene.addRect(
                0, 0, 800, 600,
                QPen(QColor(C.CANVAS_GRID_COLOR)), QBrush(QColor(C.CANVAS_BACKGROUND)),
            )
            self.status.setText("No scene selected. Create or pick a scene, then load a map image.")
            return
        # Map images are stored by basename and resolved against MAPS_DIR.
        map_path = scene.get("map_path")
        if map_path and not os.path.isabs(map_path):
            map_path = os.path.join(C.MAPS_DIR, map_path)
        if map_path and os.path.exists(map_path):
            pixmap = QPixmap(map_path)
            if not pixmap.isNull():
                self.background_item = self.scene.addPixmap(pixmap)
                # Scene bounds follow the map so Fit and zoom behave predictably.
                self.scene.setSceneRect(QRectF(pixmap.rect()))
        else:
            # No map loaded: default gray canvas.
            self.scene.setSceneRect(0, 0, 1000, 700)
            self.scene.addRect(
                0, 0, 1000, 700,
                QPen(QColor(C.CANVAS_GRID_COLOR)), QBrush(QColor(C.CANVAS_BACKGROUND)),
            )
        for token in scene.get("tokens", []):
            self._restore_token(token)
        self.status.setText(f"Scene '{scene.get('name')}' - drag tokens, right-click to remove.")

    def _restore_token(self, token):
        """Recreate a TokenItem from a saved scene dict."""
        item = TokenItem(
            token.get("entity_id", token.get("char_id")),  # char_id is the legacy key
            token.get("kind", "character"),
            token.get("name", "?"),
            token.get("color", C.DEFAULT_ENTITY_COLOR),
            token.get("diameter", C.TOKEN_DIAMETER),
            image=token.get("image"),
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
        scene = {"id": C.new_id(), "name": name.strip(), "map_path": None, "tokens": []}
        self.store.add(C.SCENES, scene)
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
        answer = QMessageBox.question(self, C.APP_NAME, f"Delete scene '{scene['name']}'?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.store.remove(C.SCENES, self.current_scene_id)
        self.current_scene_id = None
        self.refresh_scene_list()
        self.refresh_scene_view()
        self.on_change()

    def _load_map(self):
        """Pick a map image, copy it into MAPS_DIR, and attach it to the scene."""
        if self.current_scene_id is None:
            QMessageBox.information(self, C.APP_NAME, "Create a scene first, then load a map image.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Choose map image", "", C.IMAGE_FILTER)
        if not path:
            return
        # Random basename avoids collisions between identically named files.
        dest = os.path.join(C.MAPS_DIR, f"{uuid.uuid4().hex[:8]}{os.path.splitext(path)[1]}")
        try:
            shutil.copy(path, dest)
        except OSError:
            # Surface the failure rather than leaving the scene half-updated.
            QMessageBox.warning(
                self, C.APP_NAME, "Could not copy the map image into the app data folder."
            )
            return
        scene = self._find_scene(self.current_scene_id)
        scene["map_path"] = os.path.basename(dest)
        self.refresh_scene_view()
        self._fit_view()
        self.on_change()

    def _on_add_token(self):
        """Toggle 'place next click' mode for the entity in the dropdown."""
        if self.current_scene_id is None:
            QMessageBox.information(self, C.APP_NAME, "Create a scene first.")
            return
        entity = self.entity_menu.currentData()
        if entity is None:
            QMessageBox.information(self, C.APP_NAME, "Add some characters or NPCs first.")
            return
        if self.pending_entity is None:
            self.pending_entity = entity
            self.status.setText(f"Place '{entity['name']}' by clicking the map. Right-click to cancel.")
        else:
            # Clicking the button again toggles placement off.
            self.pending_entity = None
            self.status.setText("Placement cancelled.")

    def place_token(self, entity, scene_pos):
        """Drop a new token for the given entity at the scene position."""
        item = TokenItem(
            entity["id"],
            entity.get("kind", "character"),
            entity["name"],
            entity["color"],
            image=entity.get("image"),
        )
        item.setPos(scene_pos)
        self.scene.addItem(item)
        self._sync_scene_tokens()
        self.on_change()
        self.status.setText(f"Placed {entity['name']}. Drag to reposition, right-click to remove.")

    def remove_token(self, item):
        self.scene.removeItem(item)
        self._sync_scene_tokens()
        self.on_change()
        self.status.setText(f"Removed {item.name}.")

    def _sync_scene_tokens(self):
        """Write the current on-canvas token positions into the scene record."""
        if self.current_scene_id is None:
            return
        scene = self._find_scene(self.current_scene_id)
        if scene is None:
            return
        tokens = [i.to_dict() for i in self.scene.items() if isinstance(i, TokenItem)]
        scene["tokens"] = tokens

    def _fit_view(self):
        """Zoom to fit the whole scene in the viewport."""
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
