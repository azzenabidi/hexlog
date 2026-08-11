"""Combat panel: initiative order, HP, and conditions for VTT tokens.

Sits at the bottom of the VTT tab and is thin glue over the pure combat
engine in hexlog.combat. It reads and mutates the scene's TokenItems
(which expose dict-style item access for the engine) and then calls a
persist() hook so the main window autosaves exactly as it does for token
moves.
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from hexlog import constants as C
from hexlog.combat import (
    apply_damage,
    apply_healing,
    combat_status,
    initiative_sort_key,
    next_combatant,
    roll_initiative,
    set_active,
    toggle_condition,
)


class CombatPanel(QWidget):
    """Bottom pane of the VTT tab.

    get_tokens() yields the scene's combatant objects (TokenItems) in scene
    order; persist() syncs them into the store and schedules a save.
    """

    def __init__(self, get_tokens, persist, parent=None):
        super().__init__(parent)
        self.get_tokens = get_tokens
        self.persist = persist
        self._order = []  # combatants in acting order

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        box = QGroupBox("Combat")
        layout = QVBoxLayout(box)

        buttons = QHBoxLayout()
        self.start_btn = QPushButton("Start Combat")
        self.start_btn.clicked.connect(self._start)
        self.next_btn = QPushButton("Next Turn")
        self.next_btn.clicked.connect(self._next)
        self.end_btn = QPushButton("End Combat")
        self.end_btn.clicked.connect(self._end)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.next_btn)
        buttons.addWidget(self.end_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.combat_list = QListWidget()
        self.combat_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.combat_list.currentItemChanged.connect(self._on_select)
        layout.addWidget(self.combat_list, 1)

        controls = QHBoxLayout()
        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(1, 999)
        self.hp_spin.setValue(1)
        self.damage_btn = QPushButton("- HP")
        self.damage_btn.clicked.connect(self._damage)
        self.heal_btn = QPushButton("+ HP")
        self.heal_btn.clicked.connect(self._heal)
        self.condition_edit = QLineEdit()
        self.condition_edit.setPlaceholderText("condition")
        self.condition_edit.returnPressed.connect(self._toggle_condition)
        self.condition_btn = QPushButton("Toggle")
        self.condition_btn.clicked.connect(self._toggle_condition)
        controls.addWidget(QLabel("Adjust:"))
        controls.addWidget(self.hp_spin)
        controls.addWidget(self.damage_btn)
        controls.addWidget(self.heal_btn)
        controls.addStretch(1)
        controls.addWidget(self.condition_edit)
        controls.addWidget(self.condition_btn)
        layout.addLayout(controls)

        root.addWidget(box)

    def refresh_scene(self):
        """Reload the combatant list from the scene, keeping acting order."""
        tokens = [t for t in self.get_tokens()]
        if any(t.get("initiative") is not None for t in tokens):
            self._order = sorted(tokens, key=initiative_sort_key, reverse=True)
        else:
            self._order = tokens
        self.refresh()

    def refresh(self):
        """Rebuild the list widget, preserving the current selection."""
        selected_id = self._selected_id()
        self.combat_list.blockSignals(True)
        self.combat_list.clear()
        for combatant in self._order:
            item = QListWidgetItem(self._row_text(combatant))
            item.setData(Qt.ItemDataRole.UserRole, combatant.get("id"))
            if combatant.get("is_active"):
                item.setForeground(QColor(C.SELECTION_COLOR))
            self.combat_list.addItem(item)
        if not self._order:
            hint = QListWidgetItem("Place tokens, then Start Combat.")
            hint.setFlags(Qt.ItemFlag.NoItemFlags)
            hint.setForeground(QColor(C.HINT_TEXT_COLOR))
            self.combat_list.addItem(hint)
        self.combat_list.blockSignals(False)
        self._select_id(selected_id)
        self._update_controls()

    def _row_text(self, combatant):
        prefix = "▶ " if combatant.get("is_active") else ""
        text = f"{prefix}{combatant.get('name', '?')} - {combat_status(combatant)}"
        if combatant.get("initiative") is not None:
            text += f" - init {combatant['initiative']}"
        conditions = ", ".join(combatant.get("conditions") or [])
        if conditions:
            text += f" - {conditions}"
        return text

    def _start(self):
        tokens = [t for t in self.get_tokens()]
        if not tokens:
            return
        self._order = roll_initiative(tokens)
        if self._order:
            set_active(self._order, self._order[0]["id"])
        self._persist_and_refresh()

    def _next(self):
        if not self._order:
            return
        active = next((c for c in self._order if c.get("is_active")), self._order[0])
        nxt = next_combatant(self._order, active["id"])
        set_active(self._order, nxt["id"])
        self._persist_and_refresh()

    def _end(self):
        set_active(self._order, None)
        self._persist_and_refresh()

    def _selected(self):
        token_id = self._selected_id()
        if token_id is None:
            return None
        for combatant in self._order:
            if combatant.get("id") == token_id:
                return combatant
        return None

    def _selected_id(self):
        item = self.combat_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _select_id(self, token_id):
        if token_id is None:
            return
        for i in range(self.combat_list.count()):
            if self.combat_list.item(i).data(Qt.ItemDataRole.UserRole) == token_id:
                self.combat_list.blockSignals(True)
                self.combat_list.setCurrentRow(i)
                self.combat_list.blockSignals(False)
                return

    def _update_controls(self):
        enabled = self._selected() is not None
        for widget in (self.hp_spin, self.damage_btn, self.heal_btn,
                       self.condition_edit, self.condition_btn):
            widget.setEnabled(enabled)

    def _damage(self):
        combatant = self._selected()
        if combatant is not None:
            apply_damage(combatant, self.hp_spin.value())
            self._persist_and_refresh()

    def _heal(self):
        combatant = self._selected()
        if combatant is not None:
            apply_healing(combatant, self.hp_spin.value())
            self._persist_and_refresh()

    def _toggle_condition(self):
        combatant = self._selected()
        condition = self.condition_edit.text().strip()
        if combatant is not None and condition:
            toggle_condition(combatant, condition)
            self.condition_edit.clear()
            self._persist_and_refresh()

    def _on_select(self, _current, _previous):
        self._update_controls()

    def _persist_and_refresh(self):
        self.persist()
        self.refresh()
