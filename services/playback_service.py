from __future__ import annotations

import logging
from typing import Protocol

from PySide6.QtCore import QObject, Signal

from core.config import EXTEND_BATCH, MAX_CONSECUTIVE_PLAY_FAILURES, PREFETCH_AHEAD, QUEUE_HISTORY_LIMIT, RADIO_FETCH
from domain.models import Track
from domain.play_queue import LOOP_QUEUE, LOOP_SONG, PlayQueue
from domain.stream_cache import StreamInfo
from services.catalog_service import CatalogService
from services.notifier import Notifier
from services.stream_service import StreamService

log = logging.getLogger(__name__)


class AudioBackend(Protocol):
    position_changed: Signal
    time_changed: Signal
    time_ms_changed: Signal
    finished: Signal
    failed: Signal

    @property
    def is_playing(self) -> bool: ...
    @property
    def has_media(self) -> bool: ...
    def play_url(self, url: str) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...
    def seek(self, fraction: float) -> None: ...
    def set_volume(self, volume: int) -> None: ...


# reproduccion cola radio
class PlaybackService(QObject):
    track_loading = Signal(dict)
    track_started = Signal(dict)
    playing_changed = Signal(bool)
    stopped = Signal()

    progress = Signal(float)
    time_changed = Signal(int, int)
    time_ms = Signal(int)

    def __init__(self, queue: PlayQueue, streams: StreamService, audio: AudioBackend,
                 catalog: CatalogService, notifier: Notifier, parent: QObject | None = None):
        super().__init__(parent)
        self._queue = queue
        self._streams = streams
        self._audio = audio
        self._catalog = catalog
        self._notifier = notifier

        self._pending: Track | None = None
        self._current_video: str | None = None
        self._retry_video: str | None = None
        self._failures = 0
        self._extending = False
        self._radio_pending = False
        self._wait_for_extension = False

        audio.position_changed.connect(self.progress)
        audio.time_changed.connect(self.time_changed)
        audio.time_ms_changed.connect(self.time_ms)
        audio.finished.connect(self._on_audio_finished)
        audio.failed.connect(self._on_audio_failed)
        streams.resolved.connect(self._on_stream_resolved)
        streams.failed.connect(self._on_stream_failed)

    @property
    def queue(self) -> PlayQueue:
        return self._queue

    @property
    def is_loading(self) -> bool:
        return self._pending is not None

    @property
    def is_playing(self) -> bool:
        return self._audio.is_playing

    # reproducir detener anterior
    def play_track(self, song: Track | None) -> None:
        video_id = song.get("videoId") if song else None
        if not song or not video_id:
            self._notifier.error("Esta canción no está disponible.")
            return
        if video_id != self._retry_video:
            self._retry_video = None
        self._audio.stop()
        self._current_video = None
        self._pending = song
        self._wait_for_extension = False
        self.track_loading.emit(song)
        self._streams.request(video_id)

    def play_collection(self, songs: list[Track], start: int = 0) -> None:
        songs = [s for s in songs if s.get("videoId")]
        if not songs:
            return
        self._queue.replace(songs, start)
        self.play_track(self._queue.current)

    def play_queue_index(self, index: int) -> None:
        song = self._queue.jump_to(index)
        if song:
            self.play_track(song)

    # radio recomendaciones
    def start_radio(self, seed: Track) -> None:
        video_id = seed.get("videoId")
        if not video_id:
            return
        self._radio_pending = True
        self.play_track(self._queue.start_radio(seed))
        self._catalog.recommendations(
            video_id, RADIO_FETCH,
            lambda recs: self._on_radio_ready(video_id, recs),
            self._on_radio_failed,
            key="radio",
        )

    def _on_radio_failed(self, exc: Exception) -> None:
        self._radio_pending = False
        log.warning("Radio recommendations failed: %s", exc)
        self._maybe_extend()

    def _on_radio_ready(self, seed_video_id: str, recommendations: list[Track]) -> None:
        self._radio_pending = False
        if self._queue.radio_seed != seed_video_id:
            return
        self._queue.add_radio_tail(seed_video_id, recommendations)
        self._prefetch_upcoming()

    def toggle_pause(self) -> None:
        if self._pending is not None:
            return
        if self._audio.has_media:
            if self._audio.is_playing:
                self._audio.pause()
                self.playing_changed.emit(False)
            else:
                self._audio.resume()
                self.playing_changed.emit(True)
            return
        self.play_track(self._queue.current)

    def next(self) -> None:
        self._maybe_extend()
        song = self._queue.next()
        if song:
            self.play_track(song)
        else:
            self._wait_for_extension = self._extending

    def previous(self) -> None:
        song = self._queue.previous()
        if song:
            self.play_track(song)

    def seek(self, fraction: float) -> None:
        self._audio.seek(fraction)

    def set_volume(self, volume: int) -> None:
        self._audio.set_volume(volume)

    def enqueue_next(self, song: Track) -> None:
        if not song.get("videoId"):
            return
        if self._queue.insert_next(song):
            self.play_track(song)
        else:
            self._streams.prefetch([song["videoId"]])

    def enqueue_last(self, song: Track) -> None:
        if not song.get("videoId"):
            return
        if self._queue.append(song):
            self.play_track(song)
        else:
            self._streams.prefetch([song["videoId"]])

    def enqueue_next_many(self, songs: list[Track]) -> None:
        songs = [s for s in songs if s.get("videoId")]
        if not songs:
            return
        if self._queue.insert_next_many(songs):
            self.play_track(self._queue.current)
        else:
            self._streams.prefetch([songs[0]["videoId"]])

    def enqueue_last_many(self, songs: list[Track]) -> None:
        songs = [s for s in songs if s.get("videoId")]
        if not songs:
            return
        if self._queue.append_many(songs):
            self.play_track(self._queue.current)
        else:
            self._prefetch_upcoming()

    def shuffle(self) -> None:
        self._queue.shuffle_upcoming()
        self._prefetch_upcoming()

    # prefetch hover
    def preload(self, song: Track) -> None:
        if song.get("videoId"):
            self._streams.prefetch([song["videoId"]])

    def remove_from_queue(self, index: int) -> None:
        self._queue.remove_at(index)

    def move_in_queue(self, source: int, destination: int) -> None:
        self._queue.move(source, destination)

    def clear_queue(self) -> None:
        self._queue.clear_except_current()

    def toggle_loop(self) -> int:
        return self._queue.toggle_loop()

    def _on_stream_resolved(self, video_id: str, info: StreamInfo) -> None:
        song = self._pending
        if song is None or song.get("videoId") != video_id:
            return
        self._pending = None
        self._failures = 0
        try:
            self._audio.play_url(info.url)
        except Exception:
            log.exception("Audio backend failed to start playback")
            self.playing_changed.emit(False)
            self._notifier.error("No se pudo iniciar el reproductor de audio. ¿Está VLC instalado?")
            return
        self._current_video = video_id
        self.track_started.emit(song)
        self.playing_changed.emit(True)
        self._prefetch_upcoming()
        self._maybe_extend()

    def _on_stream_failed(self, video_id: str, message: str) -> None:
        song = self._pending
        if song is None or song.get("videoId") != video_id:
            return
        self._pending = None
        self.playing_changed.emit(False)
        self._notifier.error(f"No se pudo reproducir «{song.get('title', video_id)}»: {message}")
        self._skip_after_failure()

    # reintento fallos
    def _on_audio_failed(self) -> None:
        video_id, self._current_video = self._current_video, None
        song = self._queue.current
        if video_id is None or not song or song.get("videoId") != video_id:
            return
        if video_id != self._retry_video:
            self._retry_video = video_id
            self._streams.invalidate(video_id)
            self.play_track(song)
            return
        self._retry_video = None
        self.playing_changed.emit(False)
        self._notifier.error(f"Error de audio en «{song.get('title', video_id)}».")
        self._skip_after_failure()

    def _on_audio_finished(self) -> None:
        self._current_video = None
        self._retry_video = None
        if self._queue.loop_mode == LOOP_SONG and self._queue.current:
            self.play_track(self._queue.current)
            return
        self._maybe_extend()
        song = self._queue.next()
        if song:
            self.play_track(song)
            return
        self.playing_changed.emit(False)
        self._wait_for_extension = self._extending
        self.stopped.emit()

    def _skip_after_failure(self) -> None:
        self._failures += 1
        if self._failures >= MAX_CONSECUTIVE_PLAY_FAILURES:
            self._notifier.warning("Se detuvo la reproducción tras varios errores seguidos.")
            self._failures = 0
            return
        song = self._queue.next()
        if song:
            self.play_track(song)

    def _prefetch_upcoming(self) -> None:
        ids = [s["videoId"] for s in self._queue.upcoming(PREFETCH_AHEAD) if s.get("videoId")]
        self._streams.prefetch(ids)

    # extender cola
    def _maybe_extend(self) -> None:
        queue = self._queue
        if (self._extending or self._radio_pending or queue.loop_mode == LOOP_QUEUE
                or queue.remaining_after_current() > 1):
            return
        seed = queue.last
        if not seed or not seed.get("videoId"):
            return
        self._extending = True
        self._catalog.recommendations(
            seed["videoId"], EXTEND_BATCH + 4,
            self._on_extension_ready, self._on_extension_failed, key="extend",
        )

    def _on_extension_ready(self, recommendations: list[Track]) -> None:
        self._extending = False
        queued = self._queue.video_ids()
        fresh = [r for r in recommendations if r.get("videoId") not in queued][:EXTEND_BATCH]
        self._queue.extend_unique(fresh)
        self._queue.trim_played(QUEUE_HISTORY_LIMIT)
        self._prefetch_upcoming()
        if self._wait_for_extension:
            self._wait_for_extension = False
            song = self._queue.next()
            if song:
                self.play_track(song)

    def _on_extension_failed(self, exc: Exception) -> None:
        self._extending = False
        self._wait_for_extension = False
        log.warning("Could not extend the queue: %s", exc)
