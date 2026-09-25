import random

from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.navigation import Navigator
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow

HISTORY_LIMIT = 40
PROFILE_VIEWS = ("artist", "album")
COLLECTION_KINDS = ("album", "playlist")


# perfil artista album playlist
class ProfilePresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, navigator: Navigator, notifier: Notifier):
        self._window = window
        self._catalog = catalog
        self._playback = playback
        self._notifier = notifier
        self._navigator = navigator
        self._opener = opener
        self._history: list[tuple[str, str]] = []
        self._current: tuple[str, str] | None = None
        self._profile: dict | None = None
        self._collection: dict | None = None

        navigator.artist_requested.connect(lambda artist_id: self._go(("artist", artist_id)))
        navigator.album_requested.connect(lambda album_id: self._go(("album", album_id)))
        navigator.playlist_requested.connect(lambda playlist_id: self._go(("playlist", playlist_id)))
        window.view_shown.connect(self._on_view_shown)

        artist = window.artist_panel
        artist.back_requested.connect(self.back)
        artist.shuffle_requested.connect(self._shuffle_artist)
        artist.mix_requested.connect(self._start_mix)
        artist.show_all_requested.connect(self._show_all_songs)
        artist.song_chosen.connect(playback.start_radio)
        artist.song_hovered.connect(playback.preload)
        artist.add_next_clicked.connect(playback.enqueue_next)
        artist.add_queue_clicked.connect(playback.enqueue_last)
        artist.item_clicked.connect(opener.open)
        artist.item_hovered.connect(playback.preload)

        album = window.album_panel
        album.back_requested.connect(self.back)
        album.play_requested.connect(self._play_album)
        album.shuffle_requested.connect(lambda: self._play_album(shuffle=True))
        album.track_chosen.connect(self._play_album_track)
        album.track_hovered.connect(playback.preload)
        album.add_next_clicked.connect(playback.enqueue_next)
        album.add_queue_clicked.connect(playback.enqueue_last)
        album.artist_clicked.connect(lambda artist_id: navigator.artist_requested.emit(artist_id))
        album.item_clicked.connect(opener.open)

    # navegacion historial back
    def _go(self, target: tuple[str, str]) -> None:
        if target == self._current:
            self._render(target)
            return
        self._history.append(self._current or ("view", self._window.current_view))
        del self._history[:-HISTORY_LIMIT]
        self._current = target
        self._render(target)

    def back(self) -> None:
        if not self._history:
            self._window.show_view("home")
            return
        target = self._history.pop()
        if target[0] == "view":
            self._window.show_view(target[1])
            return
        self._current = target
        self._render(target)

    def _on_view_shown(self, name: str) -> None:
        if name not in PROFILE_VIEWS:
            self._history.clear()
            self._current = None

    def _render(self, target: tuple[str, str]) -> None:
        kind, ident = target
        if kind in COLLECTION_KINDS:
            self._window.show_view("album")
            self._window.album_panel.set_loading()
            fetch = self._catalog.album if kind == "album" else self._catalog.playlist_details
            fetch(ident, lambda data: self._on_collection(target, data), lambda e: self._on_failed(target, "album"))
            return
        self._window.show_view("artist")
        self._window.artist_panel.set_loading()
        self._catalog.artist_profile(ident, lambda p: self._on_profile(target, p),
                                     lambda e: self._on_failed(target, "artist"))

    def _on_profile(self, target: tuple[str, str], profile: dict) -> None:
        if target != self._current:
            return
        self._profile = profile
        if target[0] == "songs":
            self._catalog.playlist(profile["songs_browse_id"], lambda d: self._on_songs(target, profile, d),
                                   lambda e: self._on_failed(target, "artist"))
            return
        self._window.artist_panel.show_profile(profile, self._window.thumbnails)

    def _on_songs(self, target: tuple[str, str], profile: dict, data: dict | None) -> None:
        if target != self._current:
            return
        if not data or not data.get("tracks"):
            self._window.artist_panel.show_message("No hay canciones para mostrar.")
            return
        self._window.artist_panel.show_all_songs(profile["name"], data["tracks"], self._window.thumbnails)

    def _on_collection(self, target: tuple[str, str], data: dict | None) -> None:
        if target != self._current:
            return
        panel = self._window.album_panel
        if not data:
            panel.show_message("No hay canciones disponibles aquí.")
            return
        self._collection = data
        if target[0] == "album":
            panel.show_album(data, self._window.thumbnails)
        else:
            panel.show_playlist(data, self._window.thumbnails)

    def _on_failed(self, target: tuple[str, str], view: str) -> None:
        if target != self._current:
            return
        text = "No se pudo cargar. Revisa tu conexión e inténtalo de nuevo."
        panel = self._window.album_panel if view == "album" else self._window.artist_panel
        panel.show_message(text)

    def _shuffle_artist(self) -> None:
        if self._profile:
            self._opener.shuffle_artist(self._profile["id"], self._profile["name"])

    def _start_mix(self) -> None:
        if self._profile:
            self._opener.mix_artist(self._profile["id"])

    def _show_all_songs(self) -> None:
        if self._profile:
            self._go(("songs", self._profile["id"]))

    def _play_album(self, shuffle: bool = False) -> None:
        if not self._collection:
            return
        tracks = list(self._collection["tracks"])
        if shuffle:
            random.shuffle(tracks)
        self._playback.play_collection(tracks)

    def _play_album_track(self, position: int, track: dict) -> None:
        if self._collection:
            self._playback.play_collection(self._collection["tracks"], start=position)
