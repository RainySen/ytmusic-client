from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QSystemTrayIcon

from domain.settings import Settings
from services.settings_service import SettingsService
from ui import imaging
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog

VOLUME_SAVE_MS = 600


class SettingsPresenter:
    def __init__(self, window: MainWindow, settings: SettingsService,
                 free_now: Callable[[], tuple[int, int]] | None = None, cache=None,
                 on_language: Callable[[str], None] | None = None, autostart_available: bool = True,
                 thumbnails=None):
        self._window = window
        self._free_now = free_now
        self._cache = cache
        self._on_language = on_language
        self._language = settings.settings.content_language
        self._autostart_available = autostart_available
        self._thumbnails = thumbnails
        self._settings = settings
        self._restoring = False
        self._volume_timer = QTimer(window)
        self._volume_timer.setSingleShot(True)
        self._volume_timer.setInterval(VOLUME_SAVE_MS)
        self._volume_timer.timeout.connect(self._save_volume)

        window.settings_requested.connect(self.open)
        window.volume_changed.connect(self._on_volume)
        settings.changed.connect(self._apply)
        self._apply(settings.settings)

    def start(self) -> None:
        current = self._settings.settings
        if current.remember_volume:
            self._restoring = True
            self._window.player_panel.volume_slider.setValue(current.volume)
            self._restoring = False

    def open(self) -> None:
        dialog = SettingsDialog(
            self._window, self._settings.settings, QSystemTrayIcon.isSystemTrayAvailable(), self._settings.update,
            self._free_now, cache_size=self._cache.size_bytes if self._cache else None,
            clear_cache=self._cache.clear if self._cache else None, logged_in=self._window.logged_in,
            on_account=self._account_action, autostart_available=self._autostart_available)
        dialog.exec()

    def _account_action(self) -> None:
        QTimer.singleShot(0, self._window, self._window.account_action)

    def _apply(self, settings: Settings) -> None:
        self._window.set_close_to_tray(settings.background_on_close)
        imaging.set_thumbnail_quality(settings.thumbnail_quality)
        if self._thumbnails is not None:
            self._thumbnails.set_max_items(settings.thumbnail_cache_limit)
        if settings.content_language != self._language:
            self._language = settings.content_language
            if self._on_language is not None:
                self._on_language(settings.content_language)

    def _on_volume(self, _volume: int) -> None:
        if not self._restoring and self._settings.settings.remember_volume:
            self._volume_timer.start()

    def _save_volume(self) -> None:
        self._settings.update(volume=self._window.volume)
