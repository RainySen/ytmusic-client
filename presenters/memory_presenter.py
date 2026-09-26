from __future__ import annotations

from PySide6.QtCore import QTimer

from infra import memory
from presenters.explore_presenter import ExplorePresenter
from presenters.home_presenter import HomePresenter
from services.settings_service import SettingsService
from ui.main_window import MainWindow

RELEASE_DELAY_MS = 20_000


# liberar ram en segundo plano
class MemoryPresenter:
    def __init__(self, window: MainWindow, home: HomePresenter, explore: ExplorePresenter,
                 delay_ms: int = RELEASE_DELAY_MS, settings: SettingsService | None = None):
        self._window = window
        self._settings = settings
        self._home = home
        self._explore = explore
        self._released = False
        self._timer = QTimer(window)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self.release)
        window.presence_changed.connect(self._on_presence)

    def _on_presence(self, presented: bool) -> None:
        if presented:
            self._timer.stop()
            self.restore()
        else:
            self.start_hidden()

    # arranque oculto liberar tras la espera
    def start_hidden(self) -> None:
        if self._settings is None or self._settings.settings.free_memory:
            if self._settings is not None:
                self._timer.setInterval(self._settings.settings.free_memory_seconds * 1000)
            self._timer.start()

    def release(self) -> None:
        if self._window.is_presented or self._released:
            return
        self._released = True
        self._home.release()
        self._explore.release()
        self._window.side_panel.release_queue()
        self._window.thumbnails.clear_memory()
        memory.trim()

    # boton liberar ram ahora sin tocar lo visible
    def free_now(self) -> tuple[int, int]:
        before = memory.working_set_mb()
        view = self._window.current_view
        if view != "home":
            self._home.release()
        if view != "explore":
            self._explore.release()
        if not self._window.side_panel.isVisible():
            self._window.side_panel.release_queue()
        self._window.thumbnails.clear_memory()
        memory.trim()
        return before, memory.working_set_mb()

    def restore(self) -> None:
        if not self._released:
            return
        self._released = False
        view = self._window.current_view
        if view == "home":
            self._home.show()
        elif view == "explore":
            self._explore.show()
