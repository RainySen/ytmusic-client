import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from ui import theme
from ui.components import dialogs

_BROWSER_ICONS = {
    "firefox": "fa5b.firefox-browser",
    "chrome": "fa5b.chrome",
    "edge": "fa5b.edge",
    "brave": "fa5b.brave",
    "opera": "fa5b.opera",
    "vivaldi": "fa5s.globe",
    "chromium": "fa5b.chrome",
    "whale": "fa5s.globe",
}

_MANUAL_INSTRUCTIONS = (
    "Pega lo que copies de tu navegador con la sesión de music.youtube.com iniciada. Sirve cualquiera de estas opciones:\n\n"
    "• Chrome, Edge, Opera GX, Brave: F12 → Red (Network) → recarga con Ctrl+R → filtra por «browse» → clic "
    "derecho en la petición → Copiar → Copiar como cURL (bash o cmd).\n\n"
    "• Firefox: usa el botón «Firefox» de la pantalla anterior. Si no aparece: F12 → Red → clic derecho en una "
    "petición a music.youtube.com → Copiar → Copiar como cURL.\n\n"
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
        self._status = None
        self._build()
        if not auth.is_authenticated:
            self._auth.detect_browsers(self._on_browsers_detected)

    def _build(self):
        self.setWindowTitle("Bienvenido a YTMusic Client")
        self.setWindowIcon(self._app_icon)
        self.setFixedSize(400, 500)
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

        self._browser_area = QVBoxLayout()
        self._browser_area.setSpacing(8)
        self._detect_label = QLabel("🔍  Buscando sesiones en navegadores…")
        self._detect_label.setAlignment(Qt.AlignCenter)
        self._detect_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        self._browser_area.addWidget(self._detect_label)
        self._layout.addLayout(self._browser_area)

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

    def _clear_browser_area(self):
        while self._browser_area.count():
            widget = self._browser_area.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()

    def _on_browsers_detected(self, browsers):
        self._clear_browser_area()
        if browsers:
            label = QLabel("Iniciar sesión con:")
            label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
            label.setAlignment(Qt.AlignCenter)
            self._browser_area.addWidget(label)
            for browser in browsers:
                button = QPushButton(f"  {browser.capitalize()}")
                button.setIcon(qta.icon(_BROWSER_ICONS.get(browser, "fa5s.globe"), color=theme.BG))
                button.setDefault(len(browsers) == 1)
                button.setCursor(Qt.PointingHandCursor)
                button.setStyleSheet(theme.button_qss("primary"))
                button.clicked.connect(lambda _=False, b=browser: self._login_with_browser(b))
                self._browser_area.addWidget(button)
        else:
            label = QLabel("No se encontraron sesiones de YouTube en\nningún navegador compatible.")
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
            self._browser_area.addWidget(label)
        self.adjustSize()
        self.setFixedSize(400, max(500, self.sizeHint().height() + 20))

    def _set_browser_buttons_enabled(self, enabled):
        for index in range(self._browser_area.count()):
            widget = self._browser_area.itemAt(index).widget()
            if widget is not None:
                widget.setEnabled(enabled)

    def _login_with_browser(self, browser):
        self._set_browser_buttons_enabled(False)
        self._status = QLabel(f"⏳  Autenticando con {browser.capitalize()}…")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        self._browser_area.addWidget(self._status)
        self._auth.login_with_browser(browser, lambda ok, err: self._on_browser_result(ok, err, browser))

    def _on_browser_result(self, ok, error, browser):
        if ok:
            self.login_success.emit()
            return
        if self._status is not None:
            self._status.deleteLater()
            self._status = None
        self._set_browser_buttons_enabled(True)
        dialogs.notify(
            self, "Error de autenticación",
            f"No se pudo autenticar con {browser.capitalize()}:\n{error}\n\n"
            "Asegúrate de estar iniciado sesión en YouTube Music en ese navegador.",
        )

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
