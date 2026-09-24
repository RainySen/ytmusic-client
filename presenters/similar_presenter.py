from services.catalog_service import CatalogService
from services.item_opener import ItemOpener
from services.playback_service import PlaybackService
from ui.main_window import MainWindow


# similares lazy
class SimilarPresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, playback: PlaybackService,
                 opener: ItemOpener):
        self._window = window
        self._panel = window.side_panel
        self._catalog = catalog
        self._queue = playback.queue
        self._video_id: str | None = None
        self._loaded = False
        self._loading = False

        playback.track_loading.connect(self._on_track)
        panel = self._panel
        panel.similar_tab_opened.connect(self._on_tab_opened)
        panel.similar_item_chosen.connect(opener.open)
        panel.similar_add_next.connect(playback.enqueue_next)
        panel.similar_add_queue.connect(playback.enqueue_last)
        panel.similar_item_hovered.connect(playback.preload)

    def _on_track(self, song: dict) -> None:
        self._video_id = song.get("videoId")
        self._loaded = False
        self._loading = False
        self._panel.clear_similar()
        if self._panel.is_similar_tab_active():
            self._load()

    def _on_tab_opened(self) -> None:
        if self._video_id is None:
            current = self._queue.current
            self._video_id = current.get("videoId") if current else None
        if self._video_id is None:
            self._panel.set_similar_message("Reproduce una canción para ver contenido similar.")
        elif not self._loaded and not self._loading:
            self._load()

    def _load(self) -> None:
        video_id = self._video_id
        if not video_id:
            return
        self._loading = True
        self._panel.set_similar_loading()
        self._catalog.related(video_id, lambda data: self._show(video_id, data),
                              lambda exc: self._failed(video_id))

    def _show(self, video_id: str, data: dict) -> None:
        if video_id != self._video_id:
            return
        self._loading = False
        self._loaded = True
        self._panel.set_similar(data, self._window.thumbnails)

    def _failed(self, video_id: str) -> None:
        if video_id != self._video_id:
            return
        self._loading = False
        self._panel.set_similar_message("No se pudo cargar. Vuelve a abrir la pestaña para reintentar.")
