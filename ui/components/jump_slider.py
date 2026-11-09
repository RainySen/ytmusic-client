from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider, QToolTip


class JumpSlider(QSlider):
    # set to fraction -> label to show it under the cursor on hover
    hover_text = None

    def mouseMoveEvent(self, event):
        if self.hover_text is not None and self.orientation() == Qt.Horizontal and self.width() > 0:
            fraction = max(0.0, min(1.0, event.position().x() / self.width()))
            QToolTip.showText(event.globalPosition().toPoint(), self.hover_text(fraction), self)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.orientation() == Qt.Horizontal:
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            style = self.style()
            handle = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
            if not handle.contains(event.position().toPoint()):
                groove = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderGroove, self)
                span = max(1, groove.width() - handle.width())
                position = int(event.position().x()) - groove.x() - handle.width() // 2
                value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), position, span)
                self.setValue(value)
                self.sliderMoved.emit(value)
                # fake press at the new spot so dragging keeps working
                option = QStyleOptionSlider()
                self.initStyleOption(option)
                handle = style.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
                center = QPointF(handle.center())
                fake = QMouseEvent(event.type(), center, self.mapToGlobal(handle.center()),
                                   event.button(), event.buttons(), event.modifiers())
                super().mousePressEvent(fake)
                return
        super().mousePressEvent(event)
