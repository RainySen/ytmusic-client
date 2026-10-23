from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from infra.concurrency import TaskRunner
from infra.session_import import cookies_to_headers, session_headers
from infra.ytmusic_gateway import GatewayError, SessionRejected, YTMusicGateway

log = logging.getLogger(__name__)

LoginDone = Callable[[bool, str], None]

# transient rejections: sign out only on the second one
RECHECK_MS = 2 * 60 * 1000


class AuthService(QObject):
    auth_changed = Signal(bool)
    session_expired = Signal()
    # explicit logout only, not on expiry
    logged_out = Signal()

    def __init__(self, gateway: YTMusicGateway, runner: TaskRunner, parent: QObject | None = None):
        super().__init__(parent)
        self._gateway = gateway
        self._runner = runner
        self._rejected_once = False

    @property
    def is_authenticated(self) -> bool:
        return self._gateway.is_authenticated

    def verify_session(self) -> None:
        if not self._gateway.is_authenticated:
            return

        def accepted(_: None) -> None:
            self._rejected_once = False

        def rejected(exc: Exception) -> None:
            if not isinstance(exc, SessionRejected):
                log.debug("Session check skipped: %s", exc)
                return
            if not self._rejected_once:
                self._rejected_once = True
                log.warning("Session rejected by YouTube, checking again in %d s: %s", RECHECK_MS // 1000, exc)
                QTimer.singleShot(RECHECK_MS, self.verify_session)
                return
            self._rejected_once = False
            log.warning("Session rejected by YouTube again: %s", exc)
            self._gateway.mark_signed_out()
            self.auth_changed.emit(False)
            self.session_expired.emit()

        self._runner.submit(self._gateway.verify_session, accepted, rejected, key="auth:verify")

    def login_with_text(self, pasted: str, on_done: LoginDone) -> None:
        self._authenticate(lambda: session_headers(pasted), on_done)

    def login_with_web_session(self, cookies: dict[str, str], user_agent: str, on_done: LoginDone) -> None:
        self._authenticate(lambda: cookies_to_headers(cookies, user_agent=user_agent), on_done)

    def _authenticate(self, build_headers: Callable[[], dict[str, str]], on_done: LoginDone) -> None:
        def work() -> None:
            self._gateway.authenticate(build_headers())

        def ok(_: None) -> None:
            self._rejected_once = False
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
        self.logged_out.emit()
        return True
