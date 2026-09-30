import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QLabel

from ui.imaging import circle_pixmap, round_pixmap, scale_cover

_PLACEHOLDERS: dict[tuple[str, int], QPixmap] = {}


def _placeholder(icon: str, size: int) -> QPixmap:
    key = (icon, size)
    pixmap = _PLACEHOLDERS.get(key)
    if pixmap is None:
        pixmap = qta.icon(icon, color="#555").pixmap(size, size)
        _PLACEHOLDERS[key] = pixmap
    return pixmap


# painted background instead of per-widget stylesheet (ram)
class LazyThumbnail(QLabel):
    def __init__(self, size: int, radius: int = 4, circle: bool = False,
                 icon: str = "fa5s.music", background: str = "#2a2a2a", parent=None):
        super().__init__(parent)
        self._size = size
        self._radius = radius
        self._circle = circle
        self._shape = size // 2 if circle else radius
        self._background = QColor(background)
        self._loaded = False
        self._url = ""
        self._cache = None
        self._requested = False
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignCenter)
        self.setPixmap(_placeholder(icon, max(16, size // 2)))

    def set_source(self, url: str, cache) -> None:
        self._url = url
        self._cache = cache
        self._requested = False
        if self.isVisible():
            self._load()

    def showEvent(self, event):
        super().showEvent(event)
        self._load()

    def paintEvent(self, event):
        if not self._loaded:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(self._background)
            painter.drawRoundedRect(self.rect(), self._shape, self._shape)
            painter.end()
        super().paintEvent(event)

    def _load(self) -> None:
        if self._requested or not self._url or self._cache is None:
            return
        self._requested = True
        self._cache.request(self._url, self._apply)

    def _apply(self, pixmap: QPixmap) -> None:
        dpr = self.devicePixelRatioF()
        if self._circle:
            result = circle_pixmap(pixmap, self._size, dpr)
        else:
            result = round_pixmap(scale_cover(pixmap, self._size, dpr), self._radius)
        self._loaded = True
        self.setPixmap(result)
