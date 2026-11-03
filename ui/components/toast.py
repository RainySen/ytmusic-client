from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget

from ui import theme


# built on use: the theme is applied after import
def _colors() -> dict:
    return {
        "info": (theme.SURFACE_RAISED, theme.TEXT, theme.BORDER),
        "warning": (theme.SURFACE_RAISED, theme.TEXT, theme.DANGER),
        "error": (theme.SURFACE_RAISED, theme.DANGER, theme.DANGER),
    }


class Toast(QLabel):
    def __init__(self, parent: QWidget, bottom_offset: int = 96, duration_ms: int = 4500):
        super().__init__(parent)
        self._bottom_offset = bottom_offset
        self._duration_ms = duration_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()

    def show_message(self, level: str, text: str) -> None:
        colors = _colors()
        background, foreground, border = colors.get(level, colors["info"])
        self.setStyleSheet(
            f"background: {background}; color: {foreground}; border: 1px solid {border};"
            "border-radius: {theme.radius(8)}px; padding: 10px 18px; font-size: 13px;"
        )
        self.setText(text)
        self.reposition()
        self.show()
        self.raise_()
        self._timer.start(self._duration_ms)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.setMaximumWidth(max(240, min(560, parent.width() - 40)))
        self.adjustSize()
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - self._bottom_offset
        self.move(max(0, x), max(0, y))
