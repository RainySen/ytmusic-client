from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from presenters.home_presenter import HomePresenter
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.notifier import Notifier
from ui.main_window import MainWindow


SESSION_CHECK_MS = 30 * 60 * 1000


# login ventana
class AuthPresenter:
    def __init__(self, window: MainWindow, auth: AuthService, catalog: CatalogService,
                 home: HomePresenter, login_window_factory: Callable[[], QWidget], notifier: Notifier):
        self._window = window
        self._auth = auth
        self._catalog = catalog
        self._home = home
        self._make_login_window = login_window_factory
        self._notifier = notifier
        self._login_window: QWidget | None = None

        window.login_requested.connect(self.open_login)
        window.logout_requested.connect(self.logout)
        auth.auth_changed.connect(self._on_auth_changed)
        auth.session_expired.connect(self._on_session_expired)
        self._asked = False
        self._checker = QTimer()
        self._checker.setInterval(SESSION_CHECK_MS)
        self._checker.timeout.connect(self._auth.verify_session)

    def start(self) -> None:
        self._window.set_auth_state(self._auth.is_authenticated)
        self._auth.verify_session()
        self._checker.start()

    def _on_session_expired(self) -> None:
        if self._asked:
            return
        self._asked = True
        if self._window.ask_relogin():
            self.open_login()

    def open_login(self) -> None:
        if self._login_window is not None:
            self._login_window.raise_()
            self._login_window.activateWindow()
            return
        login = self._make_login_window()
        login.login_success.connect(lambda: (self._close_login(), self._notifier.info("Sesión iniciada."), self._reset_asked()))
        login.login_skipped.connect(self._close_login)
        self._login_window = login
        login.show()

    def _reset_asked(self) -> None:
        self._asked = False

    def _close_login(self) -> None:
        if self._login_window is not None:
            self._login_window.close()
            self._login_window.deleteLater()
            self._login_window = None

    def logout(self) -> None:
        if self._auth.logout():
            self._notifier.info("Sesión cerrada.")
        else:
            self._notifier.error("No se pudo cerrar la sesión.")

    def _on_auth_changed(self, authenticated: bool) -> None:
        self._window.set_auth_state(authenticated)
        self._catalog.clear_cache()
        self._home.refresh(force=True)
