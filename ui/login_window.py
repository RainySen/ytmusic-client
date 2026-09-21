import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QMessageBox, QInputDialog, QFrame,
)
from PySide6.QtCore import Qt, Signal
import qtawesome as qta

from utils import parse_curl_headers

_BROWSER_ICONS = {
    "firefox":  "fa5b.firefox-browser",
    "chrome":   "fa5b.chrome",
    "edge":     "fa5b.edge",
    "brave":    "fa5b.brave",
    "opera":    "fa5b.opera",
    "vivaldi":  "fa5s.globe",
    "chromium": "fa5b.chrome",
    "whale":    "fa5s.globe",
}


class LoginWindow(QWidget):
    login_success = Signal()
    login_skipped = Signal()

    # internal signals — emitted from worker threads, delivered in the main thread
    _browsers_found = Signal(list)
    _browser_login_done = Signal(bool, str, str)  # ok, error, browser

    def __init__(self, service, app_icon, is_authenticated):
        super().__init__()
        self.service = service
        self.app_icon = app_icon
        self.is_authenticated = is_authenticated
        self._init_ui()
        if not is_authenticated:
            self._browsers_found.connect(self._on_browsers_detected)
            self._browser_login_done.connect(self._on_browser_login_result)
            self._probe_browsers()

    def _init_ui(self):
        self.setWindowTitle("Bienvenido a YTMusic Client")
        self.setWindowIcon(self.app_icon)
        self.setFixedSize(400, 500)
        self.setStyleSheet("background-color: #060d0e;")

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignCenter)
        self._layout.setSpacing(14)
        self._layout.setContentsMargins(32, 32, 32, 32)

        icon_label = QLabel()
        icon_label.setPixmap(self.app_icon.pixmap(96, 96))
        icon_label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(icon_label)

        title = QLabel("YTMusic Minimal Client")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        self._layout.addWidget(title)

        credits = QLabel("by RainySen & Moonshine")
        credits.setAlignment(Qt.AlignCenter)
        credits.setStyleSheet("font-size: 13px; color: #555;")
        self._layout.addWidget(credits)

        self._layout.addStretch(1)

        if self.is_authenticated:
            btn = self._make_btn("Continuar", "#03adb7", "#00dfe5")
            btn.setDefault(True)
            btn.clicked.connect(self.login_skipped.emit)
            self._layout.addWidget(btn)
            return

        # ── Browser buttons placeholder ─────────────────────────
        self._browser_area = QVBoxLayout()
        self._browser_area.setSpacing(8)

        self._detect_label = QLabel("🔍  Buscando sesiones en navegadores…")
        self._detect_label.setAlignment(Qt.AlignCenter)
        self._detect_label.setStyleSheet("color: #555; font-size: 12px;")
        self._browser_area.addWidget(self._detect_label)

        self._layout.addLayout(self._browser_area)

        # ── Divider + manual option ──────────────────────────────
        self._layout.addSpacing(4)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1e1e1e;")
        self._layout.addWidget(sep)

        manual_btn = QPushButton("Iniciar sesión manualmente (cURL)")
        manual_btn.clicked.connect(self._manual_login)
        manual_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #555; border: none;
                padding: 8px; font-size: 12px;
            }
            QPushButton:hover { color: #aaa; }
        """)
        self._layout.addWidget(manual_btn)

        skip_btn = self._make_btn("Continuar sin sesión", "#1a2728", "#243536", text_color="#888")
        skip_btn.clicked.connect(self.login_skipped.emit)
        self._layout.addWidget(skip_btn)

    def _probe_browsers(self):
        def _worker():
            browsers = self.service.detect_available_browsers()
            self._browsers_found.emit(browsers)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_browsers_detected(self, browsers: list):
        # Remove the "searching" label
        while self._browser_area.count():
            item = self._browser_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if browsers:
            lbl = QLabel("Iniciar sesión con:")
            lbl.setStyleSheet("color: #888; font-size: 12px;")
            lbl.setAlignment(Qt.AlignCenter)
            self._browser_area.addWidget(lbl)

            for browser in browsers:
                icon_name = _BROWSER_ICONS.get(browser, "fa5s.globe")
                try:
                    icon = qta.icon(icon_name, color="white")
                except Exception:
                    icon = qta.icon("fa5s.globe", color="white")
                btn = QPushButton(f"  {browser.capitalize()}")
                btn.setIcon(icon)
                btn.setDefault(len(browsers) == 1)
                btn.setStyleSheet(self._btn_qss("#03adb7", "#00dfe5"))
                btn.clicked.connect(lambda checked=False, b=browser: self._login_from_browser(b))
                self._browser_area.addWidget(btn)
        else:
            lbl = QLabel("No se encontraron sesiones de YouTube en\nningún navegador compatible.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #666; font-size: 12px;")
            self._browser_area.addWidget(lbl)

        self.adjustSize()
        self.setFixedSize(400, max(500, self.sizeHint().height() + 20))

    def _login_from_browser(self, browser: str):
        for i in range(self._browser_area.count()):
            w = self._browser_area.itemAt(i).widget()
            if w:
                w.setEnabled(False)

        status = QLabel(f"⏳  Autenticando con {browser.capitalize()}…")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #888; font-size: 12px;")
        self._browser_area.addWidget(status)
        self._pending_status = status

        def _worker():
            ok, err = self.service.login_from_browser(browser)
            self._browser_login_done.emit(ok, err, browser)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_browser_login_result(self, ok: bool, err: str, browser: str):
        if ok:
            self.login_success.emit()
            return
        if hasattr(self, "_pending_status"):
            self._pending_status.deleteLater()
        for i in range(self._browser_area.count()):
            w = self._browser_area.itemAt(i).widget()
            if w:
                w.setEnabled(True)
        QMessageBox.warning(
            self, "Error de autenticación",
            f"No se pudo autenticar con {browser.capitalize()}:\n{err}\n\n"
            "Asegúrate de estar iniciado sesión en YouTube Music en ese navegador."
        )

    def _manual_login(self):
        instructions = (
            "Para iniciar sesión, sigue estos pasos:\n\n"
            "1. Abre YouTube Music en tu navegador.\n"
            "2. Asegúrate de haber iniciado sesión con tu cuenta.\n"
            "3. Abre las herramientas de desarrollador (F12).\n"
            "4. Ve a la pestaña 'Red' (Network).\n"
            "5. Haz una recarga forzada (Ctrl+Shift+R).\n"
            "6. Filtra por 'browse'.\n"
            "7. Clic derecho en la petición → 'Copiar como cURL (bash)'.\n"
            "8. Pega el texto abajo."
        )
        text, ok = QInputDialog.getMultiLineText(
            self, "Iniciar Sesión — cURL", instructions, text=""
        )
        if ok and text:
            parsed = parse_curl_headers(text)
            if parsed:
                ok2 = self.service.setup_authentication(parsed)
                if ok2:
                    QMessageBox.information(self, "Éxito", "¡Inicio de sesión completado!")
                    self.login_success.emit()
                else:
                    QMessageBox.warning(self, "Error",
                                        "No se pudo completar el inicio de sesión. Verifica las cabeceras.")

    @staticmethod
    def _make_btn(text, bg, hover, text_color="white"):
        btn = QPushButton(text)
        btn.setStyleSheet(LoginWindow._btn_qss(bg, hover, text_color))
        return btn

    @staticmethod
    def _btn_qss(bg, hover, text_color="white"):
        return f"""
            QPushButton {{
                background: {bg}; color: {text_color}; border: none;
                padding: 12px; border-radius: 8px; font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {hover}; }}
            QPushButton:disabled {{ background: #1a2728; color: #444; }}
        """
