from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolButton

_ACTIVE = """
    QToolButton {
        background: rgba(255,255,255,0.12);
        color: white;
        border: none;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 700;
        padding-top: 6px;
    }
"""
_INACTIVE = """
    QToolButton {
        background: transparent;
        color: #aaa;
        border: none;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 500;
        padding-top: 6px;
    }
    QToolButton:hover {
        background: rgba(255,255,255,0.08);
        color: #e0e0e0;
    }
"""
_SMALL = """
    QToolButton {
        background: transparent;
        color: #666;
        border: none;
        border-radius: 8px;
        font-size: 10px;
        padding-top: 4px;
    }
    QToolButton:hover {
        background: rgba(255,255,255,0.06);
        color: #aaa;
    }
"""


class Sidebar(QWidget):
    home_requested    = Signal()
    explore_requested = Signal()
    library_requested = Signal()
    import_requested  = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.setObjectName("sidebar")
        self.setFixedWidth(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 20, 8, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self.nav_buttons = {}
        for label, icon_key, signal in [
            ("Inicio",    "home",    self.home_requested),
            ("Explorar",  "explore", self.explore_requested),
            ("Biblioteca","library", self.library_requested),
        ]:
            btn = QToolButton()
            btn.setText(label)
            btn.setIcon(icons[icon_key])
            btn.setIconSize(QSize(22, 22))
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setFixedSize(74, 62)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_INACTIVE)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self.nav_buttons[label] = btn

        layout.addSpacing(12)

        self.import_button = QToolButton()
        self.import_button.setText("Importar")
        self.import_button.setIcon(icons["import"])
        self.import_button.setIconSize(QSize(18, 18))
        self.import_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.import_button.setFixedSize(74, 54)
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.setStyleSheet(_SMALL)
        self.import_button.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.import_button, alignment=Qt.AlignHCenter)

        layout.addStretch()
        self.set_active("Inicio")

    def set_active(self, name: str):
        for btn_name, btn in self.nav_buttons.items():
            btn.setStyleSheet(_ACTIVE if btn_name == name else _INACTIVE)
