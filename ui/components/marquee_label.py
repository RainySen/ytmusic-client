from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy

STEP_PX = 1
TICK_MS = 30
PAUSE_MS = 2000
GAP_PX = 48


# overflowing text loops left; timers idle when hidden
class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(1)
        self.offset = 0
        self._tick = QTimer(self)
        self._tick.setInterval(TICK_MS)
        self._tick.timeout.connect(self._advance)
        self._pause = QTimer(self)
        self._pause.setSingleShot(True)
        self._pause.setInterval(PAUSE_MS)
        self._pause.timeout.connect(self._tick.start)

    def setText(self, text):
        super().setText(text)
        self._restart()

    def text_width(self) -> int:
        return self.fontMetrics().horizontalAdvance(self.text())

    def overflowing(self) -> bool:
        return self.text_width() > self.contentsRect().width()

    @property
    def scrolling(self) -> bool:
        return self._tick.isActive() or self._pause.isActive()

    def _stop(self):
        self._tick.stop()
        self._pause.stop()

    def _restart(self):
        self.offset = 0
        self._stop()
        if self.isVisible() and self.overflowing():
            self._pause.start()
        self.update()

    def _advance(self):
        self.offset += STEP_PX
        if self.offset >= self.text_width() + GAP_PX:
            self.offset = 0
            self._tick.stop()
            self._pause.start()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._restart()

    def showEvent(self, event):
        super().showEvent(event)
        self._restart()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop()
        self.offset = 0

    def paintEvent(self, event):
        if not self.overflowing():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        rect = self.contentsRect()
        painter.setClipRect(rect)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        width = self.text_width()
        for x in (rect.x() - self.offset, rect.x() - self.offset + width + GAP_PX):
            painter.drawText(QRect(x, rect.y(), width, rect.height()), Qt.AlignLeft | Qt.AlignVCenter, self.text())
