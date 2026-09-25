import logging

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from infra.web_session import WebSessionCookies, firefox_disguise_script, google_login_user_agent
from ui import theme

log = logging.getLogger(__name__)

LOGIN_URL = (
    "https://accounts.google.com/ServiceLogin?ltmpl=music&service=youtube&continue="
    "https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop"
    "%26next%3Dhttps%3A%2F%2Fmusic.youtube.com%2F"
)
MUSIC_URL = "https://music.youtube.com/"
MUSIC_HOST = "music.youtube.com"
AUTH_HOST = "accounts.google.com"
CONSENT_HOST = "consent.youtube.com"
YOUTUBE_HOSTS = ("www.youtube.com", "m.youtube.com", "youtube.com")
SETTLE_MS = 1200
HANDOFF_DELAY_MS = 1500
MAX_HANDOFFS = 2
DISGUISE_SCRIPT_NAME = "firefox-disguise"
WAITING_HINT = "Terminando de iniciar sesión…"
NO_SESSION_HINT = "Todavía no se detecta tu sesión de Google. Termina de iniciar sesión primero."


# ventanas nuevas en la misma pagina
class LoginPage(QWebEnginePage):
    def createWindow(self, _window_type):
        child = QWebEnginePage(self.profile(), self)
        child.urlChanged.connect(lambda url: self._follow(child, url))
        return child

    def _follow(self, child: QWebEnginePage, url: QUrl) -> None:
        if url.isEmpty() or url.toString() == "about:blank":
            return
        self.load(url)
        child.deleteLater()


# login google chromium embebido
class WebLoginWindow(QWidget):
    session_captured = Signal(dict, str)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cookies = WebSessionCookies()
        self._done = False
        self._disposed = False
        self._on_music = False
        self._handoffs = 0

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
        self._page = LoginPage(self._profile, self)
        self._view = QWebEngineView(self)
        self._view.setPage(self._page)

        self._status = QLabel("Cargando…")
        self._status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; padding: 6px 12px;")
        self._continue = QPushButton("Ya inicié sesión, continuar")
        self._continue.setCursor(Qt.PointingHandCursor)
        self._continue.setStyleSheet(theme.button_qss("tonal", height=32))
        self._continue.clicked.connect(self.continue_manually)
        footer = QHBoxLayout()
        footer.setContentsMargins(12, 8, 12, 8)
        hint = QLabel("¿Ya entraste pero no avanza?")
        hint.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        footer.addWidget(hint, stretch=1)
        footer.addWidget(self._continue)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._status)
        layout.addWidget(self._view, stretch=1)
        layout.addLayout(footer)

        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SETTLE_MS)
        self._settle.timeout.connect(self._finish_if_ready)
        self._handoff_timer = QTimer(self)
        self._handoff_timer.setSingleShot(True)
        self._handoff_timer.setInterval(HANDOFF_DELAY_MS)
        self._handoff_timer.timeout.connect(self._handoff_if_needed)

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
        log.info("login page: %s%s (google=%s youtube=%s)", url.host(), url.path(),
                 self._cookies.has_google_session(), self._cookies.has_session())
        if self._on_music:
            self._settle.start()
        else:
            self._handoff_timer.start()

    # google salio de accounts y no llego a music
    def _handoff_if_needed(self) -> None:
        if self._done or self._on_music:
            return
        host = self._page.url().host()
        if host in (AUTH_HOST, CONSENT_HOST, "") or not self._cookies.has_google_session():
            return
        if host in YOUTUBE_HOSTS:
            if self._cookies.has_session():
                log.info("login: signed in on %s, opening music", host)
                self._page.load(QUrl(MUSIC_URL))
            return
        if self._handoffs >= MAX_HANDOFFS:
            return
        self._handoffs += 1
        log.info("login: signed in on %s, continuing to youtube music (%d)", host, self._handoffs)
        self._status.setText(WAITING_HINT)
        self._page.load(QUrl(LOGIN_URL))

    def continue_manually(self) -> None:
        if not self._cookies.has_google_session():
            self._status.setText(NO_SESSION_HINT)
            return
        log.info("login: manual continue from %s", self._page.url().host())
        self._status.setText(WAITING_HINT)
        self._page.load(QUrl(LOGIN_URL))

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
        self._handoff_timer.stop()
        self._view.deleteLater()
        self._page.destroyed.connect(self._profile.deleteLater)
        self._page.deleteLater()

    def closeEvent(self, event) -> None:
        if not self._done:
            self.closed.emit()
        self._dispose()
        super().closeEvent(event)
