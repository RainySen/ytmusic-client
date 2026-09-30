from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from infra import memory
from presenters.explore_presenter import ExplorePresenter
from presenters.home_presenter import HomePresenter
from services.settings_service import SettingsService
from ui.main_window import MainWindow

RELEASE_DELAY_MS = 20_000
TRIM_EVERY_MS = 60_000


class MemoryPresenter:
    def __init__(self, window: MainWindow, home: HomePresenter, explore: ExplorePresenter,
                 delay_ms: int = RELEASE_DELAY_MS, settings: SettingsService | None = None):
        self._window = window
        self._settings = settings
        self._home = home
        self._explore = explore
        self._released = False
        self._reloads: dict[str, Callable[[], None]] = {}
        self._timer = QTimer(window)
        self._timer.setSingleShot(True)
        self._timer.setInterval(delay_ms)
        self._timer.timeout.connect(self.release)
        # os pages memory back in; trim again while hidden
        self._trim_timer = QTimer(window)
        self._trim_timer.setInterval(TRIM_EVERY_MS)
        self._trim_timer.timeout.connect(memory.trim)
        # visible window: clean only when idle or in background
        self._idle_timer = QTimer(window)
        self._idle_timer.timeout.connect(self._on_idle_tick)
        window.presence_changed.connect(self._on_presence)
        if settings is not None:
            settings.changed.connect(lambda _current: self._schedule_idle())
        self._schedule_idle()

    def _schedule_idle(self) -> None:
        if self._settings is None or not self._settings.settings.free_memory:
            self._idle_timer.stop()
            return
        interval = self._settings.settings.free_memory_seconds * 1000
        if not self._idle_timer.isActive() or self._idle_timer.interval() != interval:
            self._idle_timer.start(interval)

    def _on_idle_tick(self) -> None:
        if not self._window.is_presented or self._released:
            return
        seconds = self._settings.settings.free_memory_seconds
        if QApplication.activeWindow() is None or memory.idle_seconds() >= seconds:
            self.free_now()

    def on_restore(self, view: str, reload: Callable[[], None]) -> None:
        self._reloads[view] = reload

    def _on_presence(self, presented: bool) -> None:
        if presented:
            self._timer.stop()
            self._trim_timer.stop()
            self.restore()
        else:
            self.start_hidden()

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
        self._release_pages(keep=None)
        self._window.side_panel.release_queue()
        self._window.sidebar.release_rail()
        self._window.thumbnails.clear_memory()
        memory.trim()
        self._trim_timer.start()

    def free_now(self) -> tuple[int, int]:
        before = memory.working_set_mb()
        view = self._window.current_view
        if view != "home":
            self._home.release()
        if view != "explore":
            self._explore.release()
        self._release_pages(keep=view)
        if not self._window.side_panel.isVisible():
            self._window.side_panel.release_queue()
        self._window.sidebar.release_rail()
        self._window.thumbnails.clear_memory()
        memory.trim()
        return before, memory.working_set_mb()

    def _release_pages(self, keep: str | None) -> None:
        window = self._window
        for view, panel in (("album", window.album_panel), ("artist", window.artist_panel),
                            ("library", window.library_browser)):
            if view != keep:
                panel.release()

    def restore(self) -> None:
        if not self._released:
            return
        self._released = False
        view = self._window.current_view
        if view == "home":
            self._home.show()
        elif view == "explore":
            self._explore.show()
        elif view in self._reloads:
            self._reloads[view]()
