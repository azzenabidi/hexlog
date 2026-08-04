"""Entry point for `python -m hexlog`."""

import sys

from PySide6.QtWidgets import QApplication

from hexlog.constants import APP_NAME
from hexlog.ui.main_window import MainWindow
from hexlog.ui.theme import THEME_QSS


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(THEME_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
