import random

from ui.main_window import MainWindow
from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.notifier import Notifier
from services.playback_service import PlaybackService

ALL_MOODS = "Todos"
SEED_COUNT = 2
SWAP_FRACTION = 0.4
MIN_SHELF_SONGS = 4


# home moods
class HomePresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener, notifier: Notifier, rng: random.Random | None = None):
        self._rng = rng or random.Random()
        self._sections: list = []
        self._swaps: dict[str, dict[str, dict]] = {}
        self._pool_ready: list | None = None
        self._pool_pending = False
        self._window = window
        self._panel = window.home_panel
        self._catalog = catalog
        self._notifier = notifier
        self._mood = ALL_MOODS
        self._has_content = False
        self._released = False
        self._scroll_top = False

        panel = self._panel
        panel.item_clicked.connect(opener.open)
        panel.add_next_clicked.connect(playback.enqueue_next)
        panel.add_queue_clicked.connect(playback.enqueue_last)
        panel.play_all_requested.connect(playback.play_collection)
        panel.item_hovered.connect(playback.preload)
        panel.mood_selected.connect(self.select_mood)
        window.home_requested.connect(self.reload)

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
        if self._released:
            self.restore()
        elif not self._has_content:
            self.refresh(force=False)

    # boton inicio recarga el feed
    def reload(self) -> None:
        self._window.show_view("home")
        self._released = False
        self._mood = ALL_MOODS
        self._panel.reset_mood()
        self._swaps = {}
        if self._sections:
            self._render(self._sections, reset_scroll=True)
            ready, self._pool_ready = self._pool_ready, None
            if ready:
                self._on_pool(ready)
                self._prefetch_pool()
            else:
                self._catalog.discovery_pool(self._seed_ids(), self._on_pool)
        else:
            self._scroll_top = True
            self._has_content = False
            self._panel.set_loading()
        self.refresh(force=True)

    # liberar ram segundo plano
    def release(self) -> None:
        self._panel.feed.clear()
        self._has_content = False
        self._released = True

    def restore(self) -> None:
        self._released = False
        stored = self._catalog.stored_home()
        if stored and self._mood == ALL_MOODS:
            self._render(stored, reset_scroll=True)
        else:
            self._panel.set_loading()
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
        reset_scroll = reset_scroll or self._scroll_top
        self._scroll_top = False
        sections = self._with_swaps(sections)
        self._sections = sections
        self._panel.set_sections(sections, self._window.thumbnails, reset_scroll=reset_scroll)
        if self._pool_ready is None:
            self._prefetch_pool()

    # recargar cambia canciones por recomendaciones nuevas
    def _seed_ids(self) -> list[str]:
        for _title, items in self._sections:
            songs = [i["videoId"] for i in items if i.get("type") == "song" and i.get("videoId")]
            if songs:
                return self._rng.sample(songs, min(SEED_COUNT, len(songs)))
        return []

    # recomendaciones listas para el proximo clic
    def _prefetch_pool(self) -> None:
        if self._pool_pending or self._mood != ALL_MOODS:
            return
        seeds = self._seed_ids()
        if not seeds:
            return
        self._pool_pending = True
        self._catalog.discovery_pool(seeds, self._store_pool)

    def _store_pool(self, pool) -> None:
        self._pool_pending = False
        self._pool_ready = list(pool) or None

    def _on_pool(self, pool) -> None:
        if self._mood != ALL_MOODS or not self._sections or not pool:
            return
        pool = list(pool)
        self._rng.shuffle(pool)
        for title, items in self._sections:
            songs = [i for i in items if i.get("type") == "song" and i.get("videoId")]
            if len(songs) < MIN_SHELF_SONGS:
                continue
            present = {i.get("videoId") for i in items}
            fresh = [c for c in pool if c["videoId"] not in present]
            count = min(len(fresh), max(1, round(len(songs) * SWAP_FRACTION)))
            for old, new in zip(self._rng.sample(songs, count), fresh):
                self._swaps.setdefault(title, {})[old["videoId"]] = new
        self._render(self._sections, reset_scroll=False)

    def _with_swaps(self, sections):
        if not self._swaps:
            return sections
        result = []
        for title, items in sections:
            replacements = self._swaps.get(title)
            if not replacements:
                result.append((title, items))
                continue
            present = {i.get("videoId") for i in items}
            swapped = []
            for item in items:
                new = replacements.get(item.get("videoId"))
                if new is not None and new["videoId"] not in present:
                    present.add(new["videoId"])
                    swapped.append(new)
                else:
                    swapped.append(item)
            result.append((title, swapped))
        return result

    def _on_error(self, exc: Exception) -> None:
        if self._has_content:
            self._notifier.warning("No se pudo actualizar el inicio.")
        else:
            self._panel.show_message("No se pudo cargar el inicio. Revisa tu conexión e inténtalo de nuevo.")
