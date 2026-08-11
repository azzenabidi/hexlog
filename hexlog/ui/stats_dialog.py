"""Dialog showing codebase statistics, opened from the Help menu."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from hexlog.stats import collect_stats

_ROWS = (
    ("Lines of code", "lines"),
    ("Python modules", "modules"),
    ("Classes", "classes"),
    ("Functions / methods", "functions"),
    ("Test cases", "test_functions"),
    ("Test classes", "test_classes"),
    ("External packages", "external_packages"),
)


class StatsDialog(QDialog):
    """Show nerd stats about the Hexlog codebase."""

    def __init__(self, parent=None, stats=None):
        super().__init__(parent)
        self.setWindowTitle("Nerd Stats")
        self.setMinimumWidth(360)
        stats = stats or collect_stats()

        layout = QVBoxLayout(self)
        heading = QLabel("Nerd Stats")
        heading.setObjectName("heading")
        layout.addWidget(heading)

        form = QFormLayout()
        for label, attr in _ROWS:
            value = QLabel(str(getattr(stats, attr)))
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            form.addRow(label, value)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)
