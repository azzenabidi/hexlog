"""Update dialogs: check GitHub for a newer build, download, and restart.

UpdateDialog owns the network work (on background QThreads), the progress
bar, and the decision to relaunch the AppImage; every mechanical step lives
in hexlog.updater so it stays testable without Qt. ReleaseNotesDialog shows
the notes of an applied update after the restarted app comes back up.
"""

import os

from PySide6.QtCore import QProcess, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from hexlog import __version__, constants as C
from hexlog.updater import (
    RELEASES_URL,
    appimage_path,
    download_to,
    is_newer,
    latest_release,
    open_url,
    replace_appimage,
    save_release_notes,
)


class _CheckThread(QThread):
    """Fetches the latest release; emits its result or the failure reason."""

    checked = Signal(object)
    failed = Signal(str)

    def __init__(self, opener, parent=None):
        super().__init__(parent)
        self._opener = opener

    def run(self):
        try:
            self.checked.emit(latest_release(RELEASES_URL, self._opener))
        except Exception as error:
            self.failed.emit(str(error))


class _DownloadThread(QThread):
    """Downloads the new AppImage over the running file, then applies it."""

    progress = Signal(int, int)
    applied = Signal()
    failed = Signal(str)

    def __init__(self, url, target, opener, parent=None):
        super().__init__(parent)
        self._url = url
        self._target = target
        self._opener = opener

    def run(self):
        try:
            temp = os.path.join(os.path.dirname(self._target), ".hexlog-update.download")
            download_to(self._url, temp, self._opener, self.progress.emit)
            replace_appimage(temp, self._target)
            self.applied.emit()
        except Exception as error:
            self.failed.emit(str(error))


class UpdateDialog(QDialog):
    """Check for a newer AppImage and, if asked, download and relaunch."""

    def __init__(self, parent=None, opener=None):
        super().__init__(parent)
        self.setWindowTitle("Check for Updates")
        self.setMinimumWidth(440)
        self._opener = opener or open_url
        self._release = None
        self._thread = None

        root = QVBoxLayout(self)
        self.status_label = QLabel("Checking for updates...")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        root.addWidget(self.progress)

        self.notes_edit = QTextEdit()
        self.notes_edit.setReadOnly(True)
        self.notes_edit.setVisible(False)
        self.notes_edit.setMinimumHeight(220)
        root.addWidget(self.notes_edit)

        buttons = QHBoxLayout()
        self.update_btn = QPushButton("Download & Update")
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self._start_update)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        buttons.addWidget(self.update_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        root.addLayout(buttons)

        self._start_check()

    def _start_check(self):
        self.progress.setRange(0, 0)  # indeterminate while checking
        self._thread = _CheckThread(self._opener, self)
        self._thread.checked.connect(self._on_checked)
        self._thread.failed.connect(self._on_failed)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_checked(self, release):
        self.progress.setRange(0, 100)
        self._release = release
        if release is None or not release.appimage_url:
            self.status_label.setText("The latest release has no AppImage to download.")
            return
        current = __version__
        if not is_newer(release.tag, current):
            self.status_label.setText(f"You're up to date (Hexlog {current}).")
            return
        self.status_label.setText(
            f"Hexlog {current} is installed.\n"
            f"A newer build, {release.tag}, is available."
        )
        self.notes_edit.setPlainText(release.notes)
        self.notes_edit.setVisible(True)
        self.update_btn.setVisible(True)

    def _on_failed(self, message):
        self.progress.setRange(0, 100)
        self.status_label.setText(f"Could not check for updates: {message}")
        self.close_btn.setEnabled(True)

    def _start_update(self):
        target = appimage_path()
        if not target or self._release is None:
            self.status_label.setText(
                "This copy of Hexlog was not installed as an AppImage, so it "
                f"can't update itself. Download the latest build from {C.GITHUB_URL}."
            )
            return
        self.update_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setText("Downloading the new AppImage...")
        self._thread = _DownloadThread(self._release.appimage_url, target, self._opener, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.applied.connect(self._on_applied)
        self._thread.failed.connect(self._on_download_failed)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_progress(self, received, total):
        if total:
            self.progress.setValue(int(received * 100 / total))
            self.status_label.setText(
                f"Downloading the new AppImage... {received // (1024 * 1024)}"
                f" of {total // (1024 * 1024)} MB"
            )
        else:
            self.progress.setValue(0)

    def _on_download_failed(self, message):
        self._on_failed(message)
        self.update_btn.setEnabled(True)

    def _on_applied(self):
        if self._release is not None:
            save_release_notes(self._release.notes)
        self.status_label.setText("Update applied. Restarting Hexlog...")
        QProcess.startDetached(appimage_path())
        QApplication.instance().quit()


class ReleaseNotesDialog(QDialog):
    """Shows what changed after a successful self-update."""

    def __init__(self, parent=None, notes=""):
        super().__init__(parent)
        self.setWindowTitle("Hexlog has been updated")
        self.resize(520, 420)
        root = QVBoxLayout(self)
        heading = QLabel("What's new in this release:")
        root.addWidget(heading)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(notes)
        root.addWidget(text, 1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
