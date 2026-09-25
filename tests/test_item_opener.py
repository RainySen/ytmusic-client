import pytest

from services.item_opener import ItemOpener
from tests.fakes import FakeNotifier


class Recorder:
    def __init__(self):
        self.calls = []

    def playlist(self, playlist_id, done, fail):
        self.calls.append(("playlist", playlist_id, done, fail))

    def album_tracks(self, browse_id, done, fail):
        self.calls.append(("album", browse_id, done, fail))

    def artist_tracks(self, browse_id, done, fail):
        self.calls.append(("artist", browse_id, done, fail))

    def artist_profile(self, browse_id, done, fail):
        self.calls.append(("profile", browse_id, done, fail))


class FakeNavigator:
    def __init__(self):
        self.artists = []
        self.albums = []
        self.playlists = []
        self.playlist_requested = type("S", (), {"emit": lambda _s, v: self.playlists.append(v)})()
        self.artist_requested = type("S", (), {"emit": lambda _s, v: self.artists.append(v)})()
        self.album_requested = type("S", (), {"emit": lambda _s, v: self.albums.append(v)})()


class FakePlayback:
    def __init__(self):
        self.radio = []
        self.collections = []

    def start_radio(self, item):
        self.radio.append(item)

    def play_collection(self, tracks):
        self.collections.append(tracks)


@pytest.fixture
def opener():
    catalog, playback, notifier, navigator = Recorder(), FakePlayback(), FakeNotifier(), FakeNavigator()
    opener = ItemOpener(catalog, playback, notifier, navigator)
    opener.navigator = navigator
    return opener, catalog, playback, notifier


def test_song_starts_a_radio(opener):
    o, catalog, playback, _ = opener
    o.open({"videoId": "v", "title": "T"})
    assert playback.radio == [{"videoId": "v", "title": "T"}] and catalog.calls == []


@pytest.mark.parametrize("item, playlist_id", [
    ({"resultType": "playlist", "browseId": "VLPL123", "title": "P"}, "PL123"),
    ({"type": "playlist", "playlistId": "PL9"}, "PL9"),
])
def test_playlists_open_their_page(opener, item, playlist_id):
    o, catalog, playback, _ = opener
    o.open(item)
    assert o.navigator.playlists == [playlist_id] and catalog.calls == [] and playback.collections == []


@pytest.mark.parametrize("item, browse_id", [
    ({"resultType": "album", "browseId": "MPREb_x", "playlistId": "OLAK", "title": "A"}, "MPREb_x"),
    ({"resultType": "single", "browseId": "MPREb_y"}, "MPREb_y"),
    ({"type": "album", "browseId": "MPREb_z"}, "MPREb_z"),
])
def test_albums_singles_and_eps_open_their_page(opener, item, browse_id):
    o, catalog, playback, _ = opener
    o.open(item)
    assert o.navigator.albums == [browse_id] and o.navigator.artists == [] and catalog.calls == []
    assert playback.collections == []


@pytest.mark.parametrize("item, artist_id", [
    ({"resultType": "artist", "artists": [{"name": "X", "id": "UC1"}]}, "UC1"),
    ({"type": "album", "browseId": "UCabc"}, "UCabc"),
    ({"resultType": "artist", "browseId": "UC2"}, "UC2"),
    ({"type": "artist", "browseId": "UC3"}, "UC3"),
])
def test_artists_open_their_profile(opener, item, artist_id):
    o, catalog, playback, _ = opener
    o.open(item)
    assert o.navigator.artists == [artist_id] and o.navigator.albums == [] and catalog.calls == []
    assert playback.collections == []


def test_unknown_item_warns(opener):
    o, catalog, _, notifier = opener
    o.open({"title": "??"})
    assert catalog.calls == [] and notifier.messages[-1][0] == "warning"


def test_artist_without_an_id_warns(opener):
    o, catalog, _, notifier = opener
    o.open({"resultType": "artist", "artists": [{"name": "X"}]})
    assert catalog.calls == [] and notifier.messages[-1][0] == "warning"


def test_loaded_tracks_are_played(opener):
    o, catalog, playback, _ = opener
    o.shuffle_artist("UC1", "Band")
    done = catalog.calls[-1][2]
    done({"title": "A", "tracks": [{"videoId": "1"}, {"videoId": "2"}]})
    assert playback.collections == [[{"videoId": "1"}, {"videoId": "2"}]]


def test_empty_or_failed_load_notifies(opener):
    o, catalog, playback, notifier = opener
    o.shuffle_artist("UC1", "Band")
    _, _, done, fail = catalog.calls[-1]
    done(None)
    assert notifier.messages[-1][0] == "warning" and playback.collections == []
    fail(RuntimeError("offline"))
    assert notifier.messages[-1][0] == "error"


def test_shuffle_artist_plays_their_catalogue(opener):
    o, catalog, playback, notifier = opener
    o.shuffle_artist("UC1", "Band")
    kind, target, done, _ = catalog.calls[-1]
    assert (kind, target) == ("artist", "UC1") and notifier.messages[0] == ("info", "Mezclando «Band»…")
    done({"title": "Band", "tracks": [{"videoId": "m1"}, {"videoId": "m2"}]})
    assert playback.collections == [[{"videoId": "m1"}, {"videoId": "m2"}]]


def test_mix_artist_starts_a_radio_from_one_of_their_songs(opener):
    o, catalog, playback, _ = opener
    o.mix_artist("UC1")
    kind, target, done, _ = catalog.calls[-1]
    assert (kind, target) == ("profile", "UC1")
    done({"top_songs": [{"videoId": "a"}, {"videoId": "b"}, {"videoId": "c"}]})
    assert playback.radio[0]["videoId"] in ("a", "b", "c") and len(playback.radio) == 1


def test_mix_artist_without_songs_or_when_failing_notifies(opener):
    o, catalog, playback, notifier = opener
    o.mix_artist("UC1")
    _, _, done, fail = catalog.calls[-1]
    done({"top_songs": []})
    assert notifier.messages[-1][0] == "warning" and playback.radio == []
    fail(RuntimeError("offline"))
    assert notifier.messages[-1][0] == "error"


def test_artist_id_helper_reads_both_shapes():
    assert ItemOpener.artist_id({"browseId": "UC1"}) == "UC1"
    assert ItemOpener.artist_id({"artists": [{"id": "UC2"}]}) == "UC2"
    assert ItemOpener.artist_id({"title": "x"}) == ""
