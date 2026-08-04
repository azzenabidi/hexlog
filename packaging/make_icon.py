"""Render the Hexlog icon to PNG files with PySide6 (no display needed).

Usage: python make_icon.py <output-dir>

Writes hexlog-256.png and hexlog-512.png into the output directory.
The icon is a pointy-top hexagon with a log-lines motif inside.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)

SIZES = (256, 512)
# Clockwise from the top-right vertex; down is +y in Qt.
VERTICES = (
    (0.866, -0.5), (0.866, 0.5), (0.0, 1.0),
    (-0.866, 0.5), (-0.866, -0.5), (0.0, -1.0),
)


def hex_polygon(cx: float, cy: float, r: float) -> QPolygonF:
    return QPolygonF([QPointF(cx + r * dx, cy + r * dy) for dx, dy in VERTICES])


def hex_path(cx: float, cy: float, r: float) -> QPainterPath:
    path = QPainterPath()
    for i, (dx, dy) in enumerate(VERTICES):
        pt = QPointF(cx + r * dx, cy + r * dy)
        if i == 0:
            path.moveTo(pt)
        else:
            path.lineTo(pt)
    path.closeSubpath()
    return path


def render(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    half = size / 2.0
    grad = QLinearGradient(0.0, 0.0, 0.0, float(size))
    grad.setColorAt(0.0, QColor("#6c5ce7"))
    grad.setColorAt(1.0, QColor("#0984e3"))
    p.fillPath(hex_path(half, half, size * 0.47), grad)

    shade = QPen(QColor(0, 0, 0, 70), size * 0.015)
    p.setPen(shade)
    p.drawPolygon(hex_polygon(half, half, size * 0.47))

    inner = QPen(QColor(255, 255, 255, 230), size * 0.022)
    p.setPen(inner)
    p.drawPolygon(hex_polygon(half, half, size * 0.30))

    line = QPen(QColor(255, 255, 255, 230), size * 0.045)
    line.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(line)
    width = size * 0.30
    y = size * 0.42
    for i in range(3):
        p.drawLine(
            QPointF(half - width / 2, y),
            QPointF(half + width / 2 * (1.0 - i * 0.3), y),
        )
        y += size * 0.075

    p.end()
    return pm


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "build/icon")
    out_dir.mkdir(parents=True, exist_ok=True)
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    del app
    for size in SIZES:
        render(size).save(str(out_dir / f"hexlog-{size}.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
