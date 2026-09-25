import qtawesome as qta
from importlib.util import find_spec

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from ui import theme
from ui.components import dialogs

WINDOW_HEIGHT = 480
WEB_LOGIN_AVAILABLE = find_spec("PySide6.QtWebEngineWidgets") is not None

_MANUAL_INSTRUCTIONS = (
    "Pega lo que copies de tu navegador con la sesión de music.youtube.com iniciada. Sirve cualquiera de estas opciones:\n\n"
    "• Chrome, Edge, Opera GX, Brave: F12 → Red (Network) → recarga con Ctrl+R → filtra por «browse» → clic "
    "derecho en la petición → Copiar → Copiar como cURL (bash o cmd).\n\n"
    "• Firefox: F12 → Red → clic derecho en una petición a music.youtube.com → Copiar valor → Copiar como "
    "cURL (Windows o POSIX).\n\n"
    "• Cualquier navegador: exporta las cookies de music.youtube.com con la extensión Cookie-Editor (formato "
    "JSON) o como cookies.txt, y pégalas aquí."
)


# login ventana
class LoginWindow(QWidget):
    login_success = Signal()
    login_skipped = Signal()
    closed = Signal()

    def __init__(self, auth, app_icon):
        super().__init__()
        self._auth = auth
        self._app_icon = app_icon
        self._web = None
        self._build()

    def _build(self):
        self.setWindowTitle("Bienvenido a YTMusic Client")
        self.setWindowIcon(self._app_icon)
        self.setFixedSize(400, WINDOW_HEIGHT)
        self.setStyleSheet(f"QWidget {{ background-color: {theme.BG}; }} QLabel {{ background: transparent; }}")

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignCenter)
        self._layout.setSpacing(14)
        self._layout.setContentsMargins(32, 32, 32, 32)

        icon = QLabel()
        icon.setPixmap(self._app_icon.pixmap(96, 96))
        icon.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(icon)

        title = QLabel("YTMusic Minimal Client")
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {theme.TEXT};")
        self._layout.addWidget(title)

        credits_label = QLabel("by RainySen & Moonshine")
        credits_label.setAlignment(Qt.AlignCenter)
        credits_label.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self._layout.addWidget(credits_label)
        self._layout.addStretch(1)

        if self._auth.is_authenticated:
            button = self._make_button("Continuar", "primary")
            button.setDefault(True)
            button.clicked.connect(self.login_skipped)
            self._layout.addWidget(button)
            return

        if WEB_LOGIN_AVAILABLE:
            self._web_button = self._make_button("Iniciar sesión con Google", "primary")
            self._web_button.setIcon(qta.icon("fa5b.google", color=theme.BG))
            self._web_button.clicked.connect(self._login_with_web)
            self._layout.addWidget(self._web_button)

        self._layout.addSpacing(4)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {theme.BORDER};")
        self._layout.addWidget(separator)

        manual = QPushButton("Pegar cURL o cookies")
        manual.clicked.connect(self._manual_login)
        manual.setCursor(Qt.PointingHandCursor)
        manual.setStyleSheet(theme.button_qss("text", height=32))
        self._layout.addWidget(manual)

        skip = self._make_button("Continuar sin sesión", "tonal")
        skip.clicked.connect(self.login_skipped)
        self._layout.addWidget(skip)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    # login google chromium
    def _login_with_web(self):
        if self._web is not None:
            self._web.raise_()
            self._web.activateWindow()
            return
        from ui.web_login_window import WebLoginWindow

        self._web = WebLoginWindow()
        self._web.session_captured.connect(self._on_web_session)
        self._web.closed.connect(self._on_web_closed)
        self._web.start()
        self._web.show()

    def _on_web_session(self, cookies, user_agent):
        self._web_button.setEnabled(False)
        self._web_button.setText("Iniciando sesión…")
        self._auth.login_with_web_session(cookies, user_agent, self._on_web_result)

    def _on_web_closed(self):
        self._web = None

    def _on_web_result(self, ok, error):
        self._web = None
        self._web_button.setEnabled(True)
        self._web_button.setText("Iniciar sesión con Google")
        self._on_manual_result(ok, error)

    # login pegar curl cookies
    def _manual_login(self):
        text = dialogs.prompt_text(self, "Iniciar sesión manualmente", _MANUAL_INSTRUCTIONS, ok="Iniciar sesión",
                                   placeholder="curl 'https://music.youtube.com/youtubei/v1/browse…'  ·  cookies  ·  JSON",
                                   multiline=True)
        if text:
            self._auth.login_with_text(text, self._on_manual_result)

    def _on_manual_result(self, ok, error):
        if ok:
            self.login_success.emit()
        else:
            dialogs.notify(self, "Error al iniciar sesión", f"No se pudo completar el inicio de sesión.\n\n{error}")

    @staticmethod
    def _make_button(text, kind):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(theme.button_qss(kind))
        return button
