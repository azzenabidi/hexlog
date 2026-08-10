"""Oracle dialog: ask the Shadowdark SoloDark oracle and log to the journal.

The dialog is thin glue over the pure engine in hexlog.oracle; it owns
the randomness and hands the formatted result to a caller-supplied
insert_text() callback so the exchange can land in the journal.
"""

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from hexlog.oracle import ODDS_LABELS, odds_kind, resolve, roll_check


def format_answer(answer):
    """One line per part, for the dialog result and the journal log."""
    lines = [
        f"Q: {answer.question}",
        f"Odds {answer.odds} - rolled {answer.roll}: {answer.answer}",
    ]
    if answer.twist:
        lines.append(f"Twist: {answer.twist}")
    return "\n".join(lines)


class OracleDialog(QDialog):
    """Ask a fate question, roll the oracle check, and show any twist."""

    def __init__(self, parent=None, insert_text=None):
        super().__init__(parent)
        self.setWindowTitle("Oracle")
        self.insert_text = insert_text  # callable(text) logs an exchange
        self._last = None  # the most recent OracleAnswer, for logging

        root = QVBoxLayout(self)

        form = QFormLayout()
        self.question_edit = QLineEdit()
        self.question_edit.setPlaceholderText("e.g. Is the gate guarded?")
        self.question_edit.returnPressed.connect(self._ask)
        self.odds_combo = QComboBox()
        self.odds_combo.addItems(ODDS_LABELS)
        self.odds_combo.setCurrentText("Even Chance")
        self.odds_combo.setToolTip(
            "Unlikely or Impossible: roll with disadvantage (keep lowest).\n"
            "Even Chance: roll a single d20.\n"
            "Likely or Certain: roll with advantage (keep highest)."
        )
        form.addRow("Question", self.question_edit)
        form.addRow("Odds", self.odds_combo)
        root.addLayout(form)

        self.result_label = QLabel("Ask a question to hear the oracle.")
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.result_label)

        buttons = QHBoxLayout()
        self.ask_btn = QPushButton("Ask the Oracle")
        self.ask_btn.clicked.connect(self._ask)
        self.log_btn = QPushButton("Log to journal")
        self.log_btn.setEnabled(False)
        self.log_btn.clicked.connect(self._log)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.ask_btn)
        buttons.addWidget(self.log_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

    def _ask(self):
        """Roll the oracle check (with the odds' advantage/disadvantage)
        and show the verdict plus any twist that fires on a 10."""
        question = self.question_edit.text().strip() or "(unasked)"
        odds = self.odds_combo.currentText()
        roll = roll_check(odds_kind(odds), random)
        twist_roll = random.randint(1, 100) if roll == 10 else None
        answer = resolve(question, odds, roll, twist_roll)
        self._last = answer
        self.result_label.setText(format_answer(answer))
        self.log_btn.setEnabled(True)

    def _log(self):
        """Send the last answer to the journal, if a callback was provided."""
        if self._last is not None and self.insert_text is not None:
            self.insert_text(format_answer(self._last))
