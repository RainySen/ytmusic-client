from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject, Signal

from infra import browser_cookies
from infra.concurrency import TaskRunner
from infra.session_import import session_headers
from infra.ytmusic_gateway import GatewayError, YTMusicGateway

log = logging.getLogger(__name__)

LoginDone = Callable[[bool, str], None]


# login sesion
class AuthService(QObject):
    auth_changed = Signal(bool)

    def __init__(self, gateway: YTMusicGateway, runner: TaskRunner, parent: QObject | None = None):
        super().__init__(parent)
        self._gateway = gateway
        self._runner = runner

    @property
    def is_authenticated(self) -> bool:
        return self._gateway.is_authenticated

    def detect_browsers(self, on_done: Callable[[list[str]], None]) -> None:
        names = list(browser_cookies.SUPPORTED_BROWSERS)
        probes = [(lambda b=name: browser_cookies.has_youtube_session(b)) for name in names]

        def finish(results: list) -> None:
            on_done([n for n, found in zip(names, results) if found is True])

        self._runner.gather(probes, finish, key="auth:detect")

    # login navegador
    def login_with_browser(self, browser: str, on_done: LoginDone) -> None:
        self._authenticate(lambda: browser_cookies.build_headers(browser), on_done)

    # login pegar curl cookies
    def login_with_text(self, pasted: str, on_done: LoginDone) -> None:
        self._authenticate(lambda: session_headers(pasted), on_done)

    def _authenticate(self, build_headers: Callable[[], dict[str, str]], on_done: LoginDone) -> None:
        def work() -> None:
            self._gateway.authenticate(build_headers())

        def ok(_: None) -> None:
            self.auth_changed.emit(True)
            on_done(True, "")

        def fail(exc: Exception) -> None:
            log.info("Login failed: %s", exc)
            on_done(False, str(exc))

        self._runner.submit(work, ok, fail, key="auth:login")

    def logout(self) -> bool:
        try:
            self._gateway.logout()
        except GatewayError:
            log.warning("Logout failed", exc_info=True)
            return False
        self.auth_changed.emit(False)
        return True
