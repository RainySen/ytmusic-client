from PySide6.QtCore import QTimer

from core.i18n import t
from services.catalog_service import CatalogService
from services.library_service import LibraryService
from services.item_opener import ItemOpener
from services.notifier import Notifier
from services.playback_service import PlaybackService
from services.search_history_service import SearchHistoryService
from ui.components.search_panel import SCOPE_LIBRARY, SCOPE_YTMUSIC
from ui.main_window import MainWindow

LOADING_DELAY_MS = 200
SUGGEST_DELAY_MS = 250


class SearchPresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier, history: SearchHistoryService | None = None,
                 library: LibraryService | None = None):
        self._window = window
        self._panel = window.search_panel
        self._catalog = catalog
        self._notifier = notifier
        self._history = history
        self._pending_query = ""
        self._library = library
        self._scope = SCOPE_YTMUSIC
        self._loading_timer = QTimer(window)
        self._loading_timer.setSingleShot(True)
        self._loading_timer.setInterval(LOADING_DELAY_MS)
        self._loading_timer.timeout.connect(self._show_loading)
        self._typed = ""
        self._suggest_timer = QTimer(window)
        self._suggest_timer.setSingleShot(True)
        self._suggest_timer.setInterval(SUGGEST_DELAY_MS)
        self._suggest_timer.timeout.connect(self._suggest)

        window.search_submitted.connect(self.search)
        window.search_typed.connect(self._on_typed)
        if history is not None:
            window.history_removed.connect(history.remove)
            window.history_cleared.connect(history.clear)
            history.changed.connect(window.set_search_history)
            window.set_search_history(history.items)
        self._panel.scope_changed.connect(self._on_scope)
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
        self._suggest_timer.stop()
        self._window.show_view("search")
        self._pending_query = query
        self._run(query)

    # debounce: one request after the user stops typing
    def _on_typed(self, text: str) -> None:
        self._typed = text.strip()
        if self._typed:
            self._suggest_timer.start()
        else:
            self._suggest_timer.stop()

    def _suggest(self) -> None:
        query = self._typed
        self._catalog.suggestions(query, lambda items: self._window.set_search_suggestions(query, items))

    def _on_scope(self, scope: str) -> None:
        self._scope = scope
        if self._pending_query:
            self._run(self._pending_query)

    def _run(self, query: str) -> None:
        self._loading_timer.start()
        if self._scope == SCOPE_LIBRARY and self._library is not None:
            self._library.search(query, lambda sections: self._show_library(query, sections), self._on_error)
        else:
            self._catalog.search(query, lambda grouped: self._show_web(query, grouped), self._on_error)

    def _show_web(self, query: str, grouped) -> None:
        if query == self._pending_query and (self._scope == SCOPE_YTMUSIC or self._library is None):
            self._show_results(grouped)

    def _show_library(self, query: str, sections) -> None:
        if query != self._pending_query or self._scope != SCOPE_LIBRARY:
            return
        self._loading_timer.stop()
        self._panel.show_library_results(sections, self._window.thumbnails)

    def _show_loading(self) -> None:
        self._panel.show_message(t("search.loading", query=self._pending_query))

    def _show_results(self, grouped) -> None:
        self._loading_timer.stop()
        self._panel.show_results(grouped, self._window.thumbnails)

    def _on_error(self, exc: Exception) -> None:
        self._loading_timer.stop()
        self._panel.show_message(t("search.failed"))
        self._notifier.error(t("search.error"))
