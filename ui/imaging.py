from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap


# imagenes dpr
def scale_cover(pixmap: QPixmap, size: int, dpr: float = 1.0) -> QPixmap:
    target = max(1, round(size * dpr))
    scaled = pixmap.scaled(target, target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (scaled.width() - target) // 2
    y = (scaled.height() - target) // 2
    out = scaled.copy(x, y, target, target)
    out.setDevicePixelRatio(dpr)
    return out


def round_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
    if radius <= 0 or pixmap.isNull():
        return pixmap
    out = QPixmap(pixmap.size())
    out.setDevicePixelRatio(pixmap.devicePixelRatio())
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, *pixmap.deviceIndependentSize().toTuple()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return out


def circle_pixmap(pixmap: QPixmap, size: int, dpr: float = 1.0) -> QPixmap:
    square = scale_cover(pixmap, size, dpr)
    out = QPixmap(square.size())
    out.setDevicePixelRatio(dpr)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addEllipse(QRectF(0, 0, size, size))
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, square)
    painter.end()
    return out
