from bisect import bisect_right

from domain.models import Lyrics
from services.lyrics_service import LyricsService
from services.playback_service import PlaybackService
from ui.main_window import MainWindow


# letras resaltado palabra
class LyricsPresenter:
    def __init__(self, window: MainWindow, playback: PlaybackService, lyrics: LyricsService):
        self._panel = window.side_panel
        self._lyrics = lyrics
        self._video_id: str | None = None
        self._times: list[int] = []
        self._word_synced = False
        self._active = -1

        playback.track_loading.connect(self._on_track)
        playback.time_ms.connect(self._on_time)

    def _on_track(self, song: dict) -> None:
        video_id = song.get("videoId")
        self._video_id = video_id
        self._times = []
        self._word_synced = False
        self._active = -1
        self._panel.set_lyrics_message("…")
        self._lyrics.fetch(
            song,
            lambda lyrics: self._show(video_id, lyrics),
            lambda exc: self._show(video_id, None),
        )

    def _show(self, video_id: str, lyrics: Lyrics | None) -> None:
        if video_id != self._video_id:
            return
        if lyrics is None:
            self._panel.set_lyrics_message("Letra no encontrada.")
            return
        self._panel.set_lyrics(lyrics)
        self._times = [line.time_ms for line in lyrics.lines] if lyrics.synced else []
        self._word_synced = lyrics.word_synced

    def _on_time(self, current_ms: int) -> None:
        if not self._times:
            return
        index = bisect_right(self._times, current_ms) - 1
        if index < 0:
            return
        if index != self._active:
            self._active = index
            self._panel.highlight_lyric(index)
        if self._word_synced:
            self._panel.set_lyric_progress(index, current_ms)
