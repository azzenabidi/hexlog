"""Tests for the shared confirm dialog helper (no GUI required)."""

from PySide6.QtCore import Qt

from hexlog.ui.dialogs import confirm


class FakeBox:
    """Records how the QMessageBox is configured, so no GUI is created."""

    class StandardButton:
        Yes = 1
        No = 2

    instances = []
    answer = StandardButton.Yes

    def __init__(self, parent):
        self.fields = {}
        FakeBox.instances.append(self)

    def setWindowTitle(self, title):
        self.fields["title"] = title

    def setText(self, text):
        self.fields["text"] = text

    def setTextFormat(self, fmt):
        self.fields["format"] = fmt

    def setStandardButtons(self, buttons):
        self.fields["buttons"] = buttons

    def setDefaultButton(self, button):
        self.fields["default"] = button

    def exec(self):
        return self.answer


def test_confirm_renders_text_as_plain_text(monkeypatch):
    """Interpolated names must never be interpreted as HTML (AutoText)."""
    monkeypatch.setattr("hexlog.ui.dialogs.QMessageBox", FakeBox)
    FakeBox.instances = []
    FakeBox.answer = FakeBox.StandardButton.Yes

    assert confirm(None, "Hexlog", "Delete <Bad>?</Bad>") is True
    box = FakeBox.instances[-1]
    assert box.fields["title"] == "Hexlog"
    assert box.fields["text"] == "Delete <Bad>?</Bad>"
    assert box.fields["format"] == Qt.TextFormat.PlainText
    assert box.fields["default"] == FakeBox.StandardButton.No


def test_confirm_reports_no_when_denied(monkeypatch):
    monkeypatch.setattr("hexlog.ui.dialogs.QMessageBox", FakeBox)
    FakeBox.instances = []
    FakeBox.answer = FakeBox.StandardButton.No

    assert confirm(None, "Hexlog", "Delete this?") is False
