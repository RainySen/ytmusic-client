import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("YTMUSIC_LIVE_TESTS") != "1", reason="set YTMUSIC_LIVE_TESTS=1 to run live tests")


@pytest.fixture(scope="module")
def app(qapp, tmp_path_factory):
    import qtawesome as qta
    from core import bootstrap
    from core.config import AppPaths

    services = bootstrap.build_services(AppPaths(str(tmp_path_factory.mktemp("live"))))
    ui = bootstrap.build_ui(services, qta.icon("fa5s.music"))
    ui.window.resize(1240, 750)
    ui.window.show()
    ui.start(services)
    services.warm_up()
    yield services, ui
    services.shutdown()


def fetch(wait_until, call, timeout=30000):
    box = {}
    call(lambda r: box.update(result=r), lambda e: box.update(error=e))
    assert wait_until(lambda: box, timeout), "no answer within timeout"
    return box.get("result"), box.get("error")


def test_home_feed_loads(app, wait_until):
    _, ui = app
    assert wait_until(lambda: ui.home._has_content, 30000)


def test_search_gives_artist_card_and_named_songs(app, wait_until):
    services, _ = app
    grouped, error = fetch(wait_until, lambda ok, fail: services.catalog.search("daft punk", ok, fail))
    assert error is None
    assert grouped["top_result"]["resultType"] == "artist"
    assert grouped["songs"] and all(s.get("artists") for s in grouped["songs"])


def test_artist_shuffle_plays(app, wait_until):
    services, _ = app
    grouped, _ = fetch(wait_until, lambda ok, fail: services.catalog.search("daft punk", ok, fail))
    started = []
    services.playback.track_started.connect(started.append)
    hero = grouped["top_result"]
    services.opener.shuffle_artist(services.opener.artist_id(hero), hero.get("artist", ""))
    assert wait_until(lambda: started, 45000)
    assert len(services.queue) > 3
    assert services.audio.is_playing


def test_playback_progresses_and_lyrics_arrive(app, wait_until):
    from domain.models import normalize_track

    services, ui = app
    raw = services.gateway.search("one more time daft punk", filter="songs", limit=5)
    song = normalize_track(raw[0])
    started = []
    services.playback.track_started.connect(started.append)
    services.playback.start_radio(song)
    assert wait_until(lambda: started, 45000)
    assert wait_until(lambda: ui.window.player_panel.time_label.text() != "0:00", 15000)
    lyrics, _ = fetch(wait_until, lambda ok, fail: services.lyrics.fetch(song, ok, fail))
    assert lyrics is not None and len(lyrics.lines) > 5
    assert wait_until(lambda: len(services.queue) >= 5, 20000), "radio queue was not filled"


def test_mood_feed_and_playlist_open(app, wait_until):
    services, _ = app
    sections, _ = fetch(wait_until, lambda ok, fail: services.catalog.load_mood("Fiesta", ok))
    titles = [t for t, _ in sections]
    assert any(t.startswith("Canciones") for t in titles)
    playlists = next(items for t, items in sections if t.startswith("Playlists"))
    data, error = fetch(wait_until, lambda ok, fail: services.catalog.playlist(playlists[0]["playlistId"], ok, fail))
    assert error is None and data and data["tracks"]


def test_album_opens(app, wait_until):
    services, _ = app
    grouped, _ = fetch(wait_until, lambda ok, fail: services.catalog.search("daft punk", ok, fail))
    album = next(m for m in grouped["more"] if m.get("resultType") == "album")
    data, error = fetch(wait_until, lambda ok, fail: services.catalog.album(album["browseId"], ok, fail))
    assert error is None and data and len(data["tracks"]) > 3
    assert all(t.get("thumbnails") for t in data["tracks"])


def test_queue_extends_when_it_runs_out(app, wait_until):
    services, _ = app
    services.queue.clear_except_current()
    before = len(services.queue)
    started = []
    services.playback.track_started.connect(started.append)
    services.audio.finished.emit()
    assert wait_until(lambda: started, 45000), "next track never started"
    assert len(services.queue) > before


def test_session_roundtrip(app):
    services, _ = app
    services.session.save()
    from domain.play_queue import PlayQueue
    from domain.stream_cache import StreamCache
    from services.session_service import SessionService
    from services.stream_service import StreamService

    queue = PlayQueue()
    streams = StreamService(services.resolver, StreamCache(), services.runners[2], services.runners[3])
    SessionService(services.paths.session_file, queue, streams).restore()
    assert [s["videoId"] for s in queue.snapshot()] == [s["videoId"] for s in services.queue.snapshot()]
    assert queue.current_index == services.queue.current_index
    assert len(streams.export_state()) >= 1


def test_explore_shelves_and_mood_playlists(app, wait_until):
    services, _ = app
    sections, error = fetch(wait_until, lambda ok, fail: services.catalog.load_explore(ok, fail))
    assert error is None
    by_title = dict(sections)
    assert by_title["Álbumes y sencillos nuevos"] and by_title["Tendencias"] and by_title["Estados de ánimo y géneros"]
    mood = by_title["Estados de ánimo y géneros"][0]
    playlists, error = fetch(wait_until, lambda ok, fail: services.catalog.mood_playlists(mood["params"], ok, fail))
    assert error is None and playlists and playlists[0]["playlistId"]
    album = by_title["Álbumes y sencillos nuevos"][0]
    data, error = fetch(wait_until, lambda ok, fail: services.catalog.album(album["browseId"], ok, fail))
    assert error is None and data and data["tracks"]


def test_new_song_silences_the_old_one_while_loading(app, wait_until):
    services, _ = app
    songs = services.gateway.search("daft punk", filter="songs", limit=5)
    from domain.models import normalize_track

    first, second = normalize_track(songs[0]), normalize_track(songs[1])
    started = []
    services.playback.track_started.connect(started.append)
    services.playback.start_radio(first)
    assert wait_until(lambda: started and services.audio.is_playing, 45000)
    started.clear()
    services.streams.invalidate(second["videoId"])
    services.playback.start_radio(second)
    assert services.audio.is_playing is False
    assert wait_until(lambda: started and services.audio.is_playing, 45000)
    assert started[-1]["videoId"] == second["videoId"]


def test_related_content_for_the_playing_song(app, wait_until):
    services, _ = app
    song = services.queue.current
    assert song
    data, error = fetch(wait_until, lambda ok, fail: services.catalog.related(song["videoId"], ok, fail))
    assert error is None
    assert 4 <= len(data["songs"]) <= 20 and data["playlists"] and data["artists"]
    assert len(data["playlists"]) <= 6 and len(data["artists"]) <= 6
    assert all(a["browseId"].startswith("UC") for a in data["artists"])


def test_artist_profile_and_album_page(app, wait_until):
    services, _ = app
    grouped, _ = fetch(wait_until, lambda ok, fail: services.catalog.search("madmans esprit", ok, fail))
    hero = grouped["top_result"]
    artist_id = services.opener.artist_id(hero)
    profile, error = fetch(wait_until, lambda ok, fail: services.catalog.artist_profile(artist_id, ok, fail))
    assert error is None and profile["name"] and len(profile["top_songs"]) == 5
    assert profile["songs_browse_id"] and profile["banner"]
    titles = [t for t, _ in profile["sections"]]
    assert "Álbumes" in titles or "Sencillos y EP" in titles
    release = next(i for t, items in profile["sections"] if t in ("Álbumes", "Sencillos y EP") for i in items)
    assert release["type"] == "album" and release["subtitle"].split(" • ")[0] in ("Álbum", "Sencillo", "EP")
    album, error = fetch(wait_until, lambda ok, fail: services.catalog.album(release["browseId"], ok, fail))
    assert error is None and album["tracks"] and album["kind"] and all(t.get("thumbnails") for t in album["tracks"])
    everything, error = fetch(wait_until, lambda ok, fail: services.catalog.playlist(profile["songs_browse_id"], ok, fail))
    assert error is None and len(everything["tracks"]) >= 5


def test_opening_an_artist_shows_their_page_in_the_app(app, wait_until):
    services, ui = app
    grouped, _ = fetch(wait_until, lambda ok, fail: services.catalog.search("daft punk", ok, fail))
    services.opener.open(grouped["top_result"])
    assert wait_until(lambda: ui.window.artist_panel.songs is not None, 30000)
    assert ui.window.current_view == "artist" and ui.window.artist_panel.songs.row_count == 5


def test_home_playlists_open_as_pages_and_mixes_fall_back(app, wait_until):
    services, ui = app
    sections, error = fetch(wait_until, lambda ok, fail: services.catalog.load_home(ok, fail))
    assert error is None
    playlists = [i for _, items in sections for i in items if i.get("type") == "playlist" and i.get("playlistId")]
    assert playlists
    mixes = [p for p in playlists if p["playlistId"].startswith("RD")][:2]
    pages = []
    for item in (playlists[:3] + mixes):
        page, error = fetch(wait_until, lambda ok, fail: services.catalog.playlist_details(item["playlistId"], ok, fail))
        assert error is None, item
        if page:
            pages.append(page)
            assert page["title"] and page["tracks"] and all(t.get("videoId") for t in page["tracks"])
    assert pages, "no home playlist could be opened as a page"
    services.opener.open(playlists[0])
    assert wait_until(lambda: ui.window.album_panel.tracks is not None, 30000)
    assert ui.window.current_view == "album" and ui.window.album_panel.tracks.row_count > 0


def test_playlist_card_play_button_plays_the_collection(app, wait_until):
    services, ui = app
    sections, _ = fetch(wait_until, lambda ok, fail: services.catalog.load_home(ok, fail))
    item = next(i for _, items in sections for i in items if i.get("type") == "playlist" and i.get("playlistId"))
    started = []
    services.playback.track_started.connect(started.append)
    ui.window.collection_action_requested.emit("play", item)
    assert wait_until(lambda: started, 45000)
    assert len(services.queue) > 1


def test_lyrics_chain_finds_timed_lyrics_for_a_popular_song(app, wait_until):
    services, _ = app
    songs = services.gateway.search("daft punk instant crush", filter="songs", limit=1)
    from domain.models import normalize_track

    song = normalize_track(songs[0])
    lyrics, error = fetch(wait_until, lambda ok, fail: services.lyrics.fetch(song, ok, fail), timeout=45000)
    assert error is None and lyrics is not None and len(lyrics.lines) > 10
    assert lyrics.source in ("Better Lyrics", "LRCLIB", "YouTube Music")
    if lyrics.source == "LRCLIB":
        assert lyrics.synced and lyrics.lines[3].time_ms > lyrics.lines[2].time_ms > 0
