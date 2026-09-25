import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame


class TopBar(QWidget):
    search_requested = Signal()
    login_requested = Signal()

    def __init__(self, icon_search, icon_login, icon_login_active, parent=None):
        super().__init__(parent)
        self.icon_search = icon_search
        self.icon_login = icon_login
        self.icon_login_active = icon_login_active

        self.setObjectName("top_bar")
        self.setFixedHeight(64)
        top_layout = QHBoxLayout(self)
        top_layout.setContentsMargins(16, 10, 16, 10)
        top_layout.setSpacing(8)

        logo_row = QWidget()
        logo_row.setFixedWidth(160)
        logo_l = QHBoxLayout(logo_row)
        logo_l.setContentsMargins(0, 0, 0, 0)
        logo_l.setSpacing(6)

        yt_icon = QLabel()
        yt_icon.setPixmap(qta.icon('fa5b.youtube', color='#FF0000').pixmap(24, 24))
        logo_text = QLabel("Music")
        logo_text.setObjectName("logo_label")

        logo_l.addWidget(yt_icon)
        logo_l.addWidget(logo_text)
        logo_l.addStretch()

        search_wrapper = QFrame()
        search_wrapper.setObjectName("search_wrapper")
        search_wrapper.setFixedHeight(42)
        search_wrapper.setMaximumWidth(520)
        search_wrapper.setStyleSheet("""
            QFrame#search_wrapper {
                background: #121212;
                border: 1px solid #383838;
                border-radius: 21px;
            }
            QFrame#search_wrapper:focus-within {
                border: 1px solid rgba(255,255,255,0.45);
                background: #1a1a1a;
            }
        """)
        sw_layout = QHBoxLayout(search_wrapper)
        sw_layout.setContentsMargins(14, 0, 4, 0)
        sw_layout.setSpacing(4)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar canciones, artistas, álbumes...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                font-size: 14px;
            }
        """)

        self.search_button = QPushButton()
        self.search_button.setIcon(self.icon_search)
        self.search_button.setFixedSize(34, 34)
        self.search_button.setCursor(Qt.PointingHandCursor)
        self.search_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 17px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.10); }
        """)
        self.search_button.clicked.connect(self.search_requested.emit)

        sw_layout.addWidget(self.search_box, stretch=1)
        sw_layout.addWidget(self.search_button)

        self.login_button = QPushButton()
        self.login_button.setIcon(self.icon_login)
        self.login_button.setToolTip("Iniciar sesión")
        self.login_button.setFixedSize(40, 40)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #555;
                border-radius: 20px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.10); border-color: #aaa; }
        """)
        self.login_button.clicked.connect(self.login_requested.emit)

        top_layout.addWidget(logo_row)
        top_layout.addStretch()
        top_layout.addWidget(search_wrapper, stretch=1)
        top_layout.addStretch()
        top_layout.addWidget(self.login_button)

    def set_login_state(self, is_logged_in):
        self.login_button.setIcon(self.icon_login_active if is_logged_in else self.icon_login)
        self.login_button.setToolTip("Cerrar sesión" if is_logged_in else "Iniciar sesión")
        if is_logged_in:
            self.login_button.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid #FF0033;
                    border-radius: 20px;
                }
                QPushButton:hover { background: rgba(255,0,51,0.12); }
            """)
