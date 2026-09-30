from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui import theme
from ui.components.elided_label import ElidedLabel

MAX_VISIBLE = 8
ROW_HEIGHT = 38

_POPUP_QSS = f"""
    QFrame#history_card {{ background: {theme.SURFACE_RAISED}; border: 1px solid {theme.BORDER}; border-radius: 14px; }}
"""


class _Row(QWidget):
    chosen = Signal(str)
    removed = Signal(str)

    def __init__(self, query: str):
        super().__init__()
        self._query = query
        self.setFixedHeight(ROW_HEIGHT)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QWidget { background: transparent; border-radius: 8px; } "
                           "QWidget:hover { background: rgba(255,255,255,0.08); }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 6, 0)
        layout.setSpacing(10)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.history", color="#888").pixmap(13, 13))
        icon.setStyleSheet("background: transparent;")
        text = ElidedLabel(query)
        text.setStyleSheet(f"color: {theme.TEXT}; font-size: 13px; background: transparent;")
        self.remove_button = QPushButton()
        self.remove_button.setIcon(qta.icon("fa5s.times", color="#999"))
        self.remove_button.setFixedSize(26, 26)
        self.remove_button.setToolTip("Quitar del historial")
        self.remove_button.setCursor(Qt.PointingHandCursor)
        self.remove_button.setStyleSheet("QPushButton { background: transparent; border: none; border-radius: 13px; } "
                                         "QPushButton:hover { background: rgba(255,255,255,0.15); }")
        self.remove_button.clicked.connect(lambda: self.removed.emit(self._query))
        layout.addWidget(icon)
        layout.addWidget(text, 1)
        layout.addWidget(self.remove_button)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.chosen.emit(self._query)
        super().mouseReleaseEvent(event)


class SearchHistoryPopup(QFrame):
    chosen = Signal(str)
    removed = Signal(str)
    cleared = Signal()

    def __init__(self, box, anchor: QWidget):
        super().__init__(anchor.window(), Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self._box = box
        self._anchor = anchor
        self._items: list[str] = []
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TranslucentBackground)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("history_card")
        card.setStyleSheet(_POPUP_QSS)
        outer.addWidget(card)
        self._rows = QVBoxLayout(card)
        self._rows.setContentsMargins(6, 6, 6, 6)
        self._rows.setSpacing(0)
        self._filter = _BoxWatcher(self)
        box.installEventFilter(self._filter)
        box.textChanged.connect(lambda _text: self.refresh())

    def set_items(self, items: list[str]) -> None:
        self._items = list(items)
        self.refresh()

    def shown_items(self) -> list[str]:
        needle = self._box.text().strip().lower()
        matches = [q for q in self._items if needle in q.lower() and q.lower() != needle]
        return matches[:MAX_VISIBLE]

    def refresh(self) -> None:
        while self._rows.count():
            widget = self._rows.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        items = self.shown_items()
        if not items or not self._box.hasFocus():
            self.hide()
            return
        for query in items:
            row = _Row(query)
            row.chosen.connect(self._pick)
            row.removed.connect(self.removed)
            self._rows.addWidget(row)
        if not self._box.text().strip():
            clear = QPushButton("Borrar historial")
            clear.setCursor(Qt.PointingHandCursor)
            clear.setStyleSheet(f"QPushButton {{ background: transparent; color: {theme.LINK}; border: none; "
                                f"text-align: left; padding: 8px 12px; font-size: 12px; font-weight: 600; }}")
            clear.clicked.connect(self.cleared)
            self._rows.addWidget(clear)
        self.adjustSize()
        self.setFixedWidth(self._anchor.width())
        self.move(self._anchor.mapToGlobal(QPoint(0, self._anchor.height() + 4)))
        self.show()

    def _pick(self, query: str) -> None:
        self.hide()
        self.chosen.emit(query)


class _BoxWatcher(QObject):
    def __init__(self, popup: SearchHistoryPopup):
        super().__init__(popup)
        self._popup = popup

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind in (QEvent.FocusIn, QEvent.MouseButtonPress):
            self._popup.refresh()
        elif kind == QEvent.FocusOut or (kind == QEvent.KeyPress and event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter)):
            self._popup.hide()
        return False
