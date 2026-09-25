from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot

log = logging.getLogger(__name__)


# vlc audio
class VlcAudioBackend(QObject):
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    time_ms_changed = Signal(int)
    finished = Signal()
    failed = Signal()

    _vlc_end = Signal()
    _vlc_error = Signal()

    def __init__(self, network_caching_ms: int = 1500, parent: QObject | None = None):
        super().__init__(parent)
        self._network_caching_ms = network_caching_ms
        self._init_lock = threading.Lock()
        self._instance = None
        self._player = None
        self._playing = False
        self._has_media = False
        self._volume = 100

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll)

        self._vlc_end.connect(self._handle_end, Qt.QueuedConnection)
        self._vlc_error.connect(self._handle_error, Qt.QueuedConnection)

    def warm_up(self) -> None:
        self._ensure()

    def _ensure(self):
        if self._player is None:
            with self._init_lock:
                if self._player is None:
                    import vlc

                    instance = vlc.Instance(
                        "--no-video", "--no-video-title-show",
                        f"--network-caching={self._network_caching_ms}",
                    )
                    player = instance.media_player_new()
                    events = player.event_manager()
                    events.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_end)
                    events.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_vlc_error)
                    self._instance, self._player = instance, player
        return self._player

    def _on_vlc_end(self, _event) -> None:
        self._vlc_end.emit()

    def _on_vlc_error(self, _event) -> None:
        self._vlc_error.emit()

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def has_media(self) -> bool:
        return self._has_media

    # vlc reproducir
    def play_url(self, url: str) -> None:
        player = self._ensure()
        player.set_media(self._instance.media_new(url))
        player.play()
        player.audio_set_volume(self._volume)
        self._has_media = True
        self._playing = True
        self._timer.start()

    def pause(self) -> None:
        if self._player is not None and self._has_media:
            self._player.set_pause(1)
            self._playing = False
            self._timer.stop()

    def resume(self) -> None:
        if self._player is not None and self._has_media:
            self._player.set_pause(0)
            self._playing = True
            self._timer.start()

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()
        self._playing = False
        self._has_media = False
        self._timer.stop()

    def seek(self, fraction: float) -> None:
        if self._player is not None and self._has_media:
            self._player.set_position(max(0.0, min(1.0, fraction)))

    def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, int(volume)))
        if self._player is not None:
            self._player.audio_set_volume(self._volume)

    @Slot()
    def _handle_end(self) -> None:
        self._playing = False
        self._has_media = False
        self._timer.stop()
        self.finished.emit()

    @Slot()
    def _handle_error(self) -> None:
        self._playing = False
        self._has_media = False
        self._timer.stop()
        self.failed.emit()

    # tiempo progreso
    def _poll(self) -> None:
        player = self._player
        if player is None or not self._playing:
            return
        position = player.get_position()
        total_s = player.get_length() // 1000
        if position >= 0 and total_s > 0:
            time_ms = player.get_time()
            self.position_changed.emit(position)
            self.time_changed.emit(max(0, time_ms) // 1000, total_s)
            self.time_ms_changed.emit(max(0, time_ms))
