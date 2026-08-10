"""Tests for the save-failure handling in the main window (no GUI required)."""

from hexlog.ui.main_window import flush_and_report, save_error_message


class FailingStore:
    def save(self):
        raise OSError("No space left on device")


class SucceedingStore:
    def save(self):
        pass


def test_save_error_message_names_the_failure():
    assert save_error_message(OSError("disk full")) == "Could not save your data: disk full"


def test_flush_and_report_returns_true_on_success():
    assert flush_and_report(SucceedingStore(), notify=None) is True


def test_flush_and_report_reports_and_returns_false_on_failure():
    messages = []
    result = flush_and_report(FailingStore(), messages.append)
    assert result is False
    assert messages == ["Could not save your data: No space left on device"]


def test_flush_and_report_does_not_swallow_non_os_errors():
    class BrokenStore:
        def save(self):
            raise RuntimeError("boom")

    messages = []
    try:
        flush_and_report(BrokenStore(), messages.append)
    except RuntimeError:
        assert messages == []
    else:
        raise AssertionError("RuntimeError should propagate")
