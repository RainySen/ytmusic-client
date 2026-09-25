from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow

DETAIL_CHUNK = 15
DETAIL_MAX_SECTIONS = 4


# explorar
class ExplorePresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier):
        self._window = window
        self._panel = window.explore_panel
        self._catalog = catalog
        self._opener = opener
        self._notifier = notifier
        self._sections: list = []
        self._detail: str | None = None

        window.explore_requested.connect(self.show)
        panel = self._panel
        panel.item_clicked.connect(self._on_item)
        panel.add_next_clicked.connect(playback.enqueue_next)
        panel.add_queue_clicked.connect(playback.enqueue_last)
        panel.play_all_requested.connect(playback.play_collection)
        panel.item_hovered.connect(playback.preload)
        panel.jump_requested.connect(panel.reveal)
        panel.back_requested.connect(self.show_shelves)

    def show(self) -> None:
        self._window.show_view("explore")
        if self._sections and self._detail is None:
            return
        self.show_shelves()

    def show_shelves(self) -> None:
        self._detail = None
        self._panel.set_detail_mode(False)
        if self._sections:
            self._render_shelves()
            return
        self._panel.set_loading()
        self._catalog.load_explore(self._on_shelves, self._on_error)

    def _on_shelves(self, sections) -> None:
        self._sections = sections
        if self._detail is None:
            self._render_shelves()

    def _render_shelves(self) -> None:
        self._panel.set_sections(self._sections, self._window.thumbnails)

    def _on_item(self, item: dict) -> None:
        if item.get("type") == "mood":
            self._open_mood(item)
        else:
            self._opener.open(item)

    def _open_mood(self, mood: dict) -> None:
        title = mood.get("title", "")
        self._detail = title
        self._panel.set_detail_mode(True)
        self._panel.set_loading()
        self._catalog.mood_playlists(mood["params"], lambda items: self._on_mood(title, items), self._on_error)

    def _on_mood(self, title: str, playlists: list) -> None:
        if self._detail != title:
            return
        chunks = [playlists[i:i + DETAIL_CHUNK] for i in range(0, len(playlists), DETAIL_CHUNK)]
        sections = [(title if n == 0 else f"Más de {title}", chunk)
                    for n, chunk in enumerate(chunks[:DETAIL_MAX_SECTIONS])]
        if not sections:
            self._panel.show_message(f"No se encontraron playlists para «{title}».")
            return
        self._panel.set_sections(sections, self._window.thumbnails)

    def _on_error(self, exc: Exception) -> None:
        if self._sections and self._detail is None:
            self._notifier.warning("No se pudo actualizar Explorar.")
        else:
            self._panel.show_message("No se pudo cargar. Revisa tu conexión e inténtalo de nuevo.")
