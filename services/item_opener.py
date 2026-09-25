from __future__ import annotations

import logging
import random
from typing import Callable

from domain.models import playlist_id_of
from services.catalog_service import CatalogService
from services.navigation import Navigator
from services.notifier import Notifier
from services.playback_service import PlaybackService

log = logging.getLogger(__name__)

_ALBUM_KINDS = ("album", "single", "ep")


# abrir items navegar
class ItemOpener:
    def __init__(self, catalog: CatalogService, playback: PlaybackService, notifier: Notifier,
                 navigator: Navigator):
        self._catalog = catalog
        self._playback = playback
        self._notifier = notifier
        self._navigator = navigator

    # abrir cancion artista album
    def open(self, item: dict) -> None:
        if item.get("videoId"):
            self._playback.start_radio(item)
            return
        kind = self._kind_of(item)
        if kind == "playlist":
            self._navigator.playlist_requested.emit(playlist_id_of(item))
        elif kind == "album" and item.get("browseId"):
            self._navigator.album_requested.emit(item["browseId"])
        elif kind == "artist" and self._artist_id(item):
            self._navigator.artist_requested.emit(self._artist_id(item))
        else:
            log.info("Nothing to open for item: %s", item)
            self._notifier.warning("Este elemento no se puede reproducir todavía.")

    def shuffle_artist(self, artist_id: str, name: str = "") -> None:
        self._load(lambda done, fail: self._catalog.artist_tracks(artist_id, done, fail), name, verb="Mezclando")

    def mix_artist(self, artist_id: str) -> None:
        def done(profile: dict) -> None:
            songs = profile.get("top_songs") or []
            if not songs:
                self._notifier.warning("No hay canciones para empezar un mix.")
                return
            self._playback.start_radio(random.choice(songs))

        def failed(exc: Exception) -> None:
            log.warning("Could not start a mix for %s: %s", artist_id, exc)
            self._notifier.error("No se pudo cargar el contenido. Revisa tu conexión.")

        self._catalog.artist_profile(artist_id, done, failed)

    @staticmethod
    def artist_id(item: dict) -> str:
        return ItemOpener._artist_id(item)

    @staticmethod
    def _artist_id(item: dict) -> str:
        if item.get("browseId"):
            return item["browseId"]
        artists = item.get("artists")
        first = artists[0] if isinstance(artists, list) and artists else None
        return (first.get("id") or "") if isinstance(first, dict) else ""

    @staticmethod
    def _kind_of(item: dict) -> str:
        browse_id = item.get("browseId")
        browse_id = browse_id if isinstance(browse_id, str) else ""
        if browse_id.startswith("UC"):
            return "artist"
        if browse_id.startswith("VL"):
            return "playlist"
        kind = item.get("resultType") or item.get("type") or ""
        if kind in _ALBUM_KINDS or browse_id.startswith("MPRE"):
            return "album"
        if kind in ("artist", "playlist"):
            return kind
        return "playlist" if item.get("playlistId") else ""

    def _load(self, request: Callable, label: str, verb: str = "Abriendo") -> None:
        if label:
            self._notifier.info(f"{verb} «{label}»…")

        def done(data: dict | None) -> None:
            if not data or not data.get("tracks"):
                self._notifier.warning("No hay canciones reproducibles aquí.")
                return
            self._playback.play_collection(data["tracks"])

        def failed(exc: Exception) -> None:
            log.warning("Could not open %r: %s", label, exc)
            self._notifier.error("No se pudo cargar el contenido. Revisa tu conexión.")

        request(done, failed)
