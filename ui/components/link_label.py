from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel

from ui import theme


class LinkLabel(QLabel):
    clicked = Signal()

    def __init__(self, text: str = "", size: int = 11, parent=None):
        super().__init__(text, parent)
        self._size = size
        self._linked = False
        self._paint(False)

    @property
    def linked(self) -> bool:
        return self._linked

    def set_linked(self, linked: bool) -> None:
        self._linked = linked
        self.setCursor(Qt.PointingHandCursor if linked else Qt.ArrowCursor)
        self._paint(False)

    def _paint(self, hovered: bool) -> None:
        underline = "underline" if hovered and self._linked else "none"
        color = theme.TEXT if hovered and self._linked else theme.TEXT_SECONDARY
        self.setStyleSheet(f"font-size: {self._size}px; color: {color}; text-decoration: {underline}; "
                           f"background: transparent;")

    def enterEvent(self, event):
        self._paint(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._paint(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._linked:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)
