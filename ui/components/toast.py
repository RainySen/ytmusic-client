from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget

_COLORS = {
    "info": ("#2a2a2a", "#e6e6e6", "#444"),
    "warning": ("#3a3020", "#ffd479", "#6b5a2e"),
    "error": ("#3a2020", "#ff9a9a", "#6b2e2e"),
}


# avisos
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
        background, foreground, border = _COLORS.get(level, _COLORS["info"])
        self.setStyleSheet(
            f"background: {background}; color: {foreground}; border: 1px solid {border};"
            "border-radius: 8px; padding: 10px 18px; font-size: 13px;"
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
