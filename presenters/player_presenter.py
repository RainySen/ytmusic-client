from domain.models import artist_names, primary_artist, thumbnail_url
from services.playback_service import PlaybackService
from ui.main_window import MainWindow

COVER_REQUEST_PX = 1000


# player portada cola
class PlayerPresenter:
    def __init__(self, window: MainWindow, playback: PlaybackService):
        self._window = window
        self._playback = playback
        self._queue = playback.queue
        self._cover_for: str | None = None

        window.play_pause_clicked.connect(playback.toggle_pause)
        window.next_clicked.connect(playback.next)
        window.previous_clicked.connect(playback.previous)
        window.seek_requested.connect(playback.seek)
        window.volume_changed.connect(playback.set_volume)
        window.loop_clicked.connect(playback.toggle_loop)
        window.shuffle_clicked.connect(playback.shuffle)
        window.queue_clear_confirmed.connect(playback.clear_queue)

        side = window.side_panel
        side.queue_item_activated.connect(playback.play_queue_index)
        side.queue_item_removed.connect(playback.remove_from_queue)
        side.queue_item_moved.connect(playback.move_in_queue)

        playback.track_loading.connect(self._on_loading)
        playback.track_started.connect(self._on_started)
        playback.playing_changed.connect(window.set_playing)
        playback.progress.connect(window.set_progress)
        playback.time_changed.connect(window.set_time)
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
            window.set_now_playing(current.get("title", ""), primary_artist(current))
            self._load_cover(current)

    def _on_loading(self, song: dict) -> None:
        window = self._window
        window.set_now_playing(f"Cargando: {song.get('title', '')}", artist_names(song, limit=2) or primary_artist(song))
        window.reset_progress()
        window.set_playing(True)
        self._load_cover(song)

    def _on_started(self, song: dict) -> None:
        self._window.set_now_playing(song.get("title", ""), artist_names(song, limit=2) or primary_artist(song))

    def _refresh_queue(self) -> None:
        self._window.side_panel.set_queue(
            self._queue.snapshot(), self._queue.current_index, self._window.thumbnails)

    def _load_cover(self, song: dict) -> None:
        video_id = song.get("videoId")
        self._cover_for = video_id
        url = thumbnail_url(song, COVER_REQUEST_PX)
        if not url:
            self._window.set_cover(None)
            return

        def apply(pixmap):
            if self._cover_for == video_id:
                self._window.set_cover(pixmap)

        self._window.thumbnails.request(url, apply)
