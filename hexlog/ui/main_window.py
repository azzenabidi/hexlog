"""Main application window wiring the tabs together."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
)

from hexlog import __version__, constants as C
from hexlog.storage import Store
from hexlog.ui.entities import CharactersTab, LocationsTab, MonsterTab, NPCsTab
from hexlog.ui.notes import NotesTab
from hexlog.ui.oracle_dialog import OracleDialog
from hexlog.ui.theme import get_theme_stylesheet, toggle_theme_name
from hexlog.ui.update_dialog import ReleaseNotesDialog, UpdateDialog
from hexlog.ui.vtt import MapsTab
from hexlog.updater import load_and_clear_release_notes


def save_error_message(error):
    """Human-readable explanation of a failed save for the status bar."""
    return f"Could not save your data: {error}"


def flush_and_report(store, notify):
    """Persist `store`, reporting failures through `notify`.

    A disk-full or permission error must not raise inside a Qt timer slot,
    where nothing could catch it. Returns True when the save succeeded.
    """
    try:
        store.save()
    except OSError as error:
        notify(save_error_message(error))
        return False
    return True


class MainWindow(QMainWindow):
    """Top-level window hosting all the tabs on a shared data store.

    Every change in any tab funnels through on_change(), which debounces the
    save so typing stays responsive while the JSON is written to disk a moment
    after you stop editing.
    """

    AUTOSAVE_DELAY_MS = 600

    def __init__(self):
        super().__init__()
        self.setWindowTitle(C.APP_NAME)
        self.resize(1200, 780)
        self.theme_name = "dark"
        # One store shared by every tab; a single save() persists all changes.
        self.store = Store()
        if self.store.warnings:
            QMessageBox.warning(self, C.APP_NAME, "\n".join(self.store.warnings))

        self._pending_refresh = None  # tab that last reported a change
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(self.AUTOSAVE_DELAY_MS)
        self._save_timer.timeout.connect(self._flush)

        self._setup_theme_toggle()
        self._setup_help_menu()
        self.tabs = QTabWidget()
        self.characters_tab = CharactersTab(self.store, lambda: self._on_changed(self.characters_tab))
        self.npcs_tab = NPCsTab(self.store, lambda: self._on_changed(self.npcs_tab))
        self.locations_tab = LocationsTab(self.store, lambda: self._on_changed(self.locations_tab))
        self.monsters_tab = MonsterTab(self.store, lambda: self._on_changed(self.monsters_tab))
        self.notes_tab = NotesTab(self.store, lambda: self._on_changed(self.notes_tab))
        self.maps_tab = MapsTab(self.store, lambda: self._on_changed(self.maps_tab))
        self.tabs.addTab(self.characters_tab, "Characters")
        self.tabs.addTab(self.npcs_tab, "NPCs")
        self.tabs.addTab(self.locations_tab, "Locations")
        self.tabs.addTab(self.monsters_tab, "Monsters")
        self.tabs.addTab(self.notes_tab, "Journal")
        self.tabs.addTab(self.maps_tab, "VTT")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)
        self.maps_tab.set_theme(self.theme_name)
        self._setup_tools_menu()

        self.statusBar().showMessage(
            f"Hexlog - characters, NPCs, locations, monsters, journal, VTT tokens. "
            f"Data saved to ~/.config/hexlog/{C.DATA_SUBDIR}/"
        )
        self.refresh()

        # After a self-update the updater stashes the new release's notes
        # here; surface them once, once the event loop can show the dialog.
        release_notes = load_and_clear_release_notes()
        if release_notes:
            QTimer.singleShot(0, lambda: ReleaseNotesDialog(self, release_notes).show())

    def _setup_theme_toggle(self):
        toolbar = QToolBar("Theme")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.theme_action = QAction("☀ Light", self)
        self.theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.theme_action)

    def _setup_help_menu(self):
        menu = self.menuBar().addMenu("&Help")
        update_action = QAction("&Check for Updates…", self)
        update_action.triggered.connect(self._check_for_updates)
        menu.addAction(update_action)
        about_action = QAction("About Hexlog", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

    def _check_for_updates(self):
        """Open the update dialog, which may download and restart the app."""
        UpdateDialog(self).exec()

    def _setup_tools_menu(self):
        menu = self.menuBar().addMenu("&Tools")
        oracle_action = QAction("&Oracle…", self)
        oracle_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        oracle_action.triggered.connect(self._open_oracle)
        menu.addAction(oracle_action)

    def _open_oracle(self):
        """Open the oracle dialog; answers can be logged into the journal."""
        dialog = OracleDialog(self, insert_text=self.notes_tab.insert_text)
        dialog.exec()

    def _show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"About {C.APP_NAME}")
        layout = QVBoxLayout(dialog)
        title = QLabel(f"<h2>{C.APP_NAME} {__version__}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(
            "A solo RPG companion for D&D-style play: characters, NPCs, locations, "
            "monsters, a searchable journal, and a virtual tabletop with draggable "
            f"tokens. Everything autosaves to ~/.config/hexlog/{C.DATA_SUBDIR}/."
        )
        body.setWordWrap(True)
        link = QLabel(f'<a href="{C.GITHUB_URL}">{C.GITHUB_URL}</a>')
        link.setOpenExternalLinks(True)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(link)
        layout.addWidget(close_btn)
        dialog.exec()

    def toggle_theme(self):
        self.theme_name = toggle_theme_name(self.theme_name)
        self._apply_theme()

    def _apply_theme(self):
        stylesheet = get_theme_stylesheet(self.theme_name)
        self.setStyleSheet(stylesheet)
        self.theme_action.setText("☀ Light" if self.theme_name == "dark" else "🌙 Dark")
        self.maps_tab.set_theme(self.theme_name)

    def _on_changed(self, source):
        """Schedule a save; the tab that reported the change gets refreshed."""
        self._pending_refresh = source
        self._save_timer.start()

    def flush(self):
        """Persist and refresh immediately (used on close and structural ops)."""
        self._save_timer.stop()
        self._flush()

    def _flush(self):
        if not flush_and_report(self.store, self.statusBar().showMessage):
            return
        if self._pending_refresh is not None:
            self._pending_refresh.refresh()
            self._pending_refresh = None

    def refresh(self):
        self.characters_tab.refresh()
        self.npcs_tab.refresh()
        self.locations_tab.refresh()
        self.monsters_tab.refresh()
        self.notes_tab.refresh()
        self.maps_tab.refresh()

    def _on_tab_changed(self, index):
        """Re-sync the journal/VTT when the user switches to them."""
        widget = self.tabs.widget(index)
        if widget is self.notes_tab:
            self.notes_tab.refresh()
        elif widget is self.maps_tab:
            self.maps_tab.refresh()

    def closeEvent(self, event):
        """Make sure anything still debounced hits the disk."""
        self.flush()
        super().closeEvent(event)
