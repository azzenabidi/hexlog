"""Theme support for the Hexlog UI via data-driven palettes."""

from dataclasses import dataclass
from string import Template


@dataclass(frozen=True)
class ThemePalette:
    """Container for the colors that power a theme."""

    name: str
    window_bg: str
    window_text: str
    muted_text: str
    heading_text: str
    panel_bg: str
    panel_border: str
    input_bg: str
    input_border: str
    input_text: str
    input_selection_bg: str
    input_selection_text: str
    focus_border: str
    button_bg: str
    button_border: str
    button_text: str
    button_hover_bg: str
    button_hover_border: str
    button_pressed_bg: str
    button_disabled_text: str
    button_disabled_bg: str
    button_disabled_border: str
    default_button_bg: str
    default_button_border: str
    default_button_hover_bg: str
    tab_pane_bg: str
    tab_bg: str
    tab_border: str
    tab_text: str
    tab_selected_bg: str
    tab_selected_text: str
    tab_selected_border: str
    tab_hover_text: str
    scrollbar_handle: str
    scrollbar_handle_hover: str
    menu_bg: str
    menu_border: str
    menu_item_hover: str
    separator: str
    status_bg: str
    status_text: str
    tooltip_bg: str
    tooltip_border: str
    graphics_bg: str
    graphics_border: str
    accent: str


THEME_QSS_TEMPLATE = Template("""
QMainWindow, QWidget {
    background-color: $window_bg;
    color: $window_text;
    font-size: 13px;
}
QDialog, QMessageBox {
    background-color: $window_bg;
}
QLabel {
    color: $muted_text;
}
QLabel#heading {
    font-size: 15px;
    font-weight: 700;
    color: $heading_text;
}
QGroupBox {
    background-color: $panel_bg;
    border: 1px solid $panel_border;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: $window_text;
}
QLineEdit, QPlainTextEdit, QComboBox {
    background-color: $input_bg;
    border: 1px solid $input_border;
    border-radius: 6px;
    padding: 5px 8px;
    color: $input_text;
    selection-background-color: $input_selection_bg;
    selection-color: $input_selection_text;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid $focus_border;
}
QLineEdit:disabled, QPlainTextEdit:disabled {
    color: $button_disabled_text;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: $input_bg;
    border: 1px solid $input_border;
    color: $input_text;
    selection-background-color: $input_selection_bg;
    selection-color: $input_selection_text;
    outline: 0;
}
QListWidget {
    background-color: $input_bg;
    border: 1px solid $input_border;
    border-radius: 8px;
    padding: 4px;
    outline: 0;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
    color: $input_text;
}
QListWidget::item:hover {
    background-color: $button_hover_bg;
}
QListWidget::item:selected {
    background-color: $input_selection_bg;
    color: $input_selection_text;
}
QPushButton {
    background-color: $button_bg;
    border: 1px solid $button_border;
    border-radius: 6px;
    padding: 6px 14px;
    color: $button_text;
}
QPushButton:hover {
    background-color: $button_hover_bg;
    border-color: $button_hover_border;
}
QPushButton:pressed {
    background-color: $button_pressed_bg;
}
QPushButton:disabled {
    color: $button_disabled_text;
    background-color: $button_disabled_bg;
    border-color: $button_disabled_border;
}
QPushButton:default {
    background-color: $default_button_bg;
    border: 1px solid $default_button_border;
    color: #ffffff;
}
QPushButton:default:hover {
    background-color: $default_button_hover_bg;
}
QTabWidget::pane {
    border: 1px solid $panel_border;
    border-radius: 8px;
    top: -1px;
    background-color: $window_bg;
}
QTabBar::tab {
    background-color: $tab_bg;
    border: 1px solid $tab_border;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 7px 16px;
    margin-right: 2px;
    color: $tab_text;
}
QTabBar::tab:selected {
    background-color: $tab_selected_bg;
    color: $tab_selected_text;
    border-top: 2px solid $accent;
}
QTabBar::tab:hover:!selected {
    color: $tab_hover_text;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: $scrollbar_handle;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: $scrollbar_handle_hover;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background: $scrollbar_handle;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: $scrollbar_handle_hover;
}
QScrollBar::add-line, QScrollBar::sub-line,
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
    border: none;
    height: 0;
    width: 0;
}
QMenu {
    background-color: $menu_bg;
    border: 1px solid $menu_border;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 24px;
    border-radius: 4px;
    color: $window_text;
}
QMenu::item:selected {
    background-color: $menu_item_hover;
}
QMenu::separator {
    height: 1px;
    background: $separator;
    margin: 4px 8px;
}
QStatusBar {
    background-color: $status_bg;
    color: $status_text;
}
QStatusBar::item {
    border: none;
}
QToolTip {
    background-color: $tooltip_bg;
    color: $window_text;
    border: 1px solid $tooltip_border;
    padding: 4px 8px;
}
QGraphicsView {
    background-color: $graphics_bg;
    border: 1px solid $graphics_border;
    border-radius: 8px;
}
QScrollArea {
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
""")


DARK_THEME = ThemePalette(
    name="dark",
    window_bg="#202225",
    window_text="#e6e7eb",
    muted_text="#c9ccd3",
    heading_text="#ffffff",
    panel_bg="#2b2d31",
    panel_border="#3a3d44",
    input_bg="#1a1c1f",
    input_border="#3a3d44",
    input_text="#e6e7eb",
    input_selection_bg="#343a63",
    input_selection_text="#ffffff",
    focus_border="#6c7cff",
    button_bg="#34363b",
    button_border="#3f424a",
    button_text="#e6e7eb",
    button_hover_bg="#3e4147",
    button_hover_border="#565b66",
    button_pressed_bg="#2a2c30",
    button_disabled_text="#6b6f78",
    button_disabled_bg="#2a2b2f",
    button_disabled_border="#33353b",
    default_button_bg="#5865f2",
    default_button_border="#5865f2",
    default_button_hover_bg="#6c7cff",
    tab_pane_bg="#202225",
    tab_bg="#2b2d31",
    tab_border="#3a3d44",
    tab_text="#9aa0a6",
    tab_selected_bg="#34363b",
    tab_selected_text="#ffffff",
    tab_selected_border="#6c7cff",
    tab_hover_text="#e6e7eb",
    scrollbar_handle="#3f424a",
    scrollbar_handle_hover="#565b66",
    menu_bg="#2b2d31",
    menu_border="#3a3d44",
    menu_item_hover="#343a63",
    separator="#3a3d44",
    status_bg="#1a1c1f",
    status_text="#9aa0a6",
    tooltip_bg="#2b2d31",
    tooltip_border="#3a3d44",
    graphics_bg="#1f1f1f",
    graphics_border="#3a3d44",
    accent="#6c7cff",
)

LIGHT_THEME = ThemePalette(
    name="light",
    window_bg="#f4f5f7",
    window_text="#1f2329",
    muted_text="#49505a",
    heading_text="#111827",
    panel_bg="#ffffff",
    panel_border="#d9dee8",
    input_bg="#ffffff",
    input_border="#cfd5df",
    input_text="#1f2329",
    input_selection_bg="#dbeafe",
    input_selection_text="#111827",
    focus_border="#4f46e5",
    button_bg="#e5e7eb",
    button_border="#cfd5df",
    button_text="#1f2329",
    button_hover_bg="#f3f4f6",
    button_hover_border="#9ca3af",
    button_pressed_bg="#d1d5db",
    button_disabled_text="#6b7280",
    button_disabled_bg="#f3f4f6",
    button_disabled_border="#e5e7eb",
    default_button_bg="#4f46e5",
    default_button_border="#4f46e5",
    default_button_hover_bg="#6366f1",
    tab_pane_bg="#f4f5f7",
    tab_bg="#e5e7eb",
    tab_border="#cfd5df",
    tab_text="#6b7280",
    tab_selected_bg="#ffffff",
    tab_selected_text="#111827",
    tab_selected_border="#4f46e5",
    tab_hover_text="#1f2329",
    scrollbar_handle="#cbd5e1",
    scrollbar_handle_hover="#94a3b8",
    menu_bg="#ffffff",
    menu_border="#cfd5df",
    menu_item_hover="#e0e7ff",
    separator="#cfd5df",
    status_bg="#f3f4f6",
    status_text="#4b5563",
    tooltip_bg="#ffffff",
    tooltip_border="#cfd5df",
    graphics_bg="#ffffff",
    graphics_border="#cfd5df",
    accent="#4f46e5",
)

THEMES = {"dark": DARK_THEME, "light": LIGHT_THEME}
THEME_QSS = THEME_QSS_TEMPLATE.substitute(**DARK_THEME.__dict__)


def get_theme_stylesheet(theme_name: str = "dark") -> str:
    """Return the requested stylesheet for the given theme name."""
    palette = THEMES.get(theme_name.lower(), DARK_THEME)
    return THEME_QSS_TEMPLATE.substitute(**palette.__dict__)


def toggle_theme_name(theme_name: str) -> str:
    """Flip between dark and light theme names."""
    return "light" if theme_name.lower() == "dark" else "dark"

