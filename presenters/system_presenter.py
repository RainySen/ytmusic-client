from __future__ import annotations

from domain.models import artist_names, primary_artist
from domain.settings import Settings
from services.playback_service import PlaybackService
from services.settings_service import SettingsService
from ui.main_window import MainWindow


class SystemPresenter:
    def __init__(self, window: MainWindow, playback: PlaybackService, settings: SettingsService,
                 media_keys, autostart):
        self._window = window
        self._settings = settings
        self._media_keys = media_keys
        self._autostart = autostart
        self._last_notified = ""
        self._applied: tuple[bool, bool] | None = None

        media_keys.play_pause.connect(window.play_pause_clicked)
        media_keys.next_track.connect(window.next_clicked)
        media_keys.previous_track.connect(window.previous_clicked)
        playback.track_started.connect(self._on_track)
        settings.changed.connect(self._apply)

    def start(self) -> None:
        self._apply(self._settings.settings)

    def _apply(self, settings: Settings) -> None:
        wanted = (settings.media_keys, settings.start_with_windows)
        if wanted == self._applied:
            return
        previous, self._applied = self._applied, wanted
        if previous is None or previous[0] != settings.media_keys:
            self._media_keys.set_enabled(settings.media_keys)
        if previous is None or previous[1] != settings.start_with_windows:
            self._sync_autostart(settings.start_with_windows)

    def _sync_autostart(self, enabled: bool) -> None:
        if not enabled and not self._autostart.is_enabled():
            return
        if not self._autostart.set_enabled(enabled) and enabled:
            self._applied = (self._applied[0], False)
            self._settings.update(start_with_windows=False)

    def _on_track(self, song: dict) -> None:
        video_id = song.get("videoId", "")
        if not self._settings.settings.notifications or self._window.is_presented or video_id == self._last_notified:
            return
        self._last_notified = video_id
        self._window.notify(song.get("title", ""), artist_names(song, limit=2) or primary_artist(song))
