from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from core.i18n import t
from ui import theme
from ui.components.icon_button import icon_button


class UpdateBanner(QWidget):
    open_requested = Signal()
    dismissed = Signal()

    def __init__(self, parent: QWidget, bottom_offset: int = 96):
        super().__init__(parent)
        self._bottom_offset = bottom_offset
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("UpdateBanner { background: #2a2a2a; border: 1px solid #444; border-radius: 8px; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 8, 8)
        layout.setSpacing(10)
        self._label = QLabel()
        self._label.setStyleSheet("color: #e6e6e6; font-size: 13px; background: transparent;")
        layout.addWidget(self._label)
        self.open_button = QPushButton(t("main.update.open"))
        self.open_button.setCursor(Qt.PointingHandCursor)
        self.open_button.setStyleSheet(theme.button_qss("tonal", height=30))
        self.open_button.clicked.connect(self._open)
        layout.addWidget(self.open_button)
        self.close_button = icon_button("fa5s.times", size=30, tooltip=t("main.update.close"))
        self.close_button.clicked.connect(self._close)
        layout.addWidget(self.close_button)
        self.hide()

    def text(self) -> str:
        return self._label.text()

    def show_version(self, version: str) -> None:
        self._label.setText(t("main.update.available", version=version))
        self.reposition()
        self.show()
        self.raise_()

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        self.move(max(0, (parent.width() - self.width()) // 2),
                  max(0, parent.height() - self.height() - self._bottom_offset))

    def _open(self) -> None:
        self.hide()
        self.open_requested.emit()

    def _close(self) -> None:
        self.hide()
        self.dismissed.emit()
