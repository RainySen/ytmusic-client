from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow


# busqueda
class SearchPresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier):
        self._window = window
        self._panel = window.search_panel
        self._catalog = catalog
        self._notifier = notifier

        window.search_submitted.connect(self.search)
        self._panel.item_clicked.connect(opener.open)
        self._panel.add_next_clicked.connect(playback.enqueue_next)
        self._panel.add_queue_clicked.connect(playback.enqueue_last)
        self._panel.item_hovered.connect(playback.preload)
        self._panel.artist_shuffle_requested.connect(
            lambda artist: opener.shuffle_artist(opener.artist_id(artist), artist.get("artist") or artist.get("title", "")))
        self._panel.artist_mix_requested.connect(lambda artist: opener.mix_artist(opener.artist_id(artist)))

    def search(self, query: str) -> None:
        self._window.show_view("search")
        self._panel.show_message(f"Buscando «{query}»…")
        self._catalog.search(query, self._show_results, self._on_error)

    def _show_results(self, grouped) -> None:
        self._panel.show_results(grouped, self._window.thumbnails)

    def _on_error(self, exc: Exception) -> None:
        self._panel.show_message("No se pudo completar la búsqueda. Revisa tu conexión.")
        self._notifier.error("Error de búsqueda.")
