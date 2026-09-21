from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton

_ACTIVE_STYLE = """
    QPushButton {
        background: rgba(255,255,255,0.10);
        color: white;
        text-align: left;
        padding-left: 16px;
        border: none;
        border-radius: 20px;
        font-weight: 600;
        font-size: 13px;
    }
"""
_INACTIVE_STYLE = """
    QPushButton {
        background: transparent;
        color: #aaa;
        text-align: left;
        padding-left: 16px;
        border: none;
        border-radius: 20px;
        font-weight: 500;
        font-size: 13px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.05);
        color: #e0e0e0;
    }
"""
_IMPORT_STYLE = """
    QPushButton {
        background: transparent;
        color: #888;
        text-align: left;
        padding-left: 16px;
        border: none;
        border-radius: 20px;
        font-size: 12px;
    }
    QPushButton:hover {
        background: rgba(255,255,255,0.04);
        color: #bbb;
    }
"""


class Sidebar(QWidget):
    home_requested = Signal()
    explore_requested = Signal()
    library_requested = Signal()
    import_requested = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(2)

        self.nav_buttons = {}
        for text, icon_key in [
            ("Inicio", "home"),
            ("Explorar", "explore"),
            ("Biblioteca", "library"),
        ]:
            button = QPushButton(text)
            button.setIcon(self.icons[icon_key])
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(44)
            button.setStyleSheet(_INACTIVE_STYLE)
            layout.addWidget(button)
            self.nav_buttons[text] = button

        self.nav_buttons["Inicio"].clicked.connect(self.home_requested.emit)
        self.nav_buttons["Explorar"].clicked.connect(self.explore_requested.emit)
        self.nav_buttons["Biblioteca"].clicked.connect(self.library_requested.emit)

        layout.addSpacing(12)

        self.import_button = QPushButton("Importar Playlist")
        self.import_button.setIcon(self.icons["import"])
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.setFixedHeight(40)
        self.import_button.setStyleSheet(_IMPORT_STYLE)
        self.import_button.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.import_button)

        layout.addStretch()

        self.set_active("Inicio")

    def set_active(self, name: str):
        for btn_name, btn in self.nav_buttons.items():
            btn.setStyleSheet(_ACTIVE_STYLE if btn_name == name else _INACTIVE_STYLE)
