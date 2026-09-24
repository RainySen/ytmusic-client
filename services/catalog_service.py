from __future__ import annotations

import logging
from typing import Any, Callable

from config import HOME_SECTIONS
from domain.models import (
    Track, normalize_artist_card, normalize_playlist_item, normalize_release, normalize_track, normalize_tracks,
    normalize_video, parse_home_section, playlist_id_of, release_label,
)
from domain.search_results import group_search_results
from infra.concurrency import TaskHandle, TaskRunner
from infra.json_store import read_json, write_json_atomic
from infra.ttl_cache import TTLCache
from infra.ytmusic_gateway import YTMusicGateway

log = logging.getLogger(__name__)

Section = tuple[str, list[dict]]
Done = Callable[[Any], None]
Fail = Callable[[Exception], None]

HOME_TTL = 300
SEARCH_TTL = 300
RECOMMENDATION_TTL = 600
PLAYLIST_TTL = 600
RELATED_SONGS = 20
RELATED_CARDS = 6
ARTIST_TTL = 600
ARTIST_TOP_SONGS = 5
ALBUM_TTL = 600
PLAYLIST_PAGE_FALLBACK_TRACKS = 50

FEED_KEY = "feed"
EXPLORE_TTL = 900

NEW_RELEASES_TITLE = "Álbumes y sencillos nuevos"
TRENDING_TITLE = "Tendencias"
MOODS_TITLE = "Estados de ánimo y géneros"
NEW_VIDEOS_TITLE = "Videos musicales nuevos"
POPULAR_ARTISTS_TITLE = "Artistas populares"
CHART_LISTS_TITLE = "Listas de éxitos"


# catalogo cache busqueda
class CatalogService:
    def __init__(self, gateway: YTMusicGateway, runner: TaskRunner, home_cache_file: str | None = None):
        self._gateway = gateway
        self._runner = runner
        self._home_cache_file = home_cache_file
        self._cache = TTLCache()

    def clear_cache(self) -> None:
        self._cache.clear()

    def stored_home(self) -> list[Section] | None:
        if not self._home_cache_file:
            return None
        data = read_json(self._home_cache_file)
        if not isinstance(data, list):
            return None
        return [(title, items) for title, items in data if items] or None

    # home cache disco
    def load_home(self, on_done: Done, on_error: Fail | None = None, force: bool = False) -> None:
        fresh = None if force else self._cache.get("home")
        if fresh is not None:
            self._runner.cancel_key(FEED_KEY)
            on_done(fresh)
            return

        def finish(results: list[Any]) -> None:
            personal, extras = results
            extras = extras if isinstance(extras, list) else []
            if isinstance(personal, Exception):
                if not extras:
                    if on_error:
                        on_error(personal)
                    return
                personal = []
            seen = {title.lower() for title, _ in personal}
            sections = personal + [e for e in extras if e[0].lower() not in seen]
            if sections and self._home_cache_file:
                write_json_atomic(self._home_cache_file, sections, indent=None)
            self._cache.set("home", sections, HOME_TTL)
            on_done(sections)

        self._runner.gather([lambda: self._fetch_home(HOME_SECTIONS), self._fetch_extras], finish, key=FEED_KEY)

    def _fetch_home(self, limit: int) -> list[Section]:
        sections = []
        for raw in self._gateway.get_home(limit):
            items = parse_home_section(raw)
            if items:
                sections.append((raw.get("title", "Sección"), items))
        return sections

    def _fetch_extras(self) -> list[Section]:
        extras: list[Section] = []
        try:
            charts = self._gateway.get_charts()
            artists = [{"type": "artist", "browseId": a["browseId"], "title": a.get("title", ""),
                        "thumbnails": a.get("thumbnails", [])}
                       for a in charts.get("artists") or [] if a.get("browseId", "").startswith("UC")]
            extras.append((POPULAR_ARTISTS_TITLE, artists[:20]))
            lists = [{"type": "playlist", "playlistId": v["playlistId"], "title": v.get("title", ""),
                      "thumbnails": v.get("thumbnails", [])}
                     for v in charts.get("videos") or [] if v.get("playlistId")]
            extras.append((CHART_LISTS_TITLE, lists))
        except Exception:
            log.info("Charts unavailable for the home extras", exc_info=True)
        try:
            for title, items in self._fetch_explore_sections():
                if title in (TRENDING_TITLE, NEW_VIDEOS_TITLE):
                    extras.append((title, items))
        except Exception:
            log.info("Explore unavailable for the home extras", exc_info=True)
        return [e for e in extras if e[1]]

    def load_mood(self, mood: str, on_done: Done) -> None:
        cache_key = ("mood", mood)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._runner.cancel_key(FEED_KEY)
            on_done(cached)
            return

        def songs():
            raw = self._gateway.search(f"{mood} canciones", filter="songs", limit=30)
            found = [t for t in (normalize_track(r) for r in raw) if t]
            for track in found:
                track["type"] = "song"
            return (f"Canciones — {mood}", found[:12])

        def mixes():
            raw = self._gateway.search(f"{mood} mix", filter="playlists", limit=30)
            return ("Mixes para ti", self._playlist_items(raw)[:10])

        def playlists():
            raw = self._gateway.search(f"playlist {mood}", filter="playlists", limit=30)
            return (f"Playlists • {mood}", self._playlist_items(raw)[:10])

        def finish(results: list[Any]) -> None:
            sections = [r for r in results if isinstance(r, tuple) and r[1]]
            self._cache.set(cache_key, sections, HOME_TTL)
            on_done(sections)

        self._runner.gather([songs, mixes, playlists], finish, key=FEED_KEY)

    # explorar estantes
    def load_explore(self, on_done: Done, on_error: Fail | None = None) -> None:
        cached = self._cache.get("explore")
        if cached is not None:
            on_done(cached)
            return

        work = self._fetch_explore_sections

        def ok(sections: list[Section]) -> None:
            self._cache.set("explore", sections, EXPLORE_TTL)
            on_done(sections)

        self._runner.submit(work, ok, on_error, key="explore")

    def _fetch_explore_sections(self) -> list[Section]:
        data = self._gateway.get_explore()
        releases = [{**r, "type": "album"} for r in data.get("new_releases") or [] if r.get("browseId")]
        trending = normalize_tracks((data.get("trending") or {}).get("items") or [])
        for track in trending:
            track["type"] = "song"
        moods = [{"type": "mood", "title": m.get("title", ""), "params": m.get("params", "")}
                 for m in data.get("moods_and_genres") or [] if m.get("params")]
        videos = [{**v, "type": "video"} for v in data.get("new_videos") or [] if v.get("videoId")]
        sections = [(NEW_RELEASES_TITLE, releases), (TRENDING_TITLE, trending),
                    (MOODS_TITLE, moods), (NEW_VIDEOS_TITLE, videos)]
        return [sec for sec in sections if sec[1]]

    def mood_playlists(self, params: str, on_done: Done, on_error: Fail | None = None) -> None:
        cache_key = ("mood_playlists", params)
        cached = self._cache.get(cache_key)
        if cached is not None:
            on_done(cached)
            return

        def work() -> list[dict]:
            return self._playlist_items(self._gateway.get_mood_playlists(params))

        def ok(items: list[dict]) -> None:
            self._cache.set(cache_key, items, EXPLORE_TTL)
            on_done(items)

        self._runner.submit(work, ok, on_error, key="explore:mood")

    def search(self, query: str, on_done: Done, on_error: Fail | None = None) -> None:
        cache_key = ("search", query.strip().lower())
        cached = self._cache.get(cache_key)
        if cached is not None:
            on_done(cached)
            return

        def work() -> dict:
            return group_search_results(self._gateway.search(query, limit=25))

        def ok(grouped: dict) -> None:
            self._cache.set(cache_key, grouped, SEARCH_TTL)
            on_done(grouped)

        self._runner.submit(work, ok, on_error, key="search")

    def recommendations(self, video_id: str, limit: int, on_done: Done, on_error: Fail | None = None,
                        key: str | None = None) -> TaskHandle | None:
        cache_key = ("recs", video_id, limit)
        cached = self._cache.get(cache_key)
        if cached is not None:
            on_done(cached)
            return None

        def work() -> list[Track]:
            watch = self._gateway.get_watch_playlist(video_id, limit)
            tracks = normalize_tracks(watch.get("tracks") or [])
            return [t for t in tracks if t["videoId"] != video_id]

        def ok(tracks: list[Track]) -> None:
            self._cache.set(cache_key, tracks, RECOMMENDATION_TTL)
            on_done(tracks)

        return self._runner.submit(work, ok, on_error, key=key)

    # similares
    def related(self, video_id: str, on_done: Done, on_error: Fail | None = None) -> None:
        def work() -> dict:
            shelves = [sh.get("contents") for sh in self._gateway.get_related(video_id)
                       if isinstance(sh.get("contents"), list)]
            songs: list[Track] = []
            playlists: list[dict] = []
            artists: list[dict] = []
            for items in shelves:
                first = items[0] if items and isinstance(items[0], dict) else {}
                if not songs and first.get("videoId"):
                    songs = normalize_tracks(items)[:RELATED_SONGS]
                elif not playlists and first.get("playlistId"):
                    playlists = [normalize_playlist_item(i) for i in items if i.get("playlistId")][:RELATED_CARDS]
                elif not artists and str(first.get("browseId", "")).startswith("UC"):
                    artists = [{"type": "artist", "browseId": i["browseId"], "title": i.get("title", ""),
                                "subscribers": i.get("subscribers", ""), "thumbnails": i.get("thumbnails", [])}
                               for i in items if str(i.get("browseId", "")).startswith("UC")][:RELATED_CARDS]
            for track in songs:
                track["type"] = "song"
            return {"songs": songs, "playlists": playlists, "artists": artists}

        self._runner.submit(work, on_done, on_error, key="related")

    def playlist(self, playlist_id: str, on_done: Done, on_error: Fail | None = None) -> None:
        cache_key = ("playlist", playlist_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            on_done(cached)
            return

        def work() -> dict | None:
            data = self._gateway.get_playlist(playlist_id, limit=None)
            tracks = normalize_tracks(data.get("tracks") or [])
            if not tracks:
                return None
            return {"title": data.get("title") or "Playlist Importada", "tracks": tracks}

        def ok(result: dict | None) -> None:
            if result:
                self._cache.set(cache_key, result, PLAYLIST_TTL)
            on_done(result)

        self._runner.submit(work, ok, on_error, key="playlist")

    # perfil artista cache
    def artist_profile(self, browse_id: str, on_done: Done, on_error: Fail | None = None) -> None:
        cached = self._cache.get(("artist", browse_id))
        if cached is not None:
            on_done(cached)
            return

        def ok(profile: dict) -> None:
            self._cache.set(("artist", browse_id), profile, ARTIST_TTL)
            on_done(profile)

        self._runner.submit(lambda: self._build_artist_profile(browse_id), ok, on_error, key="artist")

    def _build_artist_profile(self, browse_id: str) -> dict:
        raw = self._gateway.get_artist(browse_id)

        def results(key: str) -> list[dict]:
            return (raw.get(key) or {}).get("results") or []

        songs = raw.get("songs") or {}
        shelves = [
            ("Álbumes", [r for r in (normalize_release(a, "Álbum") for a in results("albums")) if r]),
            ("Sencillos y EP", [r for r in (normalize_release(s, "Sencillo") for s in results("singles")) if r]),
            ("Videos", [v for v in (normalize_video(v) for v in results("videos")) if v]),
            ("Fans también escuchan", [a for a in (normalize_artist_card(a) for a in results("related")) if a]),
        ]
        return {
            "id": browse_id,
            "name": raw.get("name", ""),
            "subscribers": raw.get("subscribers") or "",
            "description": raw.get("description") or "",
            "banner": raw.get("thumbnails") or [],
            "top_songs": normalize_tracks((songs.get("results") or [])[:ARTIST_TOP_SONGS]),
            "songs_browse_id": songs.get("browseId") or "",
            "shuffle_id": raw.get("shuffleId") or "",
            "radio_id": raw.get("radioId") or "",
            "sections": [(title, items) for title, items in shelves if items],
        }

    def artist_tracks(self, browse_id: str, on_done: Done, on_error: Fail | None = None) -> None:
        cached = self._cache.get(("artist", browse_id))

        def work() -> dict | None:
            profile = cached or self._build_artist_profile(browse_id)
            tracks: list[Track] = []
            mix_id = profile["shuffle_id"] or profile["radio_id"]
            if mix_id:
                try:
                    tracks = normalize_tracks(self._gateway.get_watch_playlist_for(mix_id, 25).get("tracks") or [])
                except Exception:
                    log.info("Artist mix unavailable for %s", browse_id, exc_info=True)
            tracks = tracks or list(profile["top_songs"])
            return {"title": profile["name"], "tracks": tracks} if tracks else None

        self._runner.submit(work, on_done, on_error, key="collection")

    # playlist pagina
    def playlist_details(self, playlist_id: str, on_done: Done, on_error: Fail | None = None) -> None:
        cached = self._cache.get(("playlist_page", playlist_id))
        if cached is not None:
            on_done(cached)
            return

        def work() -> dict | None:
            raw: dict = {}
            try:
                raw = self._gateway.get_playlist_page(playlist_id) or {}
            except Exception:
                log.info("Playlist page unavailable for %s, trying its queue", playlist_id, exc_info=True)
            tracks = normalize_tracks(raw.get("tracks") or [])
            if not tracks:
                queue = self._gateway.get_watch_playlist_for(playlist_id, PLAYLIST_PAGE_FALLBACK_TRACKS)
                tracks = normalize_tracks(queue.get("tracks") or [])
            if not tracks:
                return None
            author = raw.get("author")
            if isinstance(author, list):
                author = author[0] if author else None
            author = author if isinstance(author, dict) else {"name": author or ""}
            return {
                "id": playlist_id,
                "title": raw.get("title") or "Mix",
                "kind": "Playlist",
                "year": str(raw.get("year") or ""),
                "author": author.get("name") or "",
                "author_id": author.get("id") or "",
                "description": raw.get("description") or "",
                "thumbnails": raw.get("thumbnails") or tracks[0].get("thumbnails") or [],
                "track_count": raw.get("trackCount") or len(tracks),
                "duration": raw.get("duration") or "",
                "tracks": tracks,
            }

        def ok(page: dict | None) -> None:
            if page:
                self._cache.set(("playlist_page", playlist_id), page, PLAYLIST_TTL)
            on_done(page)

        self._runner.submit(work, ok, on_error, key="playlist_page")

    # album pagina
    def album(self, browse_id: str, on_done: Done, on_error: Fail | None = None) -> None:
        cached = self._cache.get(("album", browse_id))
        if cached is not None:
            on_done(cached)
            return

        def work() -> dict | None:
            raw = self._gateway.get_album(browse_id)
            cover = raw.get("thumbnails") or []
            artists = raw.get("artists") or []
            tracks = normalize_tracks([
                {**t, "thumbnails": t.get("thumbnails") or cover, "artists": t.get("artists") or artists,
                 "album": t.get("album") or raw.get("title")}
                for t in raw.get("tracks") or []])
            if not tracks:
                return None
            return {
                "id": browse_id,
                "title": raw.get("title", ""),
                "kind": release_label(raw.get("type")),
                "year": str(raw.get("year") or ""),
                "artists": artists,
                "thumbnails": cover,
                "track_count": raw.get("trackCount") or len(tracks),
                "duration": raw.get("duration") or "",
                "tracks": tracks,
                "more": [r for r in (normalize_release(x) for x in raw.get("related_recommendations") or []) if r],
            }

        def ok(album: dict | None) -> None:
            if album:
                self._cache.set(("album", browse_id), album, ALBUM_TTL)
            on_done(album)

        self._runner.submit(work, ok, on_error, key="album")

    @staticmethod
    def _playlist_items(raw: list[dict]) -> list[dict]:
        return [normalize_playlist_item(r) for r in raw if playlist_id_of(r)]
