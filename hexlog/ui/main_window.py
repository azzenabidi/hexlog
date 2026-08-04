"""Main application window wiring the tabs together."""

from PySide6.QtWidgets import QMainWindow, QTabWidget

from hexlog import constants as C
from hexlog.storage import Store
from hexlog.ui.entities import CharactersTab, LocationsTab, MonsterTab, NPCsTab
from hexlog.ui.notes import NotesTab
from hexlog.ui.vtt import MapsTab


class MainWindow(QMainWindow):
    """Top-level window hosting all the tabs on a shared data store."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(C.APP_NAME)
        self.resize(1200, 780)
        # One store shared by every tab; a single save() persists all changes.
        self.store = Store()

        self.tabs = QTabWidget()
        self.characters_tab = CharactersTab(self.store, self.save_and_refresh)
        self.npcs_tab = NPCsTab(self.store, self.save_and_refresh)
        self.locations_tab = LocationsTab(self.store, self.save_and_refresh)
        self.monsters_tab = MonsterTab(self.store, self.save_and_refresh)
        self.notes_tab = NotesTab(self.store, self.save_and_refresh)
        self.maps_tab = MapsTab(self.store, self.save_and_refresh)
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
        """Persist changes and refresh every tab in one shot."""
        self.store.save()
        self.refresh()

    def refresh(self):
        self.characters_tab.refresh()
        self.npcs_tab.refresh()
        self.locations_tab.refresh()
        self.monsters_tab.refresh()
        self.notes_tab.refresh()
        self.maps_tab.refresh()

    def _on_tab_changed(self, index):
        """Re-sync the journal/VTT when the user switches to them."""
        if index == 4:
            self.notes_tab.refresh()
        elif index == 5:
            self.maps_tab.refresh()
