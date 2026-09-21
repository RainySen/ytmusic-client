import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from utils import extract_dominant_color, scale_cover


class NowPlayingPanel(QWidget):
    """Large circular cover art with blurred + tinted album art background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._bg_tiny = None
        self._cover_scaled = None  # pre-scaled square for the circle
        self._tint = QColor(0, 0, 0, 0)
        self.setStyleSheet("background: #030303;")

    def set_cover(self, pixmap: QPixmap):
        self._pixmap = pixmap
        if pixmap and not pixmap.isNull():
            # 8×8 → extreme blur when expanded back to full size
            self._bg_tiny = pixmap.scaled(
                8, 8, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self._tint = extract_dominant_color(pixmap, alpha=70)
        else:
            self._bg_tiny = None
            self._cover_scaled = None
            self._tint = QColor(0, 0, 0, 0)
        self._rebuild_cover()
        self.update()

    def resizeEvent(self, event):
        self._rebuild_cover()
        super().resizeEvent(event)

    def _rebuild_cover(self):
        if not self._pixmap or self._pixmap.isNull():
            return
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return
        # 55 % of shortest edge — smaller and clearly circular
        size = int(min(w, h) * 0.55)
        if size > 32:
            self._cover_scaled = scale_cover(self._pixmap, size)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        # ── 1. Blurred background ─────────────────────────────────────
        if self._bg_tiny:
            bg = self._bg_tiny.scaled(
                w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            bx = (bg.width() - w) // 2
            by = (bg.height() - h) // 2
            painter.drawPixmap(0, 0, bg, bx, by, w, h)
        else:
            painter.fillRect(0, 0, w, h, QColor("#030303"))

        # ── 2. Dark + tint overlay ────────────────────────────────────
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 155))
        if self._tint.alpha() > 0:
            painter.fillRect(0, 0, w, h, self._tint)

        # ── 3. Circular cover ─────────────────────────────────────────
        if self._cover_scaled and not self._cover_scaled.isNull():
            size = self._cover_scaled.width()
            cx = (w - size) // 2
            cy = (h - size) // 2

            # Clip to circle and draw
            path = QPainterPath()
            path.addEllipse(cx, cy, size, size)
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(cx, cy, self._cover_scaled)
            painter.restore()

            # Subtle white ring around the circle
            pen = QPen(QColor(255, 255, 255, 30))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(cx, cy, size, size)

        painter.end()
        super().paintEvent(event)
