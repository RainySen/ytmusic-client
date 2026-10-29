from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QProgressBar, QVBoxLayout, QWidget

from core.i18n import t
from ui import theme
from ui.components.elided_label import ElidedLabel
from ui.components.icon_button import icon_button

PROGRESS_STEPS = 1000


# own top-level window: the main stylesheet never reaches it, so the theme is applied here
def _edge() -> str:
    return {"aero": theme.overlay(0.35), "cyberpunk": theme.LINK}.get(theme.current(), theme.BORDER)


def _progress_fill() -> str:
    return {"aero": theme.gel(), "cyberpunk": theme.ACCENT}.get(theme.current(), theme.TEXT)


def _toggle_qss() -> str:
    fill = theme.gel() if theme.current() == "aero" else theme.BUTTON_BG
    return f"QPushButton {{ background: {fill}; }} QPushButton:hover {{ background: {theme.HOVER}; }}"


class MiniPlayer(QWidget):
    toggle_requested = Signal()
    next_requested = Signal()
    previous_requested = Signal()
    rewind_requested = Signal()
    expand_requested = Signal()
    close_requested = Signal()
    moved = Signal(int, int)

    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 88)
        self._drag_offset: QPoint | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("mini_card")
        card.setStyleSheet(f"#mini_card {{ background: {theme.glass(theme.SURFACE)}; border: 1px solid {_edge()}; "
                           f"border-radius: {theme.radius(14)}px; }} QLabel {{ background: transparent; }}")
        outer.addWidget(card)

        column = QVBoxLayout(card)
        column.setContentsMargins(14, 10, 10, 8)
        column.setSpacing(6)

        row = QHBoxLayout()
        row.setSpacing(6)
        texts = QVBoxLayout()
        texts.setSpacing(0)
        self._title = ElidedLabel(t("player.mini.empty"))
        self._title.setStyleSheet(f"color: {theme.TEXT}; font-size: 13px; font-weight: 600;")
        self._artist = ElidedLabel("")
        self._artist.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        texts.addStretch(1)
        texts.addWidget(self._title)
        texts.addWidget(self._artist)
        texts.addStretch(1)
        row.addLayout(texts, 1)

        self.rewind = icon_button("fa5s.undo-alt", 32, t("player.mini.rewind"))
        self._previous = icon_button("fa5s.step-backward", 32, t("player.mini.previous"))
        self._toggle = icon_button("fa5s.play", 38, t("player.mini.play_pause"))
        self._next = icon_button("fa5s.step-forward", 32, t("player.mini.next"))
        self._expand = icon_button("fa5s.expand-alt", 32, t("player.mini.expand"))
        self._close = icon_button("fa5s.times", 28, t("player.mini.close"))
        self.rewind.clicked.connect(self.rewind_requested)
        self._previous.clicked.connect(self.previous_requested)
        self._toggle.clicked.connect(self.toggle_requested)
        self._next.clicked.connect(self.next_requested)
        self._expand.clicked.connect(self.expand_requested)
        self._close.clicked.connect(self.close_requested)
        if theme.current() != "classic":
            self._toggle.setStyleSheet(self._toggle.styleSheet() + _toggle_qss())
            self._toggle.setGraphicsEffect(theme.glow_effect())
        self.set_playing(False)
        for button in (self.rewind, self._previous, self._toggle, self._next, self._expand, self._close):
            row.addWidget(button)
        column.addLayout(row, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, PROGRESS_STEPS)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(3)
        self._progress.setStyleSheet(f"""
            QProgressBar {{ background: {theme.overlay(0.2)}; border: none; border-radius: {theme.radius(1)}px; }}
            QProgressBar::chunk {{ background: {_progress_fill()}; border-radius: {theme.radius(1)}px; }}
        """)
        column.addWidget(self._progress)

    def set_track(self, title: str, artist: str) -> None:
        self._title.setText(title or t("player.mini.empty"))
        self._artist.setText(artist)
        self._progress.setValue(0)

    def set_neighbors(self, previous: str, following: str) -> None:
        self._previous.setToolTip(t("player.mini.previous_named", title=previous) if previous
                                  else t("player.mini.previous"))
        self._next.setToolTip(t("player.mini.next_named", title=following) if following
                              else t("player.mini.next"))

    def set_rewind_seconds(self, seconds: int) -> None:
        self.rewind.setToolTip(t("player.mini.rewind_seconds", seconds=seconds))

    def set_playing(self, playing: bool) -> None:
        color = theme.TEXT if theme.current() == "classic" else theme.BUTTON_TEXT
        self._toggle.setIcon(qta.icon("fa5s.pause" if playing else "fa5s.play", color=color))

    def set_position(self, fraction: float) -> None:
        self._progress.setValue(round(max(0.0, min(1.0, fraction)) * PROGRESS_STEPS))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_offset is not None:
            self._drag_offset = None
            self.moved.emit(self.x(), self.y())
        super().mouseReleaseEvent(event)
