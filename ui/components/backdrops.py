from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget

from ui import theme

# fixed seeds: stable layout
BUBBLE_SEED = 7
BUBBLE_COUNT = 16
CITY_SEED = 11
HORIZON = 0.72
PIXEL = 3


def _color(value: str, alpha: int) -> QColor:
    color = QColor(value)
    color.setAlpha(alpha)
    return color


# cached per window size
class Backdrop(QWidget):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._cache: QPixmap | None = None

    def resizeEvent(self, event):
        self._cache = None
        super().resizeEvent(event)

    def paintEvent(self, _event):
        if self._cache is None or self._cache.size() != self.size() * self.devicePixelRatioF():
            self._cache = self._render()
        QPainter(self).drawPixmap(0, 0, self._cache)

    def _render(self) -> QPixmap:
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(self.size() * ratio)
        pixmap.setDevicePixelRatio(ratio)
        painter = QPainter(pixmap)
        self._paint(painter, float(self.width()), float(self.height()))
        painter.end()
        return pixmap

    def _paint(self, painter: QPainter, w: float, h: float) -> None:
        raise NotImplementedError


class AeroScene(Backdrop):
    def _paint(self, painter, w, h):
        painter.setRenderHint(QPainter.Antialiasing)
        self._sky(painter, w, h)
        self._aurora(painter, w, h)
        self._rays(painter, w, h)
        self._hills(painter, w, h)
        self._bubbles(painter, w, h)

    def _sky(self, painter, w, h):
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor(theme.BG))
        sky.setColorAt(1, QColor(theme.BG_END))
        painter.fillRect(QRectF(0, 0, w, h), sky)

    def _aurora(self, painter, w, h):
        first, second, third = theme.AERO_SCENE["aurora"]
        for cx, cy, radius, color, alpha in ((0.78, 0.12, 0.55, first, 70), (0.25, 0.05, 0.45, third, 55),
                                             (0.55, 0.30, 0.40, second, 35)):
            glow = QRadialGradient(QPointF(w * cx, h * cy), max(w, h) * radius)
            glow.setColorAt(0, _color(color, alpha))
            glow.setColorAt(1, _color(color, 0))
            painter.fillRect(QRectF(0, 0, w, h), glow)
        for offset, color, alpha in ((0.16, second, 40), (0.22, first, 30)):
            path = QPainterPath(QPointF(0, h * offset))
            for step in range(1, 41):
                x = w * step / 40
                path.lineTo(x, h * offset + math.sin(step / 40 * math.pi * 2.4) * h * 0.05)
            pen = QPen(_color(color, alpha), h * 0.06)
            pen.setCapStyle(Qt.RoundCap)
            painter.strokePath(path, pen)

    def _rays(self, painter, w, h):
        origin = QPointF(w * 0.08, -h * 0.05)
        for angle, spread in ((58, 4), (66, 6), (75, 3), (83, 5)):
            path = QPainterPath(origin)
            for a in (angle - spread / 2, angle + spread / 2):
                rad = math.radians(a)
                path.lineTo(origin.x() + math.cos(rad) * h * 1.4, origin.y() + math.sin(rad) * h * 1.4)
            path.closeSubpath()
            ray = QLinearGradient(origin, QPointF(origin.x() + w * 0.3, h))
            ray.setColorAt(0, _color(theme.AERO_SCENE["ray"], 22))
            ray.setColorAt(1, _color(theme.AERO_SCENE["ray"], 0))
            painter.fillPath(path, ray)

    def _hills(self, painter, w, h):
        scene = theme.AERO_SCENE
        for base, lift, phase, alpha in ((0.86, 0.10, 0.2, 120), (0.92, 0.08, 1.4, 170)):
            path = QPainterPath(QPointF(0, h))
            path.lineTo(0, h * base)
            path.cubicTo(w * (0.25 + phase * 0.05), h * (base - lift), w * (0.55 - phase * 0.05), h * (base + lift * 0.6),
                         w, h * (base - lift * 0.4))
            path.lineTo(w, h)
            path.closeSubpath()
            fill = QLinearGradient(0, h * (base - lift), 0, h)
            fill.setColorAt(0, _color(scene["hill_top"], alpha))
            fill.setColorAt(1, _color(scene["hill_bottom"], alpha))
            painter.fillPath(path, fill)
            crest = QPainterPath(QPointF(0, h * base))
            crest.cubicTo(w * (0.25 + phase * 0.05), h * (base - lift), w * (0.55 - phase * 0.05), h * (base + lift * 0.6),
                          w, h * (base - lift * 0.4))
            painter.strokePath(crest, QPen(_color(scene["rim"], 70), 1.5))

    def _bubbles(self, painter, w, h):
        tint = theme.AERO_SCENE["bubble"]
        rng = random.Random(BUBBLE_SEED)
        for _ in range(BUBBLE_COUNT):
            radius = rng.uniform(6, 42)
            # edges only: content is in the middle
            x = rng.choice((rng.uniform(0.0, 0.14), rng.uniform(0.90, 1.0))) * w
            y = rng.uniform(0.40, 0.95) * h
            center = QPointF(x, y)
            body = QRadialGradient(center, radius)
            body.setColorAt(0, _color(tint, 6))
            body.setColorAt(0.85, _color(tint, 26))
            body.setColorAt(1, _color(tint, 50))
            painter.setPen(Qt.NoPen)
            painter.setBrush(body)
            painter.drawEllipse(center, radius, radius)
            shine = QRadialGradient(QPointF(x - radius * 0.35, y - radius * 0.4), radius * 0.45)
            shine.setColorAt(0, _color(tint, 120))
            shine.setColorAt(1, _color(tint, 0))
            painter.setBrush(shine)
            painter.drawEllipse(QPointF(x - radius * 0.35, y - radius * 0.4), radius * 0.4, radius * 0.3)


class CyberScene(Backdrop):
    def _paint(self, painter, w, h):
        scene = theme.CYBER_SCENE
        horizon = round(h * HORIZON)
        painter.fillRect(QRectF(0, 0, w, h), QColor(theme.BG))
        sky = QLinearGradient(0, 0, 0, horizon)
        sky.setColorAt(0, QColor(theme.BG))
        sky.setColorAt(1, QColor(scene["haze"]))
        painter.fillRect(QRectF(0, 0, w, horizon), sky)
        rng = random.Random(CITY_SEED)
        self._stars(painter, rng, w, horizon)
        self._sun(painter, w, horizon)
        self._skyline(painter, rng, w, horizon)
        self._grid(painter, w, h, horizon)
        self._scrim(painter, w, h)
        self._scanlines(painter, w, h)

    # readability: darker behind the content
    def _scrim(self, painter, w, h):
        band = QLinearGradient(0, 0, w, 0)
        for stop, alpha in ((0.0, 0), (0.22, 150), (0.80, 150), (1.0, 0)):
            band.setColorAt(stop, _color(theme.BG, alpha))
        painter.fillRect(QRectF(0, 0, w, h), band)

    def _stars(self, painter, rng, w, horizon):
        for _ in range(70):
            color = _color(rng.choice(theme.CYBER_SCENE["windows"]), rng.randint(60, 160))
            painter.fillRect(QRectF(_snap(rng.uniform(0, w)), _snap(rng.uniform(0, horizon * 0.7)),
                                    PIXEL - 1, PIXEL - 1), color)

    def _sun(self, painter, w, horizon):
        scene = theme.CYBER_SCENE
        radius = horizon * 0.30
        cx, cy = w * 0.80, horizon - radius * 0.25
        body = QLinearGradient(0, cy - radius, 0, cy + radius)
        body.setColorAt(0, _color(scene["sun_top"], 90))
        body.setColorAt(1, _color(scene["sun_bottom"], 90))
        disc = QPainterPath()
        disc.addEllipse(QPointF(cx, cy), radius, radius)
        stripes = QPainterPath()
        y, gap = cy, 2.0
        while y < cy + radius:
            stripes.addRect(QRectF(cx - radius, y, radius * 2, gap))
            y += gap + 7
            gap += 1.5
        painter.fillPath(disc.subtracted(stripes), body)

    def _skyline(self, painter, rng, w, horizon):
        scene = theme.CYBER_SCENE
        x = 0.0
        while x < w:
            width = _snap(rng.uniform(26, 70))
            height = _snap(rng.uniform(0.10, 0.34) * horizon)
            top = horizon - height
            painter.fillRect(QRectF(x, top, width, height), QColor(scene["city"]))
            painter.fillRect(QRectF(x, top, width, 1), _color(scene["edge"], 90))
            for wy in range(int(top) + 6, horizon - 4, PIXEL * 3):
                for wx in range(int(x) + 4, int(x + width) - 4, PIXEL * 3):
                    if rng.random() < 0.22:
                        painter.fillRect(QRectF(wx, wy, PIXEL, PIXEL),
                                         _color(rng.choice(scene["windows"]), rng.randint(50, 130)))
            x += width + _snap(rng.uniform(0, 12))

    def _grid(self, painter, w, h, horizon):
        scene = theme.CYBER_SCENE
        floor = QLinearGradient(0, horizon, 0, h)
        floor.setColorAt(0, QColor(scene["haze"]))
        floor.setColorAt(1, QColor(theme.BG))
        painter.fillRect(QRectF(0, horizon, w, h - horizon), floor)
        painter.fillRect(QRectF(0, horizon - 1, w, 2), _color(theme.LINK, 200))
        painter.setPen(QPen(_color(scene["grid"], 80), 1))
        depth = h - horizon
        step = 1
        while (y := horizon + depth * (step / 12) ** 2) <= h:
            painter.drawLine(QPointF(0, y), QPointF(w, y))
            step += 1
        vanish = QPointF(w * 0.5, horizon)
        for i in range(-16, 17):
            painter.drawLine(vanish, QPointF(w * 0.5 + i * w * 0.09, h))

    def _scanlines(self, painter, w, h):
        line = _color(theme.CYBER_SCENE["scan"], 70)
        for y in range(0, int(h), PIXEL):
            painter.fillRect(QRectF(0, y, w, 1), line)


def _snap(value: float) -> float:
    return float(int(value) // PIXEL * PIXEL)


SCENES = {"aero": AeroScene, "cyberpunk": CyberScene}
