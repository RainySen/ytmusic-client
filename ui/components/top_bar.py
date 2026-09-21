from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton


class TopBar(QWidget):
    search_requested = Signal()
    login_requested = Signal()

    def __init__(self, icon_search, icon_login, icon_login_active, parent=None):
        super().__init__(parent)
        self.icon_search = icon_search
        self.icon_login = icon_login
        self.icon_login_active = icon_login_active

        self.setObjectName("top_bar")
        self.setFixedHeight(60)
        top_layout = QHBoxLayout(self)
        top_layout.setContentsMargins(16, 8, 16, 8)

        logo_label = QLabel("YouTube Music")
        logo_label.setObjectName("logo_label")
        logo_label.setFixedWidth(150)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar canción, artista, álbum...")
        self.search_box.setFixedHeight(38)
        self.search_box.setMaximumWidth(500)

        self.search_button = QPushButton()
        self.search_button.setIcon(self.icon_search)
        self.search_button.setFixedSize(38, 38)
        self.search_button.setCursor(Qt.PointingHandCursor)
        self.search_button.clicked.connect(self.search_requested.emit)

        self.login_button = QPushButton()
        self.login_button.setIcon(self.icon_login)
        self.login_button.setToolTip("Iniciar Sesión")
        self.login_button.setFixedSize(38, 38)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self.login_requested.emit)

        top_layout.addWidget(logo_label)
        top_layout.addStretch()
        top_layout.addWidget(self.search_box)
        top_layout.addWidget(self.search_button)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.login_button)

    def set_login_state(self, is_logged_in):
        self.login_button.setIcon(self.icon_login_active if is_logged_in else self.icon_login)
        self.login_button.setToolTip("Cerrar sesión" if is_logged_in else "Iniciar sesión")
