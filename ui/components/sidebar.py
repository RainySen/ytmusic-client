from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton


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
        layout.setSpacing(4)

        self.nav_buttons = {}
        for text, icon in [
            ("Inicio", self.icons["home"]),
            ("Explorar", self.icons["explore"]),
            ("Biblioteca", self.icons["library"]),
        ]:
            button = QPushButton(text)
            button.setIcon(icon)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(40)
            layout.addWidget(button)
            self.nav_buttons[text] = button

        self.nav_buttons["Inicio"].clicked.connect(self.home_requested.emit)
        self.nav_buttons["Explorar"].clicked.connect(self.explore_requested.emit)
        self.nav_buttons["Biblioteca"].clicked.connect(self.library_requested.emit)

        layout.addSpacing(16)

        self.import_button = QPushButton("Importar Playlist")
        self.import_button.setIcon(self.icons["import"])
        self.import_button.setCursor(Qt.PointingHandCursor)
        self.import_button.setFixedHeight(40)
        self.import_button.clicked.connect(self.import_requested.emit)
        layout.addWidget(self.import_button)

        layout.addStretch()
