"""Entry point for `python -m hexlog`."""

import sys

from PySide6.QtWidgets import QApplication

from hexlog.constants import APP_NAME
from hexlog.ui.main_window import MainWindow
from hexlog.ui.theme import get_theme_stylesheet


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(get_theme_stylesheet("dark"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
