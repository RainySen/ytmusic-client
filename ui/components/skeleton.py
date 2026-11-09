from PySide6.QtCore import QRectF, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import QSizePolicy, QWidget

from core.i18n import t
from ui import theme

SECTIONS = 2
COLUMNS = 3
ROWS = 4
ROW_H = 56
ROW_GAP = 8
COL_GAP = 12
TITLE_H = 22
SECTION_GAP = 32
THUMB = 44
FRAME_MS = 33
SWEEP_MS = 1400
BAND = 260


def _text_color(alpha: float) -> QColor:
    color = QColor(theme.TEXT)
    color.setAlphaF(alpha)
    return color


# placeholder shaped like the compact song sections; timer runs only while visible
class FeedSkeleton(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName(t("home.loading"))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        section_h = TITLE_H + 12 + ROWS * ROW_H + (ROWS - 1) * ROW_GAP
        self.setFixedHeight(SECTIONS * section_h + (SECTIONS - 1) * SECTION_GAP)
        self._section_h = section_h
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, event):
        self._timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _tick(self):
        self._phase = (self._phase + FRAME_MS / SWEEP_MS) % 1.0
        self.update()

    def _shapes(self) -> QPainterPath:
        path = QPainterPath()
        radius = theme.radius(6)
        col_w = (self.width() - (COLUMNS - 1) * COL_GAP) / COLUMNS
        for section in range(SECTIONS):
            top = section * (self._section_h + SECTION_GAP)
            path.addRoundedRect(QRectF(0, top, 220, TITLE_H), radius, radius)
            for row in range(ROWS):
                y = top + TITLE_H + 12 + row * (ROW_H + ROW_GAP)
                for col in range(COLUMNS):
                    x = col * (col_w + COL_GAP) + 8
                    path.addRoundedRect(QRectF(x, y + 6, THUMB, THUMB), theme.radius(4), theme.radius(4))
                    text_x = x + THUMB + 10
                    width = max(40.0, col_w - THUMB - 34)
                    path.addRoundedRect(QRectF(text_x, y + 12, width * 0.7, 12), radius, radius)
                    path.addRoundedRect(QRectF(text_x, y + 32, width * 0.45, 10), radius, radius)
        return path

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        shapes = self._shapes()
        painter.fillPath(shapes, _text_color(0.07))
        start = self._phase * (self.width() + BAND) - BAND
        sheen = QLinearGradient(start, 0, start + BAND, 0)
        sheen.setColorAt(0, _text_color(0.0))
        sheen.setColorAt(0.5, _text_color(0.09))
        sheen.setColorAt(1, _text_color(0.0))
        painter.setClipPath(shapes)
        painter.fillRect(self.rect(), sheen)
        painter.end()
