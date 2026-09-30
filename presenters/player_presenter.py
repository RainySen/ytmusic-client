import time
from typing import Callable

from domain.models import artist_names, primary_artist, thumbnail_url
from services.library_service import LibraryService
from services.navigation import Navigator
from services.notifier import Notifier
from services.playback_service import PlaybackService
from services.settings_service import SettingsService
from ui import imaging
from ui.main_window import MainWindow

COVER_REQUEST_PX = 1000
LIKED = "LIKE"
SEEK_GRACE_S = 0.7


def album_of(song: dict) -> tuple[str, str]:
    album = song.get("album")
    if isinstance(album, dict):
        return album.get("name") or "", album.get("id") or song.get("albumId") or ""
    return album or "", song.get("albumId") or ""


def artist_id_of(song: dict) -> str:
    for artist in song.get("artists") or []:
        if isinstance(artist, dict) and artist.get("id"):
            return artist["id"]
    return ""


class PlayerPresenter:
    def __init__(self, window: MainWindow, playback: PlaybackService, navigator: Navigator | None = None,
                 library: LibraryService | None = None, notifier: Notifier | None = None,
                 clock: Callable[[], float] = time.monotonic, settings: SettingsService | None = None):
        self._window = window
        self._playback = playback
        self._queue = playback.queue
        self._navigator = navigator
        self._library = library
        self._notifier = notifier
        self._clock = clock
        self._settings = settings
        self._seek_until = 0.0
        self._cover_for: str | None = None
        self._song: dict | None = None
        self._liked = False

        window.play_pause_clicked.connect(playback.toggle_pause)
        window.next_clicked.connect(playback.next)
        window.previous_clicked.connect(playback.previous)
        window.seek_requested.connect(self._on_seek)
        window.volume_changed.connect(playback.set_volume)
        window.loop_clicked.connect(playback.toggle_loop)
        window.shuffle_clicked.connect(playback.shuffle)
        window.queue_clear_confirmed.connect(playback.clear_queue)
        window.now_artist_clicked.connect(self._open_artist)
        window.now_album_clicked.connect(self._open_album)
        window.like_clicked.connect(self._toggle_like)

        side = window.side_panel
        side.queue_item_activated.connect(playback.play_queue_index)
        side.queue_item_removed.connect(playback.remove_from_queue)
        side.queue_item_moved.connect(playback.move_in_queue)
        if settings is not None:
            side.set_auto_queue(settings.settings.auto_queue)
            side.auto_queue_toggled.connect(lambda enabled: settings.update(auto_queue=enabled))
            settings.changed.connect(lambda current: side.set_auto_queue(current.auto_queue))

        playback.track_loading.connect(self._on_loading)
        playback.track_started.connect(self._on_started)
        playback.playing_changed.connect(window.set_playing)
        playback.progress.connect(self._on_progress)
        playback.time_changed.connect(self._on_time)
        self._queue.changed.connect(self._refresh_queue)
        self._queue.loop_mode_changed.connect(window.set_loop_mode)

    def start(self) -> None:
        window = self._window
        window.set_loop_mode(self._queue.loop_mode)
        window.set_playing(False)
        self._playback.set_volume(window.volume)
        self._refresh_queue()
        current = self._queue.current
        if current:
            self._show(current, current.get("title", ""))
            self._load_cover(current)

    # ignore stale progress right after a seek
    def _on_seek(self, fraction: float) -> None:
        self._seek_until = self._clock() + SEEK_GRACE_S
        self._playback.seek(fraction)

    def _on_progress(self, fraction: float) -> None:
        if self._clock() >= self._seek_until:
            self._window.set_progress(fraction)

    def _on_time(self, current: int, total: int) -> None:
        if self._clock() >= self._seek_until:
            self._window.set_time(current, total)

    def _show(self, song: dict, title: str) -> None:
        self._song = song
        self._window.player_panel.song = song
        album, album_id = album_of(song)
        self._window.set_now_playing(title, artist_names(song, limit=2) or primary_artist(song), album,
                                     bool(self._navigator and artist_id_of(song)),
                                     bool(self._navigator and album and album_id))

    def _on_loading(self, song: dict) -> None:
        window = self._window
        self._show(song, f"Cargando: {song.get('title', '')}")
        window.reset_progress()
        window.set_playing(True)
        self._load_cover(song)
        self._load_like(song)

    def _on_started(self, song: dict) -> None:
        self._show(song, song.get("title", ""))

    def _open_artist(self) -> None:
        artist_id = artist_id_of(self._song or {})
        if self._navigator and artist_id:
            self._navigator.artist_requested.emit(artist_id)

    def _open_album(self) -> None:
        _name, album_id = album_of(self._song or {})
        if self._navigator and album_id:
            self._navigator.album_requested.emit(album_id)

    def _load_like(self, song: dict) -> None:
        self._liked = song.get("likeStatus") == LIKED
        self._window.set_liked(self._liked)
        video_id = song.get("videoId")
        if "likeStatus" in song or not video_id or not self._library or not self._window.logged_in:
            return

        def apply(status) -> None:
            if status is not None and self._song is not None and self._song.get("videoId") == video_id:
                self._liked = status == LIKED
                self._window.set_liked(self._liked)

        self._library.like_status(video_id, apply)

    def _toggle_like(self) -> None:
        video_id = (self._song or {}).get("videoId")
        if not video_id or not self._library:
            return
        wanted = not self._liked
        self._liked = wanted
        self._window.set_liked(wanted)

        def done(ok: bool) -> None:
            if ok:
                return
            if self._song is not None and self._song.get("videoId") == video_id:
                self._liked = not wanted
                self._window.set_liked(self._liked)
            if self._notifier:
                self._notifier.error("No se pudo actualizar Me gusta.")

        self._library.set_like(video_id, wanted, done)

    def _refresh_queue(self) -> None:
        self._window.side_panel.set_queue(
            self._queue.snapshot(), self._queue.current_index, self._window.thumbnails)

    def _load_cover(self, song: dict) -> None:
        video_id = song.get("videoId")
        self._cover_for = video_id
        url = thumbnail_url(song, imaging.thumb_px(COVER_REQUEST_PX))
        if not url:
            self._window.set_cover(None)
            return

        def apply(pixmap):
            if self._cover_for == video_id:
                self._window.set_cover(pixmap)

        self._window.thumbnails.request(url, apply)
