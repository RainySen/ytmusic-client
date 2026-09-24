from typing import Callable

from PySide6.QtWidgets import QWidget

from presenters.home_presenter import HomePresenter
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.notifier import Notifier
from ui.main_window import MainWindow


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

    def start(self) -> None:
        self._window.set_auth_state(self._auth.is_authenticated)

    def open_login(self) -> None:
        if self._login_window is not None:
            self._login_window.raise_()
            self._login_window.activateWindow()
            return
        login = self._make_login_window()
        login.login_success.connect(lambda: (self._close_login(), self._notifier.info("Sesión iniciada.")))
        login.login_skipped.connect(self._close_login)
        self._login_window = login
        login.show()

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
