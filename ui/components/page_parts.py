import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ui import theme


def back_button() -> QPushButton:
    button = QPushButton()
    button.setIcon(qta.icon("fa5s.arrow-left", color="white"))
    button.setFixedSize(40, 40)
    button.setCursor(Qt.PointingHandCursor)
    button.setToolTip("Volver")
    button.setStyleSheet("""
        QPushButton { background: rgba(0,0,0,0.45); border: none; border-radius: 20px; }
        QPushButton:hover { background: rgba(255,255,255,0.20); }
    """)
    return button


def pill_button(text: str, kind: str = "primary", icon: str | None = None, height: int = 40) -> QPushButton:
    button = QPushButton("  " + text if icon else text)
    if icon:
        button.setIcon(qta.icon(icon, color=theme.BG if kind == "primary" else "white"))
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(theme.button_qss(kind, height))
    return button


def outline_button(text: str) -> QPushButton:
    button = QPushButton(text)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet("""
        QPushButton { background: transparent; color: white; border: 1px solid rgba(255,255,255,0.35);
                      border-radius: 18px; padding: 0 20px; min-height: 36px; font-size: 14px; font-weight: 600; }
        QPushButton:hover { background: rgba(255,255,255,0.10); border-color: white; }
    """)
    return button


def heading(text: str, px: int = 22) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(f"font-size: {px}px; font-weight: 700; color: {theme.TEXT};")
    return label


class MessagePage(QWidget):
    def __init__(self, text: str, on_back, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 24, 48, 24)
        button = back_button()
        button.clicked.connect(on_back)
        layout.addWidget(button, alignment=Qt.AlignLeft)
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 14px; padding: 60px;")
        layout.addWidget(label)
        layout.addStretch()
