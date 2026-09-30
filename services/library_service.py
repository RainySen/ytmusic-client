from __future__ import annotations

import logging
from typing import Any, Callable

from domain.models import LOCAL_SOURCES, Track, normalize_artist_card, normalize_tracks
from infra.concurrency import TaskRunner
from infra.playlist_repository import LocalPlaylistRepository
from infra.pinned_playlists import PinnedPlaylists
from infra.recent_playlists import RecentPlaylists
from infra.ytmusic_gateway import YTMusicGateway
from services.catalog_service import CatalogService

log = logging.getLogger(__name__)

RECENT_SHOWN = 4
SONGS_PAGE = 50
LIKED_PAGE = 50
PAGE_STEP = 100
PAGE_CAP = 1000
LIBRARY_ARTISTS = 100
CHANNEL_ID = "__self__"
CHANNEL_HISTORY_SONGS = 10
CHANNEL_ARTISTS = 8

Done = Callable[[Any], None]
Fail = Callable[[Exception], None]

def _summary(playlist: dict) -> dict:
    tracks = playlist.get("tracks", [])
    return {
        "playlistId": playlist["playlistId"],
        "title": playlist["title"],
        "source": playlist.get("source", "local"),
        "track_count": playlist.get("track_count", len(tracks)),
        "thumbnails": tracks[0].get("thumbnails", []) if tracks else [],
        "updated_at": playlist.get("updated_at") or playlist.get("created_at", ""),
    }


class LibraryService:
    def __init__(self, gateway: YTMusicGateway, repository: LocalPlaylistRepository,
                 catalog: CatalogService, runner: TaskRunner, recents: RecentPlaylists | None = None,
                 pins: PinnedPlaylists | None = None):
        self._gateway = gateway
        self._repo = repository
        self._catalog = catalog
        self._runner = runner
        self._recents = recents
        self._pins = pins
        self._remote: list[dict] | None = None
        self._waiters: list[tuple[Done, bool]] = []

    def local_summaries(self) -> list[dict]:
        return [_summary(p) for p in self._repo.all()]

    # one shared request for grid and rail; cache served first, re-notify only on change
    def playlists(self, on_done: Done) -> None:
        if not self._gateway.is_authenticated:
            self._remote = None
            on_done(self._sorted(self.local_summaries()))
            return
        cached = self._remote is not None
        if cached:
            on_done(self._sorted(self.local_summaries() + self._remote))
        self._waiters.append((on_done, cached))
        if len(self._waiters) > 1:
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

        def finish(remote: list[dict] | None) -> None:
            changed = remote is not None and remote != self._remote
            if remote is not None:
                self._remote = remote
            waiters, self._waiters = self._waiters, []
            result = self._sorted(self.local_summaries() + (self._remote or []))
            for callback, served in waiters:
                if changed or not served:
                    callback(result)

        def fallback(exc: Exception) -> None:
            log.warning("Library playlists failed: %s", exc)
            finish(None)

        self._runner.submit(work, finish, fallback, key="library:playlists")

    def library_artists(self, on_done: Done) -> None:
        if not self._gateway.is_authenticated:
            on_done(self.artists())
            return

        def work() -> list[dict]:
            raw = self._gateway.get_library_artists(limit=LIBRARY_ARTISTS)
            return [a for a in (normalize_artist_card(a) for a in raw) if a]

        def fallback(exc: Exception) -> None:
            log.warning("Library artists failed: %s", exc)
            on_done(self.artists())

        self._runner.submit(work, lambda found: on_done(found or self.artists()), fallback, key="library:artists")

    def _sorted(self, playlists: list[dict]) -> list[dict]:
        pins = self._pins.ids() if self._pins else []
        by_id = {p["playlistId"]: p for p in playlists if p.get("playlistId")}
        pinned = [{**by_id[i], "pinned": True} for i in pins if i in by_id]
        rest = [p for p in playlists if p.get("playlistId") not in pins]
        rest.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
        return pinned + [{**p, "pinned": False} for p in rest]

    def toggle_pin(self, playlist_id: str) -> bool:
        return self._pins.toggle(playlist_id) if self._pins else False

    def delete_local_playlist(self, playlist_id: str) -> bool:
        ok = self._repo.delete(playlist_id)
        if ok and self._pins:
            self._pins.discard(playlist_id)
        return ok

    def playlist_tracks(self, entry: dict, on_done: Done, on_error: Fail | None = None) -> None:
        playlist_id = entry.get("playlistId", "")
        if entry.get("source", "ytmusic") in LOCAL_SOURCES:
            data = self._repo.get(playlist_id)
            tracks = normalize_tracks(data.get("tracks", [])) if data else []
            on_done({"title": data["title"], "tracks": tracks} if tracks else None)
            return
        self._catalog.playlist(playlist_id, on_done, on_error)

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

    def like_status(self, video_id: str, on_done: Done) -> None:
        self._runner.submit(lambda: self._gateway.get_like_status(video_id), on_done, lambda _exc: on_done(None),
                            key="like-status")

    def set_like(self, video_id: str, liked: bool, on_done: Done) -> None:
        def failed(exc: Exception) -> None:
            log.warning("Rating %s failed: %s", video_id, exc)
            on_done(False)

        self._runner.submit(lambda: self._gateway.rate_song(video_id, "LIKE" if liked else "INDIFFERENT"),
                            lambda _: on_done(True), failed)

    # no cursor in ytmusicapi: each page asks again with a larger limit
    def liked_songs(self, on_done: Done, limit: int = LIKED_PAGE) -> None:
        if not self._gateway.is_authenticated:
            on_done(None)
            return

        def failed(exc: Exception) -> None:
            log.warning("Liked songs failed: %s", exc)
            on_done(None)

        self._runner.submit(lambda: normalize_tracks(self._gateway.get_liked_songs(limit=limit)),
                            on_done, failed, key="library:liked")

    def songs(self, on_done: Done, limit: int = SONGS_PAGE) -> None:
        local = self._local_songs()
        if not self._gateway.is_authenticated:
            on_done(local)
            return

        def work() -> list[Track]:
            return normalize_tracks(self._gateway.get_library_songs(limit=limit))

        def fallback(exc: Exception) -> None:
            log.warning("Library songs failed: %s", exc)
            on_done(local)

        self._runner.submit(work, lambda songs: on_done(songs or local), fallback, key="library:songs")

    def channel_profile(self, on_done: Done) -> None:
        if not self._gateway.is_authenticated:
            on_done(None)
            return

        def work() -> dict:
            account = self._gateway.get_account_info()
            try:
                history = normalize_tracks(self._gateway.get_history())[:CHANNEL_HISTORY_SONGS]
            except Exception:
                log.info("History unavailable for the channel page", exc_info=True)
                history = []
            try:
                raw_artists = self._gateway.get_library_artists(limit=CHANNEL_ARTISTS)
                artists = [a for a in (normalize_artist_card(a) for a in raw_artists) if a]
            except Exception:
                log.info("Library artists unavailable for the channel page", exc_info=True)
                artists = []
            photo = account.get("accountPhotoUrl")
            return {
                "id": CHANNEL_ID,
                "name": account.get("accountName") or "",
                "subscribers": account.get("channelHandle") or "",
                "description": "",
                "banner": [{"url": photo}] if photo else [],
                "top_songs": history,
                "songs_title": "Escuchado recientemente",
                "songs_browse_id": "",
                "shuffle_id": "",
                "radio_id": "",
                "sections": [("Tus artistas favoritos", artists)] if artists else [],
            }

        def failed(exc: Exception) -> None:
            log.warning("Channel profile failed: %s", exc)
            on_done(None)

        self._runner.submit(work, on_done, failed, key="library:channel")

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
