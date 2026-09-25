from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from ui.imaging import round_pixmap, scale_cover

COVER_RADIUS = 10
MARGIN = 48


# portada grande
class NowPlayingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self._cover = None
        self.setStyleSheet("background: #030303;")

    def set_cover(self, pixmap: QPixmap):
        self._pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        self._rebuild_cover()
        self.update()

    def resizeEvent(self, event):
        self._rebuild_cover()
        super().resizeEvent(event)

    def _cover_size(self):
        return min(self.width(), self.height()) - 2 * MARGIN

    def _rebuild_cover(self):
        size = self._cover_size()
        if self._pixmap is None or size < 32:
            self._cover = None
            return
        self._cover = round_pixmap(scale_cover(self._pixmap, size, self.devicePixelRatioF()), COVER_RADIUS)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#030303"))
        if self._cover is not None:
            size = round(self._cover.deviceIndependentSize().width())
            painter.drawPixmap((self.width() - size) // 2, (self.height() - size) // 2, self._cover)
        painter.end()
