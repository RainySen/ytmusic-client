import time

from domain.models import (
    Lyrics, artist_names, normalize_track, parse_home_section, parse_lyrics, parse_time_ms,
    playlist_id_of, primary_artist, thumbnail_url,
)
from domain.search_results import flatten_search_results, group_search_results
from domain.stream_cache import StreamCache, StreamInfo, expiry_from_url
from infra.ttl_cache import TTLCache


def test_thumbnail_picks_smallest_sufficient():
    item = {"thumbnails": [{"url": "big", "width": 544}, {"url": "small", "width": 60}, {"url": "mid", "width": 226}]}
    assert thumbnail_url(item, 200) == "mid"
    assert thumbnail_url(item, 0) == "small"
    assert thumbnail_url(item, 9999) == "big"


def test_thumbnail_falls_back_to_video_id():
    assert thumbnail_url({"videoId": "abc"}).endswith("/abc/hqdefault.jpg")
    assert thumbnail_url({}) == ""


def test_artist_helpers():
    song = {"artists": [{"name": "A"}, {"name": "B"}, {"name": ""}]}
    assert artist_names(song) == "A • B"
    assert artist_names(song, limit=1) == "A"
    assert primary_artist(song) == "A"
    assert primary_artist({}) == "Desconocido"


def test_normalize_track_requires_video_id():
    assert normalize_track({"title": "x"}) is None
    track = normalize_track({"videoId": "v", "extra": 1})
    assert track["title"] == "Título Desconocido" and track["artists"][0]["name"] == "Desconocido"


def test_playlist_id_strips_vl_prefix():
    assert playlist_id_of({"playlistId": "PL1"}) == "PL1"
    assert playlist_id_of({"browseId": "VLPL2"}) == "PL2"
    assert playlist_id_of({"browseId": "MPRE"}) == "MPRE"


def test_parse_home_section_kinds():
    section = {"contents": [
        {"videoId": "v", "title": "S"}, {"playlistId": "p", "title": "P"},
        {"browseId": "b", "title": "A"}, None, {"unknown": 1},
    ]}
    assert [i["type"] for i in parse_home_section(section)] == ["song", "playlist", "album"]


def test_parse_time_ms():
    assert parse_time_ms("1:05") == 65000
    assert parse_time_ms("1:02:03") == 3723000
    assert parse_time_ms("12.5") == 12500
    assert parse_time_ms("") == 0 and parse_time_ms("garbage") == 0 and parse_time_ms(None) == 0


def test_parse_lyrics_synced_and_plain():
    synced = parse_lyrics({"lines": [{"text": "a", "time": "0:01"}, {"text": "b", "time": "0:02"}]})
    assert isinstance(synced, Lyrics) and synced.synced and synced.texts == ["a", "b"]
    plain = parse_lyrics({"lyrics": "x\ny"})
    assert not plain.synced and plain.texts == ["x", "y"]
    assert parse_lyrics(None) is None and parse_lyrics({}) is None


def test_group_search_results():
    raw = [
        {"category": "Top result", "resultType": "artist", "artist": "X"},
        {"category": "Songs", "resultType": "song", "videoId": "1"},
        {"resultType": "song", "videoId": "2"},
        {"category": "Albums", "resultType": "album"},
    ]
    grouped = group_search_results(raw)
    assert grouped["top_result"]["artist"] == "X"
    assert [s["videoId"] for s in grouped["songs"]] == ["1", "2"]
    assert len(grouped["more"]) == 1
    assert len(flatten_search_results(grouped)) == 4


def test_songs_under_artist_card_inherit_the_artist():
    artist = {"category": "Top result", "resultType": "artist", "artists": [{"name": "Daft Punk", "id": "UC1"}]}
    raw = [artist,
           {"resultType": "song", "videoId": "1", "title": "A"},
           {"resultType": "song", "videoId": "2", "title": "B", "artists": [{"name": "Other"}]}]
    songs = group_search_results(raw)["songs"]
    assert songs[0]["artists"][0]["name"] == "Daft Punk"
    assert songs[1]["artists"][0]["name"] == "Other"


def test_songs_untouched_when_top_result_is_not_an_artist():
    raw = [{"category": "Top result", "resultType": "song", "videoId": "0", "title": "T"},
           {"resultType": "song", "videoId": "1", "title": "A"}]
    grouped = group_search_results(raw)
    assert "artists" not in grouped["songs"][0]


def test_expiry_from_url():
    assert expiry_from_url("https://x/y?a=1&expire=1234567890&b=2") == 1234567890.0
    now = 1000.0
    assert expiry_from_url("https://x/y", default_ttl=50, now=now) == 1050.0
    assert expiry_from_url("https://x/y?expire=notanumber", default_ttl=50, now=now) == 1050.0


def test_stream_cache_expiry_and_lru():
    cache = StreamCache(margin=0, max_size=2)
    live = StreamInfo("a", "u", "t", time.time() + 100)
    dead = StreamInfo("b", "u", "t", time.time() - 1)
    cache.put(live)
    cache.put(dead)
    assert cache.get("a") is live and cache.get("b") is None
    cache.put(StreamInfo("c", "u", "t", time.time() + 100))
    cache.put(StreamInfo("d", "u", "t", time.time() + 100))
    assert len(cache) == 2 and cache.get("a") is None


def test_stream_cache_margin():
    cache = StreamCache(margin=60)
    cache.put(StreamInfo("a", "u", "t", time.time() + 30))
    assert cache.get("a") is None


def test_stream_cache_export_load_roundtrip():
    cache = StreamCache()
    cache.put(StreamInfo("a", "u", "t", time.time() + 100))
    cache.put(StreamInfo("old", "u", "t", time.time() - 100))
    exported = cache.export()
    assert list(exported) == ["a"]
    other = StreamCache()
    assert other.load({**exported, "bad": {"nope": 1}}) == 1
    assert other.get("a").url == "u"


def test_ttl_cache_expires():
    now = [0.0]
    cache = TTLCache(clock=lambda: now[0])
    cache.set("k", "v", ttl=10)
    assert cache.get("k") == "v"
    now[0] = 10.1
    assert cache.get("k") is None


def test_ttl_cache_evicts_oldest_at_capacity():
    now = [0.0]
    cache = TTLCache(clock=lambda: now[0], max_items=2)
    cache.set("a", 1, 10)
    now[0] = 1
    cache.set("b", 2, 10)
    now[0] = 2
    cache.set("c", 3, 10)
    assert cache.get("a") is None and cache.get("b") == 2 and cache.get("c") == 3


GOOGLE = "https://yt3.googleusercontent.com/abc_DEF-123"


def google_thumbs(*widths):
    return [{"url": f"{GOOGLE}=w{w}-h{w}-l90-rj", "width": w, "height": w} for w in widths]


def test_small_art_is_rerendered_at_the_requested_size():
    from domain.models import thumbnail_url

    item = {"thumbnails": google_thumbs(60, 120)}
    assert thumbnail_url(item, 1000) == f"{GOOGLE}=w1000-h1000-l90-rj"
    assert thumbnail_url(item, 88) == f"{GOOGLE}=w88-h88-l90-rj"


def test_thumbnail_size_is_capped_and_no_minimum_keeps_the_listed_url():
    from domain.models import MAX_THUMBNAIL_PX, thumbnail_url

    item = {"thumbnails": google_thumbs(60, 226)}
    assert thumbnail_url(item, 5000).endswith(f"=w{MAX_THUMBNAIL_PX}-h{MAX_THUMBNAIL_PX}-l90-rj")
    assert thumbnail_url(item, 0) == f"{GOOGLE}=w60-h60-l90-rj"


def test_other_urls_and_non_square_art_are_left_alone():
    from domain.models import thumbnail_url

    video = {"thumbnails": [{"url": "https://i.ytimg.com/vi/x/hqdefault.jpg?sqp=abc", "width": 400}]}
    assert thumbnail_url(video, 1000) == "https://i.ytimg.com/vi/x/hqdefault.jpg?sqp=abc"
    banner = {"thumbnails": [{"url": f"{GOOGLE}=w1060-h175-l90-rj", "width": 1060}]}
    assert thumbnail_url(banner, 400) == f"{GOOGLE}=w1060-h175-l90-rj"
    assert thumbnail_url({"videoId": "abc"}, 100) == "https://i.ytimg.com/vi/abc/hqdefault.jpg"
    assert thumbnail_url({}, 100) == ""
