from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject, Signal

from infra.concurrency import TaskRunner
from infra.session_import import cookies_to_headers, session_headers
from infra.ytmusic_gateway import GatewayError, SessionRejected, YTMusicGateway

log = logging.getLogger(__name__)

LoginDone = Callable[[bool, str], None]


# login sesion
class AuthService(QObject):
    auth_changed = Signal(bool)
    session_expired = Signal()

    def __init__(self, gateway: YTMusicGateway, runner: TaskRunner, parent: QObject | None = None):
        super().__init__(parent)
        self._gateway = gateway
        self._runner = runner

    @property
    def is_authenticated(self) -> bool:
        return self._gateway.is_authenticated

    # login sesion caducada aviso
    def verify_session(self) -> None:
        if not self._gateway.is_authenticated:
            return

        def rejected(exc: Exception) -> None:
            if isinstance(exc, SessionRejected):
                log.warning("Session rejected by YouTube: %s", exc)
                self.auth_changed.emit(False)
                self.session_expired.emit()
            else:
                log.debug("Session check skipped: %s", exc)

        self._runner.submit(self._gateway.verify_session, None, rejected, key="auth:verify")

    # login pegar curl cookies
    def login_with_text(self, pasted: str, on_done: LoginDone) -> None:
        self._authenticate(lambda: session_headers(pasted), on_done)

    def login_with_web_session(self, cookies: dict[str, str], user_agent: str, on_done: LoginDone) -> None:
        self._authenticate(lambda: cookies_to_headers(cookies, user_agent=user_agent), on_done)

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
