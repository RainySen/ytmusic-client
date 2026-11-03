from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton

from ui import theme

WIDTH = 42
HEIGHT = 24


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
        checked = self.isChecked()
        track = QColor(theme.LINK) if checked else QColor(theme.TEXT)
        if not checked:
            track.setAlphaF(60 / 255)
        knob = QColor(theme.SWITCH_KNOB) if checked else QColor(theme.PRESSED)
        if not self.isEnabled():
            track.setAlphaF(0.35)
            knob.setAlphaF(0.5)
        corner = theme.radius(HEIGHT // 2)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(0, 0, WIDTH, HEIGHT), corner, corner)
        diameter = HEIGHT - 8
        left = WIDTH - diameter - 4 if self.isChecked() else 4
        painter.setBrush(knob)
        knob_corner = theme.radius(diameter // 2)
        painter.drawRoundedRect(QRectF(left, 4, diameter, diameter), knob_corner, knob_corner)
        painter.end()
