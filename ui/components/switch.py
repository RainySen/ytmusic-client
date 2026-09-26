from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

from ui import theme

WIDTH = 42
HEIGHT = 24


# interruptor on off
class Switch(QAbstractButton):
    def __init__(self, checked: bool = False):
        super().__init__()
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(WIDTH, HEIGHT)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        track = QColor(theme.LINK) if self.isChecked() else QColor(255, 255, 255, 60)
        knob = QColor("#ffffff") if self.isChecked() else QColor("#cccccc")
        if not self.isEnabled():
            track.setAlphaF(0.35)
            knob.setAlphaF(0.5)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 0, WIDTH, HEIGHT), HEIGHT / 2, HEIGHT / 2)
        diameter = HEIGHT - 8
        left = WIDTH - diameter - 4 if self.isChecked() else 4
        painter.setBrush(knob)
        painter.drawEllipse(QRectF(left, 4, diameter, diameter))
        painter.end()
