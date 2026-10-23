from typing import Callable

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QDesktopServices

from services.update_service import UpdateService
from ui.main_window import MainWindow

UPDATE_CHECK_DELAY_MS = 8000


def _open_in_browser(url: str) -> None:
    QDesktopServices.openUrl(QUrl(url))


class UpdatePresenter:
    def __init__(self, window: MainWindow, updates: UpdateService,
                 open_url: Callable[[str], None] = _open_in_browser, delay_ms: int = UPDATE_CHECK_DELAY_MS):
        self._updates = updates
        self._open_url = open_url
        self._delay_ms = delay_ms
        self._release: tuple[str, str] | None = None
        self._banner = window.update_banner
        self._banner.open_requested.connect(self._open)
        self._banner.dismissed.connect(self._dismiss)

    # after startup so the check never competes with the first loads
    def start(self) -> None:
        QTimer.singleShot(self._delay_ms, self.check_now)

    def check_now(self) -> None:
        self._updates.check(self._show)

    def _show(self, version: str, url: str) -> None:
        self._release = (version, url)
        self._banner.show_version(version)

    def _open(self) -> None:
        if self._release:
            self._open_url(self._release[1])
        self._dismiss()

    def _dismiss(self) -> None:
        if self._release:
            self._updates.dismiss(self._release[0])
            self._release = None
