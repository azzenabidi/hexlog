"""Update dialogs: check GitHub for a newer build, download, and restart.

UpdateDialog owns the network work (on background QThreads), the progress
bar, and the decision to relaunch the AppImage; every mechanical step lives
in hexlog.updater so it stays testable without Qt. When a newer release is
found the dialog shows a release card - version, published date, download
size, and the release notes rendered as formatted markdown - instead of a
bare link. ReleaseNotesDialog shows the notes of an applied update after
the restarted app comes back up.
"""

import os
import uuid

from PySide6.QtCore import QProcess, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from hexlog import __version__, constants as C
from hexlog.markdown import render_markdown
from hexlog.updater import (
    RELEASES_URL,
    appimage_path,
    download_to,
    format_size,
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
            unique = f".hexlog-update.{uuid.uuid4().hex[:8]}.download"
            temp = os.path.join(os.path.dirname(self._target), unique)
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
        self.setMinimumWidth(480)
        self._opener = opener or open_url
        self._release = None
        self._thread = None

        root = QVBoxLayout(self)
        self.status_label = QLabel("Checking for updates...")
        self.status_label.setWordWrap(True)
        self.status_label.setOpenExternalLinks(True)
        root.addWidget(self.status_label)

        self.release_heading = QLabel("")
        self.release_heading.setObjectName("heading")
        self.release_heading.setVisible(False)
        root.addWidget(self.release_heading)

        self.release_meta = QLabel("")
        self.release_meta.setWordWrap(True)
        self.release_meta.setTextFormat(Qt.TextFormat.RichText)
        self.release_meta.setOpenExternalLinks(True)
        self.release_meta.setVisible(False)
        root.addWidget(self.release_meta)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        root.addWidget(self.progress)

        self.notes_browser = QTextBrowser()
        self.notes_browser.setOpenExternalLinks(True)
        self.notes_browser.setMinimumHeight(240)
        self.notes_browser.setVisible(False)
        root.addWidget(self.notes_browser, 1)

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
            self.status_label.setText(
                "The latest release has no AppImage to download. "
                f'<a href="{C.GITHUB_URL}/releases/latest">See the release on GitHub.</a>'
            )
            return
        current = __version__
        if not is_newer(release.tag, current):
            # One window handles both outcomes: the check dialog itself says
            # you're up to date instead of stacking a second message box.
            self.progress.setVisible(False)
            self.status_label.setText(f"You're up to date (Hexlog {current}).")
            return
        self.status_label.setText(f"Hexlog {current} is installed.")
        self.release_heading.setText(f"Hexlog {release.tag} is available")
        self.release_meta.setText(self._release_meta(release))
        self.notes_browser.setHtml(render_markdown(release.notes))
        for widget in (self.release_heading, self.release_meta, self.notes_browser, self.update_btn):
            widget.setVisible(True)

    def _release_meta(self, release):
        """Meta line for the release card: date, size, and the release page."""
        parts = []
        if release.published_at:
            parts.append(f"Released {release.published_at[:10]}")
        if release.size:
            parts.append(format_size(release.size))
        if release.html_url:
            parts.append(f'<a href="{release.html_url}">open release page</a>')
        return "  ·  ".join(parts)

    def _on_failed(self, message):
        self.progress.setRange(0, 100)
        self.status_label.setText(f"Could not check for updates: {message}")
        self.close_btn.setEnabled(True)

    def _start_update(self):
        target = appimage_path()
        if not target or self._release is None:
            self.status_label.setText(
                "This copy of Hexlog was not installed as an AppImage, so it "
                f'can\'t update itself. Download the latest build from '
                f'<a href="{C.GITHUB_URL}">{C.GITHUB_URL}</a>.'
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
            try:
                save_release_notes(self._release.notes)
            except OSError:
                pass  # notes are a nicety; the update itself already succeeded
        parent = self.parent()
        if parent is not None and hasattr(parent, "flush"):
            parent.flush()  # persist anything still inside the autosave debounce
        if not QProcess.startDetached(appimage_path()):
            self.status_label.setText(
                "Update applied, but Hexlog could not restart. "
                "Please relaunch it manually."
            )
            self.update_btn.setEnabled(True)
            self.close_btn.setEnabled(True)
            return
        if self._thread is not None:
            self._thread.wait()
        self.status_label.setText("Update applied. Restarting Hexlog...")
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            event.ignore()
            return
        super().closeEvent(event)

    def reject(self):
        if self._thread is not None and self._thread.isRunning():
            return
        super().reject()


class ReleaseNotesDialog(QDialog):
    """Shows what changed after a successful self-update."""

    def __init__(self, parent=None, notes=""):
        super().__init__(parent)
        self.setWindowTitle("Hexlog has been updated")
        self.resize(540, 460)
        root = QVBoxLayout(self)
        heading = QLabel("What's new in this release")
        heading.setObjectName("heading")
        root.addWidget(heading)
        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setHtml(render_markdown(notes))
        root.addWidget(text, 1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
