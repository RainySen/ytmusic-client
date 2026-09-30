from PySide6.QtCore import QTimer

from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.notifier import Notifier
from services.playback_service import PlaybackService
from services.search_history_service import SearchHistoryService
from ui.main_window import MainWindow

LOADING_DELAY_MS = 200


class SearchPresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier, history: SearchHistoryService | None = None):
        self._window = window
        self._panel = window.search_panel
        self._catalog = catalog
        self._notifier = notifier
        self._history = history
        self._pending_query = ""
        self._loading_timer = QTimer(window)
        self._loading_timer.setSingleShot(True)
        self._loading_timer.setInterval(LOADING_DELAY_MS)
        self._loading_timer.timeout.connect(self._show_loading)

        window.search_submitted.connect(self.search)
        if history is not None:
            window.history_removed.connect(history.remove)
            window.history_cleared.connect(history.clear)
            history.changed.connect(window.set_search_history)
            window.set_search_history(history.items)
        self._panel.item_clicked.connect(opener.open)
        self._panel.add_next_clicked.connect(playback.enqueue_next)
        self._panel.add_queue_clicked.connect(playback.enqueue_last)
        self._panel.item_hovered.connect(playback.preload)
        self._panel.artist_shuffle_requested.connect(
            lambda artist: opener.shuffle_artist(opener.artist_id(artist), artist.get("artist") or artist.get("title", "")))
        self._panel.artist_mix_requested.connect(lambda artist: opener.mix_artist(opener.artist_id(artist)))

    # no loading flash for cached or fast results
    def search(self, query: str) -> None:
        if self._history is not None:
            self._history.add(query)
        self._window.show_view("search")
        self._pending_query = query
        self._loading_timer.start()
        self._catalog.search(query, self._show_results, self._on_error)

    def _show_loading(self) -> None:
        self._panel.show_message(f"Buscando «{self._pending_query}»…")

    def _show_results(self, grouped) -> None:
        self._loading_timer.stop()
        self._panel.show_results(grouped, self._window.thumbnails)

    def _on_error(self, exc: Exception) -> None:
        self._loading_timer.stop()
        self._panel.show_message("No se pudo completar la búsqueda. Revisa tu conexión.")
        self._notifier.error("Error de búsqueda.")
