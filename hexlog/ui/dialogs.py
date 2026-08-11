"""Shared dialog helpers for the Hexlog UI."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidgetItem, QMessageBox

from hexlog import constants as C


def add_hint_item(list_widget, text):
    """Append a non-selectable placeholder row to a list widget."""
    item = QListWidgetItem(text)
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    item.setForeground(QColor(C.HINT_TEXT_COLOR))
    list_widget.addItem(item)


def confirm(parent, title, text):
    """Ask a yes/no question and return whether the user confirmed.

    User data (entity names, scene names) is interpolated into confirm
    prompts, so the default AutoText format - which treats `<...>` as HTML -
    is explicitly disabled to keep names from rendering as markup.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes
