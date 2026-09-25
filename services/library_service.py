from __future__ import annotations

import logging
import re
from typing import Any, Callable

from domain.models import LOCAL_SOURCES, Track, normalize_tracks
from infra.concurrency import TaskRunner
from infra.playlist_repository import LocalPlaylistRepository
from infra.recent_playlists import RecentPlaylists
from infra.ytmusic_gateway import YTMusicGateway
from services.catalog_service import CatalogService

log = logging.getLogger(__name__)

RECENT_SHOWN = 4

Done = Callable[[Any], None]
Fail = Callable[[Exception], None]

_PLAYLIST_URL_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")


def extract_playlist_id(url: str) -> str | None:
    match = _PLAYLIST_URL_RE.search(url or "")
    return match.group(1) if match else None


def _summary(playlist: dict) -> dict:
    tracks = playlist.get("tracks", [])
    return {
        "playlistId": playlist["playlistId"],
        "title": playlist["title"],
        "source": playlist.get("source", "local"),
        "track_count": playlist.get("track_count", len(tracks)),
        "thumbnails": tracks[0].get("thumbnails", []) if tracks else [],
    }


# biblioteca playlists
class LibraryService:
    def __init__(self, gateway: YTMusicGateway, repository: LocalPlaylistRepository,
                 catalog: CatalogService, runner: TaskRunner, recents: RecentPlaylists | None = None):
        self._gateway = gateway
        self._repo = repository
        self._catalog = catalog
        self._runner = runner
        self._recents = recents

    def local_summaries(self) -> list[dict]:
        return [_summary(p) for p in self._repo.all()]

    def playlists(self, on_done: Done) -> None:
        local = self.local_summaries()
        if not self._gateway.is_authenticated:
            on_done(local)
            return

        def work() -> list[dict]:
            remote = self._gateway.get_library_playlists(limit=50)
            return [{
                "playlistId": p.get("playlistId"),
                "title": p.get("title"),
                "source": "ytmusic",
                "track_count": p.get("count", 0),
                "thumbnails": p.get("thumbnails", []),
            } for p in remote]

        def fallback(exc: Exception) -> None:
            log.warning("Library playlists failed: %s", exc)
            on_done(local)

        self._runner.submit(work, lambda remote: on_done(local + remote), fallback, key="library:playlists")

    def playlist_tracks(self, entry: dict, on_done: Done, on_error: Fail | None = None) -> None:
        playlist_id = entry.get("playlistId", "")
        if entry.get("source", "ytmusic") in LOCAL_SOURCES:
            data = self._repo.get(playlist_id)
            tracks = normalize_tracks(data.get("tracks", [])) if data else []
            on_done({"title": data["title"], "tracks": tracks} if tracks else None)
            return
        self._catalog.playlist(playlist_id, on_done, on_error)

    # playlist guardar cloud local
    def save_playlist(self, title: str, tracks: list[Track], *, cloud: bool, on_done: Done) -> None:
        local_ok = self._repo.add(title, tracks, "user_created") is not None
        if not (cloud and self._gateway.is_authenticated):
            on_done((local_ok, False))
            return

        def work() -> bool:
            ids = [t["videoId"] for t in tracks if t.get("videoId")]
            return bool(self._gateway.create_playlist(title, "Creada desde YTMusic Client", ids))

        def failed(exc: Exception) -> None:
            log.warning("Cloud save failed: %s", exc)
            on_done((local_ok, False))

        self._runner.submit(work, lambda ok: on_done((local_ok, ok)), failed)

    def save_targets(self, on_done: Done) -> None:
        def ready(playlists: list[dict]) -> None:
            playlists = [p for p in playlists if p.get("playlistId")]
            by_id = {p["playlistId"]: p for p in playlists}
            recent_ids = self._recents.ids() if self._recents else []
            recent = [by_id[i] for i in recent_ids if i in by_id][:RECENT_SHOWN]
            on_done({"recent": recent, "all": playlists})

        self.playlists(ready)

    # playlist agregar
    def add_to_playlist(self, entry: dict, tracks: Track | list[Track], on_done: Done) -> None:
        playlist_id = entry["playlistId"]
        tracks = [tracks] if isinstance(tracks, dict) else list(tracks)

        def finish(outcome: str) -> None:
            if outcome != "failed" and self._recents:
                self._recents.touch(playlist_id)
            on_done(outcome)

        if entry.get("source", "ytmusic") in LOCAL_SOURCES:
            added = self._repo.add_tracks(playlist_id, tracks)
            finish("failed" if added is None else "added" if added else "duplicate")
            return

        def work() -> bool:
            return self._gateway.add_playlist_items(playlist_id, [t["videoId"] for t in tracks if t.get("videoId")])

        def failed(exc: Exception) -> None:
            log.warning("Adding to playlist %s failed: %s", playlist_id, exc)
            on_done("failed")

        self._runner.submit(work, lambda ok: finish("added" if ok else "failed"), failed)

    def save_imported(self, title: str, tracks: list[Track], *, cloud: bool, on_done: Done) -> None:
        if cloud and self._gateway.is_authenticated:
            def work() -> bool:
                ids = [t["videoId"] for t in tracks if t.get("videoId")]
                return bool(self._gateway.create_playlist(title, "Importada desde YTMusic Client", ids))

            def failed(exc: Exception) -> None:
                log.warning("Cloud save failed: %s", exc)
                on_done(("YouTube Music", False))

            self._runner.submit(work, lambda ok: on_done(("YouTube Music", ok)), failed)
            return
        on_done(("local", self._repo.add(title, tracks, "imported") is not None))

    def songs(self, on_done: Done) -> None:
        local = self._local_songs()
        if not self._gateway.is_authenticated:
            on_done(local)
            return

        def work() -> list[Track]:
            return normalize_tracks(self._gateway.get_library_songs(limit=50))

        def fallback(exc: Exception) -> None:
            log.warning("Library songs failed: %s", exc)
            on_done(local)

        self._runner.submit(work, lambda songs: on_done(songs or local), fallback, key="library:songs")

    def artists(self) -> list[dict]:
        artist_map: dict[str, dict] = {}
        for playlist in self._repo.all():
            for track in playlist.get("tracks", []):
                for artist in track.get("artists") or []:
                    name = artist.get("name", "")
                    if not name:
                        continue
                    entry = artist_map.setdefault(
                        name, {"name": name, "count": 0, "thumbnails": track.get("thumbnails", [])})
                    entry["count"] += 1
        return sorted(artist_map.values(), key=lambda a: -a["count"])

    def _local_songs(self) -> list[Track]:
        seen: set[str] = set()
        songs: list[Track] = []
        for playlist in self._repo.all():
            for track in playlist.get("tracks", []):
                vid = track.get("videoId")
                if vid and vid not in seen:
                    seen.add(vid)
                    songs.append(track)
        return songs
