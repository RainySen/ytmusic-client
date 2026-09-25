from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


# click hover clic derecho
class ClickableWidget(QWidget):
    activated = Signal()
    hover_changed = Signal(bool)
    context_requested = Signal(QPoint)
    dwelled = Signal()

    def __init__(self, parent=None, radius: int = 6, hover_alpha: int = 15, dwell_ms: int = 0):
        super().__init__(parent)
        self._radius = radius
        self._hover_alpha = hover_alpha
        self._hovered = False
        self._pressed = False
        self._dwell_timer = None
        if dwell_ms > 0:
            self._dwell_timer = QTimer(self)
            self._dwell_timer.setSingleShot(True)
            self._dwell_timer.setInterval(dwell_ms)
            self._dwell_timer.timeout.connect(self.dwelled)
        self.setCursor(Qt.PointingHandCursor)

    @property
    def hovered(self) -> bool:
        return self._hovered

    def paintEvent(self, event):
        if self._hovered and self._hover_alpha:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, self._hover_alpha))
            painter.drawRoundedRect(self.rect(), self._radius, self._radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dwell_timer is not None:
                self._dwell_timer.stop()
            self._pressed = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        was_pressed, self._pressed = self._pressed, False
        if was_pressed and event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.activated.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.context_requested.emit(event.globalPos())
        event.accept()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        if self._dwell_timer is not None:
            self._dwell_timer.start()
        self.hover_changed.emit(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._pressed = False
        if self._dwell_timer is not None:
            self._dwell_timer.stop()
        self.update()
        self.hover_changed.emit(False)
        super().leaveEvent(event)
