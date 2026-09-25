from __future__ import annotations

import logging
import random
from typing import Callable

from domain.models import Track, playlist_id_of
from services.catalog_service import CatalogService
from services.notifier import Notifier
from services.playback_service import PlaybackService

log = logging.getLogger(__name__)

WEB_ROOT = "https://music.youtube.com"


# acciones playlist album
class CollectionActions:
    def __init__(self, catalog: CatalogService, playback: PlaybackService, notifier: Notifier):
        self._catalog = catalog
        self._playback = playback
        self._notifier = notifier

    @staticmethod
    def is_album(item: dict) -> bool:
        return str(item.get("browseId", "")).startswith("MPRE")

    def tracks_of(self, item: dict, done: Callable[[list[Track]], None]) -> None:
        def ready(data: dict | None) -> None:
            tracks = (data or {}).get("tracks") or []
            if tracks:
                done(tracks)
            else:
                self._notifier.warning("No hay canciones reproducibles aquí.")

        def failed(exc: Exception) -> None:
            log.warning("Could not load %r: %s", item.get("title"), exc)
            self._notifier.error("No se pudo cargar el contenido. Revisa tu conexión.")

        if self.is_album(item):
            self._catalog.album(item["browseId"], ready, failed)
        else:
            self._catalog.playlist_details(playlist_id_of(item), ready, failed)

    def perform(self, action: str, item: dict) -> None:
        handler = {
            "play": lambda tracks: self._playback.play_collection(tracks),
            "shuffle": lambda tracks: self._playback.play_collection(random.sample(tracks, len(tracks))),
            "mix": lambda tracks: self._playback.start_radio(random.choice(tracks)),
            "next": self._playback.enqueue_next_many,
            "queue": self._playback.enqueue_last_many,
        }.get(action)
        if handler is None:
            log.warning("Unknown collection action %r", action)
            return
        if action in ("play", "shuffle", "mix") and item.get("title"):
            self._notifier.info(f"{'Mezclando' if action == 'shuffle' else 'Abriendo'} «{item['title']}»…")
        self.tracks_of(item, handler)

    def share_url(self, item: dict) -> str:
        if self.is_album(item):
            return f"{WEB_ROOT}/browse/{item['browseId']}"
        return f"{WEB_ROOT}/playlist?list={playlist_id_of(item)}"
