import threading
import time

import pytest

from domain.stream_cache import StreamCache, StreamInfo
from infra.concurrency import TaskRunner
from infra.playlist_repository import LocalPlaylistRepository
from services.catalog_service import CatalogService
from services.library_service import LibraryService, extract_playlist_id
from services.stream_service import StreamService


class FakeResolver:
    def __init__(self):
        self.calls = []
        self.gates = {}
        self.fail = set()
        self.lock = threading.Lock()

    def gate(self, video_id):
        event = threading.Event()
        self.gates[video_id] = event
        return event

    def resolve(self, video_id):
        with self.lock:
            self.calls.append(video_id)
        gate = self.gates.get(video_id)
        if gate:
            gate.wait(2)
        if video_id in self.fail:
            raise RuntimeError("unavailable")
        return StreamInfo(video_id, f"url-{video_id}", video_id, time.time() + 3600)


@pytest.fixture
def streams(qapp):
    resolver = FakeResolver()
    play, prefetch = TaskRunner("play", 2), TaskRunner("prefetch", 1)
    service = StreamService(resolver, StreamCache(), play, prefetch)
    yield service, resolver
    play.shutdown()
    prefetch.shutdown()


def collect(service):
    resolved, failed = [], []
    service.resolved.connect(lambda vid, info: resolved.append((vid, info.url)))
    service.failed.connect(lambda vid, msg: failed.append((vid, msg)))
    return resolved, failed


def test_request_resolves_and_caches(streams, wait_until):
    service, resolver = streams
    resolved, _ = collect(service)
    service.request("a")
    assert wait_until(lambda: resolved)
    assert resolved == [("a", "url-a")]
    service.request("a")
    assert len(resolved) == 2 and resolver.calls == ["a"]


def test_failure_is_reported(streams, wait_until):
    service, resolver = streams
    _, failed = collect(service)
    resolver.fail.add("bad")
    service.request("bad")
    assert wait_until(lambda: failed)
    assert failed[0][0] == "bad" and "unavailable" in failed[0][1]


def test_duplicate_requests_are_deduplicated(streams, wait_until):
    service, resolver = streams
    resolved, _ = collect(service)
    gate = resolver.gate("a")
    service.request("a")
    service.request("a")
    gate.set()
    assert wait_until(lambda: resolved)
    wait_until(lambda: False, 100)
    assert resolver.calls == ["a"] and len(resolved) == 1


def test_prefetch_skips_cached_and_inflight(streams, wait_until):
    service, resolver = streams
    resolved, _ = collect(service)
    service.request("a")
    assert wait_until(lambda: resolved)
    service.prefetch(["a", "b", "b", ""])
    assert wait_until(lambda: len(resolved) == 2)
    assert sorted(resolver.calls) == ["a", "b"]


def test_request_promotes_queued_prefetch(streams, wait_until):
    service, resolver = streams
    resolved, _ = collect(service)
    gate = resolver.gate("first")
    service.prefetch(["first", "second"])
    wait_until(lambda: resolver.calls == ["first"], 500)
    service.request("second")
    assert wait_until(lambda: any(v == "second" for v, _ in resolved), 1500)
    gate.set()
    assert wait_until(lambda: any(v == "first" for v, _ in resolved))


def test_request_reuses_running_prefetch(streams, wait_until):
    service, resolver = streams
    resolved, _ = collect(service)
    gate = resolver.gate("a")
    service.prefetch(["a"])
    wait_until(lambda: resolver.calls == ["a"], 500)
    service.request("a")
    gate.set()
    assert wait_until(lambda: resolved)
    wait_until(lambda: False, 100)
    assert resolver.calls == ["a"] and len(resolved) == 1


def test_state_export_import(streams):
    service, _ = streams
    service._cache.put(StreamInfo("x", "u", "t", time.time() + 100))
    state = service.export_state()
    other = StreamService(FakeResolver(), StreamCache(), TaskRunner("p", 1), TaskRunner("q", 1))
    assert other.import_state(state) == 1 and other.cached("x").url == "u"


class FakeGateway:
    is_authenticated = False

    def __init__(self):
        self.calls = []
        self.home_sections = [{"title": "S1", "contents": [{"videoId": "v", "title": "x"}]},
                              {"title": "Empty", "contents": []}]
        self.search_result = []
        self.watch = {"tracks": [{"videoId": "seed"}, {"videoId": "r1", "title": "R1"}]}
        self.fail_search = False

    def get_home(self, limit):
        self.calls.append(("home", limit))
        return self.home_sections

    def search(self, query, filter=None, limit=25):
        self.calls.append(("search", query, filter))
        if self.fail_search:
            raise RuntimeError("down")
        return self.search_result

    def get_watch_playlist(self, video_id, limit):
        self.calls.append(("watch", video_id, limit))
        return self.watch

    def get_playlist(self, playlist_id, limit=None):
        self.calls.append(("playlist", playlist_id))
        return {"title": "PL", "tracks": [{"videoId": "a"}, {"title": "no id"}]}


@pytest.fixture
def catalog(qapp, tmp_path):
    gateway = FakeGateway()
    runner = TaskRunner("catalog", 4)
    service = CatalogService(gateway, runner, str(tmp_path / "home.json"))
    yield service, gateway
    runner.shutdown()


def test_home_loads_and_is_persisted(catalog, wait_until):
    service, gateway = catalog
    full = []
    service.load_home(full.append)
    assert wait_until(lambda: full)
    assert full[0] == [("S1", [{"type": "song", "videoId": "v", "title": "x", "artists": [], "thumbnails": []}])]
    assert [c for c in gateway.calls if c[0] == "home"] == [("home", 20)]
    assert service.stored_home() == full[0]


def test_home_uses_memory_cache_until_forced(catalog, wait_until):
    service, gateway = catalog
    full = []
    service.load_home(full.append)
    assert wait_until(lambda: full)
    before = len(gateway.calls)
    service.load_home(full.append)
    assert len(full) == 2 and len(gateway.calls) == before
    service.load_home(full.append, force=True)
    assert wait_until(lambda: len(full) == 3)


def test_home_error_reaches_callback(catalog, wait_until):
    service, gateway = catalog

    def boom(limit):
        raise RuntimeError("offline")

    gateway.get_home = boom
    errors = []
    service.load_home(lambda s: None, errors.append)
    assert wait_until(lambda: errors)


def test_stored_home_missing_or_corrupt(catalog):
    service, _ = catalog
    assert service.stored_home() is None


def test_search_groups_and_caches(catalog, wait_until):
    service, gateway = catalog
    gateway.search_result = [{"category": "Top result", "resultType": "artist"},
                             {"category": "Songs", "resultType": "song", "videoId": "1"}]
    out = []
    service.search("Foo", out.append)
    assert wait_until(lambda: out)
    assert out[0]["top_result"]["resultType"] == "artist" and len(out[0]["songs"]) == 1
    service.search("  foo ", out.append)
    assert len(out) == 2 and len([c for c in gateway.calls if c[0] == "search"]) == 1


def test_search_error_reaches_callback(catalog, wait_until):
    service, gateway = catalog
    gateway.fail_search = True
    errors = []
    service.search("x", lambda r: None, errors.append)
    assert wait_until(lambda: errors)


def test_recommendations_exclude_seed_and_cache(catalog, wait_until):
    service, gateway = catalog
    out = []
    service.recommendations("seed", 5, out.append)
    assert wait_until(lambda: out)
    assert [t["videoId"] for t in out[0]] == ["r1"]
    service.recommendations("seed", 5, out.append)
    assert len(out) == 2 and len([c for c in gateway.calls if c[0] == "watch"]) == 1


def test_mood_runs_three_searches_in_parallel(catalog, wait_until):
    service, gateway = catalog
    gateway.search_result = [{"videoId": "s1", "title": "S", "playlistId": "PL1"}]
    out = []
    service.load_mood("Fiesta", out.append)
    assert wait_until(lambda: out)
    titles = [t for t, _ in out[0]]
    assert titles == ["Canciones — Fiesta", "Mixes para ti", "Playlists • Fiesta"]
    assert out[0][0][1][0]["type"] == "song" and out[0][1][1][0]["type"] == "playlist"


def test_mood_survives_partial_failure(catalog, wait_until):
    service, gateway = catalog
    gateway.fail_search = True
    out = []
    service.load_mood("Fiesta", out.append)
    assert wait_until(lambda: out)
    assert out[0] == []


def test_playlist_drops_tracks_without_id(catalog, wait_until):
    service, _ = catalog
    out = []
    service.playlist("PL", out.append)
    assert wait_until(lambda: out)
    assert out[0]["title"] == "PL" and [t["videoId"] for t in out[0]["tracks"]] == ["a"]


@pytest.fixture
def library(qapp, tmp_path):
    gateway = FakeGateway()
    runner = TaskRunner("lib", 2)
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    catalog = CatalogService(gateway, runner)
    yield LibraryService(gateway, repo, catalog, runner), repo, gateway
    runner.shutdown()


def test_local_playlist_summaries_and_tracks(library):
    service, repo, _ = library
    pid = repo.add("Mine", [{"videoId": "a", "thumbnails": [{"url": "t"}]}], "user_created")
    summaries = service.local_summaries()
    assert summaries[0]["title"] == "Mine" and summaries[0]["thumbnails"] == [{"url": "t"}]
    out = []
    service.playlists(out.append)
    assert out[0][0]["playlistId"] == pid
    tracks = []
    service.playlist_tracks(summaries[0], tracks.append)
    assert tracks[0]["tracks"][0]["videoId"] == "a"


def test_library_songs_and_artists_fall_back_to_local(library):
    service, repo, _ = library
    repo.add("P", [{"videoId": "a", "title": "A", "artists": [{"name": "X"}]},
                   {"videoId": "a", "title": "A", "artists": [{"name": "X"}]},
                   {"videoId": "b", "title": "B", "artists": [{"name": "Y"}, {"name": "X"}]}])
    songs = []
    service.songs(songs.append)
    assert [s["videoId"] for s in songs[0]] == ["a", "b"]
    assert service.artists()[0] == {"name": "X", "count": 3, "thumbnails": []}


def test_save_playlist_locally(library):
    service, repo, _ = library
    result = []
    service.save_playlist("Cola", [{"videoId": "a"}], cloud=True, on_done=result.append)
    assert result == [(True, False)]
    assert repo.all()[0]["source"] == "user_created"


def test_save_imported_locally(library):
    service, repo, _ = library
    result = []
    service.save_imported("Imp", [{"videoId": "a"}], cloud=False, on_done=result.append)
    assert result == [("local", True)] and repo.all()[0]["source"] == "imported"


def test_extract_playlist_id():
    assert extract_playlist_id("https://music.youtube.com/playlist?list=PLabc-_1") == "PLabc-_1"
    assert extract_playlist_id("https://example.com") is None
    assert extract_playlist_id("") is None


def test_explore_sections_shape_and_order(catalog, wait_until):
    service, gateway = catalog
    gateway.get_explore = lambda: {
        "new_releases": [{"title": "Alb", "browseId": "MPREb_1", "type": "Single", "thumbnails": []},
                         {"title": "no id"}],
        "trending": {"items": [{"title": "Song", "videoId": "v1", "thumbnails": []}, {"title": "no id"}]},
        "moods_and_genres": [{"title": "Calma", "params": "abc"}, {"title": "broken"}],
        "new_videos": [{"title": "Vid", "videoId": "v2", "thumbnails": []}],
    }
    out = []
    service.load_explore(out.append)
    assert wait_until(lambda: out)
    titles = [t for t, _ in out[0]]
    assert titles == ["Álbumes y sencillos nuevos", "Tendencias", "Estados de ánimo y géneros",
                      "Videos musicales nuevos"]
    by_title = dict(out[0])
    assert by_title["Álbumes y sencillos nuevos"][0]["type"] == "album" and len(by_title["Álbumes y sencillos nuevos"]) == 1
    assert by_title["Tendencias"][0]["type"] == "song"
    assert by_title["Estados de ánimo y géneros"] == [{"type": "mood", "title": "Calma", "params": "abc"}]
    assert by_title["Videos musicales nuevos"][0]["type"] == "video"


def test_explore_drops_empty_shelves_and_caches(catalog, wait_until):
    service, gateway = catalog
    calls = []

    def fake():
        calls.append(1)
        return {"new_releases": [], "trending": {"items": []}, "moods_and_genres": [], "new_videos": []}

    gateway.get_explore = fake
    out = []
    service.load_explore(out.append)
    assert wait_until(lambda: out) and out[0] == []
    service.load_explore(out.append)
    assert len(calls) == 1 and len(out) == 2


def test_mood_playlists_normalised_and_cached(catalog, wait_until):
    service, gateway = catalog
    calls = []

    def fake(params):
        calls.append(params)
        return [{"title": "Cafecito", "playlistId": "RD1", "thumbnails": []}, {"title": "no id"}]

    gateway.get_mood_playlists = fake
    out = []
    service.mood_playlists("p1", out.append)
    assert wait_until(lambda: out)
    assert out[0] == [{"type": "playlist", "playlistId": "RD1", "title": "Cafecito", "thumbnails": []}]
    service.mood_playlists("p1", out.append)
    assert calls == ["p1"] and len(out) == 2


def test_home_is_enriched_with_extra_shelves(catalog, wait_until):
    service, gateway = catalog
    gateway.get_charts = lambda: {
        "artists": [{"title": "Art", "browseId": "UC1", "thumbnails": []}, {"title": "bad", "browseId": "x"}],
        "videos": [{"title": "Top", "playlistId": "PL1", "thumbnails": []}],
    }
    gateway.get_explore = lambda: {
        "trending": {"items": [{"title": "Song", "videoId": "v1", "thumbnails": []}]},
        "new_videos": [{"title": "Vid", "videoId": "v2", "thumbnails": []}],
        "new_releases": [{"title": "Alb", "browseId": "MPREb_1"}],
    }
    out = []
    service.load_home(out.append)
    assert wait_until(lambda: out)
    titles = [t for t, _ in out[0]]
    assert titles == ["S1", "Artistas populares", "Listas de éxitos", "Tendencias", "Videos musicales nuevos"]
    artists = dict(out[0])["Artistas populares"]
    assert artists == [{"type": "artist", "browseId": "UC1", "title": "Art", "thumbnails": []}]


def test_home_extras_failure_keeps_the_personal_feed(catalog, wait_until):
    service, gateway = catalog

    def boom():
        raise RuntimeError("charts down")

    gateway.get_charts = boom
    out = []
    service.load_home(out.append)
    assert wait_until(lambda: out)
    assert [t for t, _ in out[0]] == ["S1"]


def test_home_personal_failure_still_shows_extras(catalog, wait_until):
    service, gateway = catalog

    def boom(limit):
        raise RuntimeError("home down")

    gateway.get_home = boom
    gateway.get_charts = lambda: {"artists": [], "videos": [{"title": "Top", "playlistId": "PL1"}]}
    errors, out = [], []
    service.load_home(out.append, errors.append)
    assert wait_until(lambda: out or errors)
    assert errors == [] and [t for t, _ in out[0]] == ["Listas de éxitos"]


def test_extras_do_not_duplicate_existing_titles(catalog, wait_until):
    service, gateway = catalog
    gateway.home_sections = [{"title": "Tendencias", "contents": [{"videoId": "v", "title": "x"}]}]
    gateway.get_explore = lambda: {"trending": {"items": [{"title": "Song", "videoId": "v1"}]}}
    out = []
    service.load_home(out.append)
    assert wait_until(lambda: out)
    assert [t for t, _ in out[0]] == ["Tendencias"]


def test_related_shelves_are_recognised_by_content_not_title(catalog, wait_until):
    service, gateway = catalog
    gateway.get_related = lambda vid: [
        {"title": "Tambien te puede interesar", "contents": [{"videoId": f"s{i}", "title": f"S{i}"} for i in range(30)]},
        {"title": "Listas recomendadas", "contents": [
            {"playlistId": f"PL{i}", "title": f"P{i}", "thumbnails": []} for i in range(10)]},
        {"title": "Otras actuaciones", "contents": [{"videoId": "other", "title": "O"}]},
        {"title": "Artistas similares", "contents": [
            {"browseId": f"UC{i}", "title": f"A{i}", "subscribers": "1 M", "thumbnails": []} for i in range(10)]
            + [{"browseId": "MPRE1", "title": "album"}]},
        {"title": "Informacion", "contents": "long text"},
    ]
    out = []
    service.related("v0", out.append)
    assert wait_until(lambda: out)
    data = out[0]
    assert len(data["songs"]) == 20 and data["songs"][0]["type"] == "song"
    assert len(data["playlists"]) == 6 and data["playlists"][0]["type"] == "playlist"
    assert len(data["artists"]) == 6
    assert data["artists"][0] == {"type": "artist", "browseId": "UC0", "title": "A0", "subscribers": "1 M",
                                  "thumbnails": []}


def test_related_tolerates_missing_shelves_and_errors(catalog, wait_until):
    service, gateway = catalog
    gateway.get_related = lambda vid: []
    out = []
    service.related("v0", out.append)
    assert wait_until(lambda: out) and out[0] == {"songs": [], "playlists": [], "artists": []}

    def boom(vid):
        raise RuntimeError("offline")

    gateway.get_related = boom
    errors = []
    service.related("v1", out.append, errors.append)
    assert wait_until(lambda: errors)


@pytest.fixture
def saving(qapp, tmp_path):
    from infra.recent_playlists import RecentPlaylists

    gateway = FakeGateway()
    runner = TaskRunner("save", 2)
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    recents = RecentPlaylists(str(tmp_path / "recent.json"))
    service = LibraryService(gateway, repo, CatalogService(gateway, runner), runner, recents)
    yield service, repo, gateway, recents
    runner.shutdown()


def test_save_targets_lists_local_playlists_and_recent_ones(saving):
    service, repo, _, recents = saving
    ids = [repo.add(name, [{"videoId": name}], "user_created") for name in "ABCDEF"]
    recents.touch(ids[4])
    recents.touch(ids[1])
    recents.touch("deleted-long-ago")
    out = []
    service.save_targets(out.append)
    assert [p["title"] for p in out[0]["all"]] == list("ABCDEF")
    assert [p["title"] for p in out[0]["recent"]] == ["B", "E"]


def test_save_targets_shows_at_most_four_recent(saving):
    service, repo, _, recents = saving
    for pid in [repo.add(str(n), []) for n in range(7)]:
        recents.touch(pid)
    out = []
    service.save_targets(out.append)
    assert len(out[0]["recent"]) == 4


def test_add_to_local_playlist_reports_added_then_duplicate(saving):
    service, repo, _, recents = saving
    pid = repo.add("Mine", [], "user_created")
    entry = service.local_summaries()[0]
    out = []
    service.add_to_playlist(entry, {"videoId": "a", "title": "A"}, out.append)
    service.add_to_playlist(entry, {"videoId": "a", "title": "A"}, out.append)
    assert out == ["added", "duplicate"]
    assert [t["videoId"] for t in repo.get(pid)["tracks"]] == ["a"] and recents.ids() == [pid]


def test_add_to_missing_local_playlist_fails_without_touching_recents(saving):
    service, _, _, recents = saving
    out = []
    service.add_to_playlist({"playlistId": "local_gone", "source": "local"}, {"videoId": "a"}, out.append)
    assert out == ["failed"] and recents.ids() == []


def test_add_to_account_playlist_uses_the_gateway(saving, wait_until):
    service, _, gateway, recents = saving
    calls = []
    gateway.add_playlist_items = lambda pid, ids: calls.append((pid, ids)) or True
    out = []
    service.add_to_playlist({"playlistId": "PL1", "source": "ytmusic"}, {"videoId": "a"}, out.append)
    assert wait_until(lambda: out)
    assert out == ["added"] and calls == [("PL1", ["a"])] and recents.ids() == ["PL1"]


def test_account_playlist_refusal_and_errors_are_failures(saving, wait_until):
    service, _, gateway, recents = saving
    out = []
    gateway.add_playlist_items = lambda pid, ids: False
    service.add_to_playlist({"playlistId": "PL1", "source": "ytmusic"}, {"videoId": "a"}, out.append)
    assert wait_until(lambda: out == ["failed"])

    def boom(pid, ids):
        raise RuntimeError("offline")

    gateway.add_playlist_items = boom
    service.add_to_playlist({"playlistId": "PL1", "source": "ytmusic"}, {"videoId": "a"}, out.append)
    assert wait_until(lambda: out == ["failed", "failed"]) and recents.ids() == []
