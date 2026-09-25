from services.item_opener import ItemOpener
from services.library_service import LibraryService
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow

DEFAULT_CHIP = "Playlists"


# biblioteca
class LibraryPresenter:
    def __init__(self, window: MainWindow, library: LibraryService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier):
        self._window = window
        self._browser = window.library_browser
        self._library = library
        self._playback = playback
        self._notifier = notifier
        self._active = DEFAULT_CHIP

        window.library_requested.connect(self.show)
        self._browser.chip_selected.connect(self.load)
        self._browser.playlist_activated.connect(self._open_playlist)
        self._browser.song_activated.connect(opener.open)
        self._browser.song_add_next.connect(playback.enqueue_next)
        self._browser.song_add_queue.connect(playback.enqueue_last)
        self._browser.song_hovered.connect(playback.preload)

    def show(self) -> None:
        self._window.show_view("library")
        self.load(DEFAULT_CHIP)

    def load(self, chip: str) -> None:
        self._active = chip
        self._browser.set_active_chip(chip)
        thumbnails = self._window.thumbnails
        if chip == "Artistas":
            self._browser.show_artists(self._library.artists(), thumbnails)
            return
        self._browser.show_message("Cargando…")
        if chip == "Playlists":
            self._library.playlists(lambda items: self._render(chip, self._browser.show_playlists, items))
        elif chip == "Canciones":
            self._library.songs(lambda items: self._render(chip, self._browser.show_songs, items))

    def _render(self, chip: str, show, items) -> None:
        if chip == self._active:
            show(items, self._window.thumbnails)

    def _open_playlist(self, entry: dict) -> None:
        def done(data):
            if not data:
                self._notifier.warning("La playlist está vacía o no se pudo cargar.")
                return
            self._playback.play_collection(data["tracks"])

        self._library.playlist_tracks(entry, done, lambda exc: self._notifier.error("No se pudo abrir la playlist."))
