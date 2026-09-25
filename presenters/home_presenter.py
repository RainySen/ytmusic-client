from ui.main_window import MainWindow
from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.notifier import Notifier
from services.playback_service import PlaybackService

ALL_MOODS = "Todos"


# home moods
class HomePresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier):
        self._window = window
        self._panel = window.home_panel
        self._catalog = catalog
        self._notifier = notifier
        self._mood = ALL_MOODS
        self._has_content = False

        panel = self._panel
        panel.item_clicked.connect(opener.open)
        panel.add_next_clicked.connect(playback.enqueue_next)
        panel.add_queue_clicked.connect(playback.enqueue_last)
        panel.play_all_requested.connect(playback.play_collection)
        panel.item_hovered.connect(playback.preload)
        panel.mood_selected.connect(self.select_mood)
        window.home_requested.connect(self.show)

    def start(self) -> None:
        stored = self._catalog.stored_home()
        if stored:
            self._render(stored, reset_scroll=True)
        else:
            self._panel.set_loading()
        self._window.show_view("home")
        self.refresh(force=True)

    def show(self) -> None:
        self._window.show_view("home")
        if not self._has_content:
            self.refresh(force=False)

    def refresh(self, force: bool = True) -> None:
        if self._mood == ALL_MOODS:
            self._catalog.load_home(self._on_feed, self._on_error, force=force)
        else:
            self.select_mood(self._mood)

    def select_mood(self, mood: str) -> None:
        self._mood = mood
        if mood == ALL_MOODS:
            self._catalog.load_home(self._on_feed, self._on_error, force=False)
            return
        self._panel.set_loading()
        self._has_content = False
        self._catalog.load_mood(mood, lambda sections: self._on_mood(mood, sections))

    def _on_feed(self, sections) -> None:
        if self._mood != ALL_MOODS:
            return
        self._render(sections, reset_scroll=not self._has_content)

    def _on_mood(self, mood: str, sections) -> None:
        if self._mood != mood:
            return
        if not sections:
            self._panel.show_message(f"No se encontró contenido para «{mood}».")
            return
        self._render(sections, reset_scroll=True)

    def _render(self, sections, reset_scroll: bool) -> None:
        self._has_content = True
        self._panel.set_sections(sections, self._window.thumbnails, reset_scroll=reset_scroll)

    def _on_error(self, exc: Exception) -> None:
        if self._has_content:
            self._notifier.warning("No se pudo actualizar el inicio.")
        else:
            self._panel.show_message("No se pudo cargar el inicio. Revisa tu conexión e inténtalo de nuevo.")
