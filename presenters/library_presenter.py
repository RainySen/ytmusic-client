from domain.models import LOCAL_SOURCES
from presenters.paging import Pager
from services.item_opener import ItemOpener
from services.library_service import LIKED_PAGE, PAGE_CAP, PAGE_STEP, SONGS_PAGE, LibraryService
from services.navigation import Navigator
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow

DEFAULT_CHIP = "Playlists"
_PAGED = {"Canciones": (SONGS_PAGE, "songs", "show_songs"), "Me gusta": (LIKED_PAGE, "liked_songs", "show_liked")}


class LibraryPresenter:
    def __init__(self, window: MainWindow, library: LibraryService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier, navigator: Navigator):
        self._window = window
        self._browser = window.library_browser
        self._library = library
        self._playback = playback
        self._notifier = notifier
        self._navigator = navigator
        self._active = DEFAULT_CHIP
        self._pager = Pager(self._fetch_page, self._deliver_page, PAGE_STEP, PAGE_CAP)

        window.library_requested.connect(self.show)
        self._browser.chip_selected.connect(self.load)
        self._browser.load_more_requested.connect(self._pager.more)
        self._browser.playlist_activated.connect(self._open_playlist)
        self._browser.song_activated.connect(opener.open)
        self._browser.song_add_next.connect(playback.enqueue_next)
        self._browser.song_add_queue.connect(playback.enqueue_last)
        self._browser.song_hovered.connect(playback.preload)

    def show(self) -> None:
        self._window.show_view("library")
        self.load(DEFAULT_CHIP)

    def reload(self) -> None:
        self.load(self._active)

    def load(self, chip: str) -> None:
        self._active = chip
        self._pager.stop()
        self._browser.set_active_chip(chip)
        self._browser.show_message("Cargando…")
        if chip == "Playlists":
            self._library.playlists(lambda items: self._render(chip, self._browser.show_playlists, items))
        elif chip == "Artistas":
            self._library.library_artists(lambda items: self._render(chip, self._browser.show_artists, items))
        elif chip in _PAGED:
            self._pager.start(_PAGED[chip][0])

    def _fetch_page(self, limit: int, done) -> None:
        getattr(self._library, _PAGED[self._active][1])(lambda items: done(items), limit)

    def _deliver_page(self, items, has_more: bool, append: bool) -> None:
        if self._active not in _PAGED:
            return
        show = getattr(self._browser, _PAGED[self._active][2])
        show(items, self._window.thumbnails, has_more=has_more, append=append)

    def _render(self, chip: str, show, items) -> None:
        if chip == self._active:
            show(items, self._window.thumbnails)

    # local playlists open directly; ytmusic ones go to the paged page
    def _open_playlist(self, entry: dict) -> None:
        if entry.get("source", "ytmusic") not in LOCAL_SOURCES:
            self._navigator.playlist_requested.emit(entry["playlistId"])
            return

        def done(data):
            if not data:
                self._notifier.warning("La playlist está vacía o no se pudo cargar.")
                return
            self._playback.play_collection(data["tracks"])

        self._library.playlist_tracks(entry, done, lambda exc: self._notifier.error("No se pudo abrir la playlist."))
