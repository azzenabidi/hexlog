"""Cohesive dark theme applied app-wide via a single stylesheet."""

THEME_QSS = """
QMainWindow, QWidget {
    background-color: #202225;
    color: #e6e7eb;
    font-size: 13px;
}
QDialog, QMessageBox {
    background-color: #202225;
}
QLabel {
    color: #c9ccd3;
}
QLabel#heading {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
}
QGroupBox {
    background-color: #2b2d31;
    border: 1px solid #3a3d44;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #e6e7eb;
}
QLineEdit, QPlainTextEdit, QComboBox {
    background-color: #1a1c1f;
    border: 1px solid #3a3d44;
    border-radius: 6px;
    padding: 5px 8px;
    color: #e6e7eb;
    selection-background-color: #4f5aa6;
    selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #6c7cff;
}
QLineEdit:disabled, QPlainTextEdit:disabled {
    color: #6b6f78;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #1a1c1f;
    border: 1px solid #3a3d44;
    color: #e6e7eb;
    selection-background-color: #343a63;
    selection-color: #ffffff;
    outline: 0;
}
QListWidget {
    background-color: #1a1c1f;
    border: 1px solid #3a3d44;
    border-radius: 8px;
    padding: 4px;
    outline: 0;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
    color: #e6e7eb;
}
QListWidget::item:hover {
    background-color: #2f3136;
}
QListWidget::item:selected {
    background-color: #343a63;
    color: #ffffff;
}
QPushButton {
    background-color: #34363b;
    border: 1px solid #3f424a;
    border-radius: 6px;
    padding: 6px 14px;
    color: #e6e7eb;
}
QPushButton:hover {
    background-color: #3e4147;
    border-color: #565b66;
}
QPushButton:pressed {
    background-color: #2a2c30;
}
QPushButton:disabled {
    color: #6b6f78;
    background-color: #2a2b2f;
    border-color: #33353b;
}
QPushButton:default {
    background-color: #5865f2;
    border: 1px solid #5865f2;
    color: #ffffff;
}
QPushButton:default:hover {
    background-color: #6c7cff;
}
QTabWidget::pane {
    border: 1px solid #3a3d44;
    border-radius: 8px;
    top: -1px;
    background-color: #202225;
}
QTabBar::tab {
    background-color: #2b2d31;
    border: 1px solid #3a3d44;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 16px;
    margin-right: 2px;
    color: #9aa0a6;
}
QTabBar::tab:selected {
    background-color: #34363b;
    color: #ffffff;
    border-top: 2px solid #6c7cff;
}
QTabBar::tab:hover:!selected {
    color: #e6e7eb;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3f424a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #565b66;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: #3f424a;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #565b66;
}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
    border: none;
    height: 0;
    width: 0;
}
QMenu {
    background-color: #2b2d31;
    border: 1px solid #3a3d44;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
    color: #e6e7eb;
}
QMenu::item:selected {
    background-color: #343a63;
}
QMenu::separator {
    height: 1px;
    background: #3a3d44;
    margin: 4px 8px;
}
QStatusBar {
    background-color: #1a1c1f;
    color: #9aa0a6;
}
QStatusBar::item {
    border: none;
}
QToolTip {
    background-color: #2b2d31;
    color: #e6e7eb;
    border: 1px solid #3a3d44;
    padding: 4px 8px;
}
QGraphicsView {
    background-color: #1f1f1f;
    border: 1px solid #3a3d44;
    border-radius: 8px;
}
QScrollArea {
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
"""
