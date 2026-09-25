from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from infra.web_session import WebSessionCookies, firefox_disguise_script, google_login_user_agent
from ui import theme

LOGIN_URL = (
    "https://accounts.google.com/ServiceLogin?ltmpl=music&service=youtube&continue="
    "https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop"
    "%26next%3Dhttps%3A%2F%2Fmusic.youtube.com%2F"
)
MUSIC_HOST = "music.youtube.com"
SETTLE_MS = 1200
DISGUISE_SCRIPT_NAME = "firefox-disguise"


# login google chromium embebido
class WebLoginWindow(QWidget):
    session_captured = Signal(dict, str)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self._cookies = WebSessionCookies()
        self._done = False
        self._disposed = False
        self._on_music = False

        self.setWindowTitle("Iniciar sesión con Google")
        self.resize(520, 720)
        self.setStyleSheet(f"background: {theme.BG};")

        self._profile = QWebEngineProfile(self)
        self._user_agent = google_login_user_agent()
        self._profile.setHttpUserAgent(self._user_agent)
        self._profile.setHttpAcceptLanguage("es-419,es;q=0.9,en;q=0.8")
        disguise = QWebEngineScript()
        disguise.setName(DISGUISE_SCRIPT_NAME)
        disguise.setSourceCode(firefox_disguise_script())
        disguise.setInjectionPoint(QWebEngineScript.DocumentCreation)
        disguise.setWorldId(QWebEngineScript.MainWorld)
        disguise.setRunsOnSubFrames(True)
        self._profile.scripts().insert(disguise)
        self._page = QWebEnginePage(self._profile, self)
        self._view = QWebEngineView(self)
        self._view.setPage(self._page)

        self._status = QLabel("Cargando…")
        self._status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; padding: 6px 12px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._status)
        layout.addWidget(self._view, stretch=1)

        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SETTLE_MS)
        self._settle.timeout.connect(self._finish_if_ready)

        store = self._profile.cookieStore()
        store.cookieAdded.connect(self._on_cookie_added)
        store.cookieRemoved.connect(self._on_cookie_removed)
        store.loadAllCookies()
        self._page.urlChanged.connect(self._on_url)
        self._page.loadFinished.connect(lambda ok: self._status.setText("" if ok else "No se pudo cargar la página."))

    def start(self) -> None:
        self._page.load(QUrl(LOGIN_URL))

    def _on_cookie_added(self, cookie) -> None:
        self._cookies.add(cookie.domain(), bytes(cookie.name()).decode(), bytes(cookie.value()).decode())
        if self._on_music:
            self._settle.start()

    def _on_cookie_removed(self, cookie) -> None:
        self._cookies.remove(cookie.domain(), bytes(cookie.name()).decode())

    def _on_url(self, url: QUrl) -> None:
        self._on_music = url.host() == MUSIC_HOST
        if self._on_music:
            self._settle.start()

    def _finish_if_ready(self) -> None:
        if self._done or not self._on_music or not self._cookies.has_session():
            return
        self._done = True
        self.session_captured.emit(self._cookies.snapshot(), self._user_agent)
        self.close()

    def _dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._settle.stop()
        self._view.deleteLater()
        self._page.destroyed.connect(self._profile.deleteLater)
        self._page.deleteLater()

    def closeEvent(self, event) -> None:
        if not self._done:
            self.closed.emit()
        self._dispose()
        super().closeEvent(event)
