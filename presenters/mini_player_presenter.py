from __future__ import annotations

from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from domain.models import artist_names, primary_artist
from domain.settings import Settings
from services.playback_service import PlaybackService
from services.settings_service import SettingsService
from ui.components.mini_player import MiniPlayer
from ui.main_window import MainWindow

MINI_MARGIN = 24


class MiniPlayerPresenter:
    def __init__(self, window: MainWindow, playback: PlaybackService, settings: SettingsService,
                 mini: MiniPlayer | None = None):
        self._window = window
        self._playback = playback
        self._settings = settings
        self._mini = mini or MiniPlayer()
        self._dismissed = False
        mini = self._mini

        window.presence_changed.connect(self._on_presence)
        settings.changed.connect(lambda _settings: self._refresh())

        playback.track_loading.connect(self._on_track)
        playback.track_started.connect(self._on_track)
        playback.playing_changed.connect(mini.set_playing)
        playback.progress.connect(mini.set_position)
        playback.queue.changed.connect(self._update_neighbors)
        playback.queue.loop_mode_changed.connect(lambda _mode: self._update_neighbors())

        mini.toggle_requested.connect(window.play_pause_clicked)
        mini.next_requested.connect(window.next_clicked)
        mini.previous_requested.connect(window.previous_clicked)
        mini.expand_requested.connect(window.bring_to_front)
        mini.close_requested.connect(self._dismiss)
        mini.moved.connect(lambda x, y: settings.update(mini_x=x, mini_y=y))

    @property
    def mini(self) -> MiniPlayer:
        return self._mini

    def _on_track(self, song: dict) -> None:
        title = song.get("title", "")
        self._mini.set_track(title, artist_names(song, limit=2) or primary_artist(song))
        self._update_neighbors()
        self._refresh()

    def _update_neighbors(self) -> None:
        queue = self._playback.queue
        self._mini.set_neighbors(self._describe(queue.peek_previous()), self._describe(queue.peek_next()))

    @staticmethod
    def _describe(song: dict | None) -> str:
        if not song:
            return ""
        artist = artist_names(song, limit=2) or primary_artist(song)
        return f"{song.get('title', '')} — {artist}" if artist else song.get("title", "")

    def _dismiss(self) -> None:
        self._dismissed = True
        self._refresh()

    def _on_presence(self, presented: bool) -> None:
        if presented:
            self._dismissed = False
        self._refresh()

    def _refresh(self) -> None:
        settings = self._settings.settings
        background = settings.background_on_close and QSystemTrayIcon.isSystemTrayAvailable()
        wanted = (settings.mini_player and background and not self._dismissed and not self._window.is_presented
                  and self._playback.queue.current is not None)
        if not wanted:
            self._mini.hide()
            return
        if not self._mini.isVisible():
            self._place(settings)
        self._mini.show()

    def _place(self, settings: Settings) -> None:
        if settings.mini_x is not None and settings.mini_y is not None:
            self._mini.move(settings.mini_x, settings.mini_y)
            return
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self._mini.move(area.right() - self._mini.width() - MINI_MARGIN,
                            area.bottom() - self._mini.height() - MINI_MARGIN)
