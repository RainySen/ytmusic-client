from services.library_service import LibraryService
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.components import dialogs
from ui.main_window import MainWindow


class PlaylistRailPresenter:
    def __init__(self, window: MainWindow, library: LibraryService, playback: PlaybackService, notifier: Notifier):
        self._window = window
        self._library = library
        self._playback = playback
        self._notifier = notifier
        self._cache: list[dict] | None = None
        rail = window.sidebar.rail

        window.sidebar_expanded.connect(self._on_toggle)
        window.library_requested.connect(self.refresh)
        rail.playlist_chosen.connect(self._open)
        rail.play_next_requested.connect(lambda playlist: self._with_tracks(playlist, self._playback.enqueue_next_many))
        rail.add_queue_requested.connect(lambda playlist: self._with_tracks(playlist, self._playback.enqueue_last_many))
        rail.pin_toggled.connect(self._toggle_pin)
        rail.delete_requested.connect(self._delete)

    # show cached rail first, refresh in background
    def _on_toggle(self, expanded: bool) -> None:
        if not expanded:
            return
        if self._cache is not None:
            self._window.sidebar.set_playlists(self._cache, self._window.thumbnails)
        else:
            self._window.sidebar.rail.set_loading()
        self.refresh()

    def refresh(self) -> None:
        def done(items: list[dict]) -> None:
            self._cache = items
            self._window.sidebar.set_playlists(items, self._window.thumbnails)

        self._library.playlists(done)

    def _open(self, playlist: dict) -> None:
        def done(data):
            if not data:
                self._notifier.warning("La playlist está vacía o no se pudo cargar.")
                return
            self._playback.play_collection(data["tracks"])

        self._library.playlist_tracks(playlist, done, lambda _exc: self._notifier.error("No se pudo abrir la playlist."))

    def _with_tracks(self, playlist: dict, apply) -> None:
        def done(data):
            tracks = (data or {}).get("tracks") or []
            if tracks:
                apply(tracks)
            else:
                self._notifier.warning("La playlist está vacía o no se pudo cargar.")

        self._library.playlist_tracks(playlist, done, lambda _exc: self._notifier.error("No se pudo abrir la playlist."))

    def _toggle_pin(self, playlist: dict) -> None:
        self._library.toggle_pin(playlist["playlistId"])
        self.refresh()

    def _delete(self, playlist: dict) -> None:
        if dialogs.confirm(self._window, "¿Eliminar playlist?", f"Se eliminará «{playlist.get('title', '')}» de este "
                           "equipo. Esto no se puede deshacer.", ok="Eliminar"):
            self._library.delete_local_playlist(playlist["playlistId"])
            self.refresh()
