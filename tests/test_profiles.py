import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest

from domain.models import (
    normalize_artist_card, normalize_release, normalize_track, normalize_video, parse_home_section, release_label,
)
from infra.concurrency import TaskRunner
from presenters.profile_presenter import ProfilePresenter
from services.catalog_service import CatalogService
from services.navigation import Navigator
from tests.test_presenters import Rig
from tests.test_services import FakeGateway
from tests.test_ui import FakeThumbnails, playlist, song
from ui.components.album_panel import AlbumPanel
from ui.components.artist_panel import ArtistPanel
from ui.components.search_panel import SearchPanel
from ui.components.section_feed import CardsSection, SectionFeed
from ui.components.track_actions import TrackActionsButton
from ui.components.track_list import FIRST_BATCH, TrackList, TrackRow

ARTIST = "UC_artist"


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def raw_song(n, **extra):
    return {"videoId": f"v{n}", "title": f"Song {n}", "artists": [{"name": "Band", "id": ARTIST}],
            "album": {"name": f"Album {n}", "id": f"MPRE{n}"}, "thumbnails": [{"url": "u", "width": 60}],
            "views": None, **extra}


def release(n, kind=None, year="2025"):
    raw = {"title": f"Release {n}", "browseId": f"MPREb_{n}", "thumbnails": [{"url": "u", "width": 226}],
           "year": year}
    if kind:
        raw["type"] = kind
    return raw


def raw_artist():
    return {
        "name": "Band", "subscribers": "42.7 k", "thumbnails": [{"url": "https://x/b=w540-h225", "width": 540}],
        "shuffleId": "RDshuffle", "radioId": "RDradio",
        "songs": {"browseId": "VLOLAKsongs", "results": [raw_song(n) for n in range(1, 9)]},
        "albums": {"results": [release(1), release(2)]},
        "singles": {"results": [release(3, "Single"), release(4, "EP", "2024")]},
        "videos": {"results": [{"videoId": "vid1", "title": "Clip", "artists": [{"name": "Band"}], "views": "21K",
                                "thumbnails": [{"url": "t", "width": 400}]}]},
        "related": {"results": [{"title": "Other", "browseId": "UC_other", "subscribers": "9K", "thumbnails": []}]},
    }


def raw_album():
    return {
        "title": "Release 3", "type": "Single", "year": "2025", "artists": [{"name": "Band", "id": ARTIST}],
        "thumbnails": [{"url": "cover", "width": 544}], "trackCount": 2, "duration": "8 minutos y 14 segundos",
        "tracks": [{"videoId": "a1", "title": "One", "artists": None, "album": "Release 3", "thumbnails": None,
                    "views": "172K plays", "duration": "4:26"},
                   {"videoId": "a2", "title": "Two", "artists": [{"name": "Guest"}], "album": None,
                    "thumbnails": None, "views": None, "duration": "3:48"}],
        "related_recommendations": [dict(release(9, "Album"), artists=[{"name": "Else", "id": "UC_else"}])],
    }


def test_tracks_keep_album_and_spanish_play_counts():
    track = normalize_track(raw_song(1, views="172K plays"))
    assert track["album"] == "Album 1" and track["views"] == "172K reproducciones"
    assert normalize_track({"videoId": "x", "album": "Plain", "views": "5 K reproducciones"})["views"] == "5 K reproducciones"
    bare = normalize_track({"videoId": "x", "album": None, "views": None})
    assert "album" not in bare and "views" not in bare


@pytest.mark.parametrize("kind, label", [("Single", "Sencillo"), ("sencillo", "Sencillo"), ("EP", "EP"),
                                         ("Album", "Álbum"), ("Álbum", "Álbum"), (None, "Álbum"), ("??", "Álbum")])
def test_release_labels(kind, label):
    assert release_label(kind) == label


def test_releases_videos_and_artist_cards():
    single = normalize_release(release(3, "Single"))
    assert single["type"] == "album" and single["subtitle"] == "Sencillo • 2025" and single["browseId"] == "MPREb_3"
    assert normalize_release(release(1), "Sencillo")["subtitle"] == "Sencillo • 2025"
    assert normalize_release({"title": "no id"}) is None
    assert normalize_release({"browseId": "MPREb_x"})["subtitle"] == "Álbum"
    video = normalize_video({"videoId": "v", "title": "T", "artists": [{"name": "Band"}], "views": "21K"})
    assert video["type"] == "video" and video["subtitle"] == "Band • 21K visualizaciones"
    assert normalize_video({"title": "no id"}) is None
    card = normalize_artist_card({"title": "Other", "browseId": "UC1", "subscribers": "9K"})
    assert card["type"] == "artist" and card["subscribers"] == "9K"
    assert normalize_artist_card({"title": "x"}) is None


def test_home_items_with_a_channel_id_are_artists():
    items = parse_home_section({"contents": [{"browseId": "UC1", "title": "A"}, {"browseId": "MPREb_1", "title": "B"}]})
    assert [i["type"] for i in items] == ["artist", "album"]


class ProfileGateway(FakeGateway):
    def __init__(self):
        super().__init__()
        self.artist_calls = 0
        self.album_calls = 0
        self.mix_fails = False

    def get_artist(self, browse_id):
        self.artist_calls += 1
        return raw_artist()

    def get_album(self, browse_id):
        self.album_calls += 1
        return raw_album()

    def get_watch_playlist_for(self, playlist_id, limit):
        if self.mix_fails:
            raise RuntimeError("no mix")
        return {"tracks": [{"videoId": f"m{n}", "title": f"Mix {n}"} for n in range(3)]}


@pytest.fixture
def profiles(qapp, tmp_path):
    gateway = ProfileGateway()
    runner = TaskRunner("profiles", 3)
    yield CatalogService(gateway, runner), gateway
    runner.shutdown()


def ask(wait_until, call):
    box = []
    call(box.append)
    assert wait_until(lambda: box)
    return box[0]


def test_artist_profile_content_and_order(profiles, wait_until):
    catalog, _ = profiles
    profile = ask(wait_until, lambda done: catalog.artist_profile(ARTIST, done))
    assert profile["name"] == "Band" and profile["subscribers"] == "42.7 k"
    assert [s.get("videoId") for s in profile["top_songs"]] == ["v1", "v2", "v3", "v4", "v5"]
    assert profile["songs_browse_id"] == "VLOLAKsongs"
    assert profile["shuffle_id"] == "RDshuffle" and profile["radio_id"] == "RDradio"
    titles = [t for t, _ in profile["sections"]]
    assert titles == ["Álbumes", "Sencillos y EP", "Videos", "Fans también escuchan"]
    singles = dict(profile["sections"])["Sencillos y EP"]
    assert [i["subtitle"] for i in singles] == ["Sencillo • 2025", "EP • 2024"]
    assert dict(profile["sections"])["Álbumes"][0]["subtitle"] == "Álbum • 2025"
    assert dict(profile["sections"])["Videos"][0]["type"] == "video"
    assert dict(profile["sections"])["Fans también escuchan"][0]["browseId"] == "UC_other"


def test_artist_without_some_shelves_drops_them(profiles, wait_until):
    catalog, gateway = profiles
    gateway.get_artist = lambda browse_id: {"name": "Tiny", "songs": {"results": []}, "albums": {"results": []}}
    profile = ask(wait_until, lambda done: catalog.artist_profile("UC_tiny", done))
    assert profile["sections"] == [] and profile["top_songs"] == [] and profile["songs_browse_id"] == ""


def test_artist_profile_is_cached(profiles, wait_until):
    catalog, gateway = profiles
    first = ask(wait_until, lambda done: catalog.artist_profile(ARTIST, done))
    again = []
    catalog.artist_profile(ARTIST, again.append)
    assert again == [first] and gateway.artist_calls == 1


def test_artist_shuffle_uses_the_mix_and_the_cached_profile(profiles, wait_until):
    catalog, gateway = profiles
    ask(wait_until, lambda done: catalog.artist_profile(ARTIST, done))
    data = ask(wait_until, lambda done: catalog.artist_tracks(ARTIST, done))
    assert data["title"] == "Band" and [t["videoId"] for t in data["tracks"]] == ["m0", "m1", "m2"]
    assert gateway.artist_calls == 1


def test_artist_shuffle_falls_back_to_top_songs(profiles, wait_until):
    catalog, gateway = profiles
    gateway.mix_fails = True
    data = ask(wait_until, lambda done: catalog.artist_tracks(ARTIST, done))
    assert [t["videoId"] for t in data["tracks"]] == ["v1", "v2", "v3", "v4", "v5"]


def test_album_page_data(profiles, wait_until):
    catalog, gateway = profiles
    album = ask(wait_until, lambda done: catalog.album("MPREb_3", done))
    assert (album["title"], album["kind"], album["year"], album["track_count"]) == ("Release 3", "Sencillo", "2025", 2)
    one, two = album["tracks"]
    assert one["artists"] == [{"name": "Band", "id": ARTIST}] and two["artists"] == [{"name": "Guest"}]
    assert one["thumbnails"] == [{"url": "cover", "width": 544}]
    assert one["album"] == "Release 3" and one["views"] == "172K reproducciones"
    assert [m["subtitle"] for m in album["more"]] == ["Álbum • 2025"]
    again = []
    catalog.album("MPREb_3", again.append)
    assert again == [album] and gateway.album_calls == 1


def test_album_without_tracks_is_none(profiles, wait_until):
    catalog, gateway = profiles
    gateway.get_album = lambda browse_id: {"title": "Empty", "tracks": []}
    assert ask(wait_until, lambda done: catalog.album("MPREb_e", done)) is None


def test_track_list_builds_in_batches_and_numbers_rows(qapp):
    tracks = [normalize_track(raw_song(n)) for n in range(1, 101)]
    listing = TrackList()
    listing.resize(900, 600)
    listing.show()
    listing.set_tracks(tracks, FakeThumbnails(), numbered=True, show_cover=False)
    assert listing.row_count == FIRST_BATCH
    QTest.qWait(1200)
    assert listing.row_count == 100
    rows = listing.findChildren(TrackRow)
    assert len(rows) == 100


def test_track_list_replacing_tracks_drops_the_old_batches(qapp):
    listing = TrackList()
    listing.show()
    listing.set_tracks([normalize_track(raw_song(n)) for n in range(100)], FakeThumbnails())
    listing.set_tracks([normalize_track(raw_song(1))], FakeThumbnails())
    QTest.qWait(400)
    assert listing.row_count == 1


def test_track_list_signals_carry_position_and_track(qapp):
    tracks = [normalize_track(raw_song(n)) for n in range(1, 4)]
    listing = TrackList()
    listing.resize(900, 300)
    listing.move(400, 400)
    listing.show()
    listing.set_tracks(tracks, FakeThumbnails(), numbered=True)
    chosen = QSignalSpy(listing.track_chosen)
    third = listing.findChildren(TrackRow)[2]
    QTest.mouseClick(third, Qt.LeftButton, pos=third.rect().center())
    assert chosen.count() == 1 and chosen.at(0)[0] == 2 and chosen.at(0)[1]["videoId"] == "v3"
    queued = QSignalSpy(listing.add_playlist_clicked)
    third.findChildren(TrackActionsButton)[0].add_playlist.emit()
    assert queued.count() == 1 and queued.at(0)[0]["videoId"] == "v3"


def test_track_row_shows_only_the_columns_asked_for(qapp):
    from PySide6.QtWidgets import QLabel

    track = normalize_track(raw_song(1, views="172K plays", duration="4:26"))
    full = TrackRow(track, FakeThumbnails(), number=1)
    texts = {label.text() for label in full.findChildren(QLabel)}
    assert {"1", "Song 1", "Band", "172K reproducciones", "Album 1", "4:26"} <= texts
    lean = TrackRow(track, FakeThumbnails(), show_cover=False, show_artist=False, show_album=False)
    lean_texts = {label.text() for label in lean.findChildren(QLabel)}
    assert "Band" not in lean_texts and "Album 1" not in lean_texts and "Song 1" in lean_texts


def test_feed_header_scrolls_with_the_sections_and_can_be_replaced(qapp):
    from PySide6.QtWidgets import QLabel

    feed = SectionFeed()
    feed.resize(900, 600)
    feed.show()
    first, second = QLabel("first"), QLabel("second")
    feed.set_header(first)
    feed.set_sections([("Shelf", [playlist(n) for n in range(4)])], FakeThumbnails())
    assert first.isVisible() and feed._built and feed._built[0].mapTo(feed._content, feed._built[0].rect().topLeft()).y() > 0
    feed.set_header(second)
    QTest.qWait(50)
    assert second.isVisible() and feed._header_slot.count() == 1
    feed.set_header(None)
    assert feed._header_slot.count() == 0
    feed.set_sections([], FakeThumbnails(), empty_message="")
    assert feed._pending == [] and feed._layout.count() == 1


def profile_data():
    return {
        "id": ARTIST, "name": "Band", "subscribers": "42.7 k", "banner": [], "description": "",
        "top_songs": [normalize_track(raw_song(n)) for n in range(1, 6)], "songs_browse_id": "VLOLAKsongs",
        "shuffle_id": "", "radio_id": "",
        "sections": [("Álbumes", [dict(normalize_release(release(1)))]),
                     ("Sencillos y EP", [dict(normalize_release(release(3, "Single")))])],
    }


def test_artist_panel_header_buttons_and_top_songs(qapp):
    panel = ArtistPanel()
    panel.resize(1100, 800)
    panel.show()
    panel.show_profile(profile_data(), FakeThumbnails())
    shuffle, mix, all_songs = QSignalSpy(panel.shuffle_requested), QSignalSpy(panel.mix_requested), QSignalSpy(panel.show_all_requested)
    panel.shuffle_button.click()
    panel.mix_button.click()
    panel.show_all_button.click()
    assert (shuffle.count(), mix.count(), all_songs.count()) == (1, 1, 1)
    assert panel.songs.row_count == 5
    assert "Aleatorio" in panel.shuffle_button.text() and "Mix" in panel.mix_button.text()
    assert len(panel.feed._built) >= 1


def test_artist_panel_without_full_list_hides_show_all(qapp):
    data = profile_data()
    data["songs_browse_id"] = ""
    panel = ArtistPanel()
    panel.resize(1100, 800)
    panel.show()
    panel.show_profile(data, FakeThumbnails())
    from PySide6.QtWidgets import QPushButton

    assert "Mostrar todo" not in [b.text() for b in panel.findChildren(QPushButton)]


def test_artist_panel_relays_song_and_shelf_clicks(qapp):
    panel = ArtistPanel()
    panel.resize(1100, 800)
    panel.move(300, 300)
    panel.show()
    panel.show_profile(profile_data(), FakeThumbnails())
    chosen = QSignalSpy(panel.song_chosen)
    first = panel.songs.findChildren(TrackRow)[0]
    QTest.mouseClick(first, Qt.LeftButton, pos=first.rect().center())
    assert chosen.count() == 1 and chosen.at(0)[0]["videoId"] == "v1"
    playlist_signal = QSignalSpy(panel.add_playlist_clicked)
    first.add_playlist.emit(first.track)
    assert playlist_signal.count() == 1


def test_artist_panel_messages_offer_a_way_back(qapp):
    panel = ArtistPanel()
    panel.resize(900, 600)
    panel.show()
    spy = QSignalSpy(panel.back_requested)
    panel.show_message("No se pudo cargar")
    from PySide6.QtWidgets import QPushButton
    panel.findChildren(QPushButton)[0].click()
    assert spy.count() == 1


def test_artist_panel_full_song_list_page(qapp):
    panel = ArtistPanel()
    panel.resize(1100, 800)
    panel.show()
    tracks = [normalize_track(raw_song(n)) for n in range(1, 41)]
    panel.show_all_songs("Band", tracks, FakeThumbnails())
    assert panel.songs.row_count == FIRST_BATCH
    QTest.qWait(600)
    assert panel.songs.row_count == 40


def test_album_panel_details_tracks_and_actions(qapp):
    album = {"id": "MPREb_3", "title": "Release 3", "kind": "Sencillo", "year": "2025",
             "artists": [{"name": "Band", "id": ARTIST}], "thumbnails": [], "track_count": 2,
             "duration": "8 minutos y 14 segundos",
             "tracks": [normalize_track(raw_song(1)), normalize_track(raw_song(2))],
             "more": [normalize_release(release(9))]}
    panel = AlbumPanel()
    panel.resize(1200, 900)
    panel.move(300, 300)
    panel.show()
    panel.show_album(album, FakeThumbnails())
    from PySide6.QtWidgets import QLabel, QPushButton

    texts = {label.text() for label in panel.findChildren(QLabel)}
    assert {"Release 3", "Sencillo • 2025", "2 canciones • 8 minutos y 14 segundos", "Lanzamientos para ti"} <= texts
    assert panel.tracks.row_count == 2 and panel.findChildren(CardsSection)
    play, shuffle = QSignalSpy(panel.play_requested), QSignalSpy(panel.shuffle_requested)
    panel.play_button.click()
    panel.shuffle_button.click()
    assert (play.count(), shuffle.count()) == (1, 1)
    artist = QSignalSpy(panel.artist_clicked)
    next(b for b in panel.findChildren(QPushButton) if b.text() == "Band").click()
    assert artist.at(0)[0] == ARTIST
    chosen = QSignalSpy(panel.track_chosen)
    second = panel.tracks.findChildren(TrackRow)[1]
    QTest.mouseClick(second, Qt.LeftButton, pos=second.rect().center())
    assert chosen.at(0)[0] == 1


def test_album_panel_without_related_releases_and_with_one_track(qapp):
    from PySide6.QtWidgets import QLabel

    panel = AlbumPanel()
    panel.resize(1200, 700)
    panel.show()
    panel.show_album({"id": "x", "title": "Solo", "kind": "EP", "year": "", "artists": [], "thumbnails": [],
                      "track_count": 1, "duration": "", "tracks": [normalize_track(raw_song(1))], "more": []},
                     FakeThumbnails())
    texts = {label.text() for label in panel.findChildren(QLabel)}
    assert "1 canción" in texts and "Lanzamientos para ti" not in texts


def test_album_panel_hides_the_artist_column_when_it_is_one_artist(qapp):
    from PySide6.QtWidgets import QLabel

    panel = AlbumPanel()
    panel.resize(1200, 700)
    panel.show()
    base = {"id": "x", "title": "T", "kind": "Álbum", "year": "2020", "artists": [{"name": "Band"}],
            "thumbnails": [], "track_count": 2, "duration": "", "more": []}
    solo = [normalize_track(raw_song(1)), normalize_track(raw_song(2))]
    panel.show_album({**base, "tracks": solo}, FakeThumbnails())
    assert "Band" not in {l.text() for l in panel.tracks.findChildren(QLabel)}
    guest = normalize_track({**raw_song(3), "artists": [{"name": "Guest"}]})
    panel.show_album({**base, "tracks": [solo[0], guest]}, FakeThumbnails())
    assert "Guest" in {l.text() for l in panel.tracks.findChildren(QLabel)}


def test_search_artist_card_opens_the_profile_and_offers_shuffle_and_mix(qapp):
    panel = SearchPanel()
    panel.resize(1000, 700)
    panel.move(300, 300)
    panel.show()
    hero = {"resultType": "artist", "artist": "Band", "browseId": ARTIST, "subscribers": "42.7 k", "thumbnails": []}
    panel.show_results({"top_result": hero, "songs": [], "more": []}, FakeThumbnails())
    from ui.components.search_panel import _ArtistHero

    card = panel.findChildren(_ArtistHero)[0]
    opened, shuffled, mixed = QSignalSpy(panel.item_clicked), QSignalSpy(panel.artist_shuffle_requested), QSignalSpy(panel.artist_mix_requested)
    QTest.mouseClick(card, Qt.LeftButton, pos=card.rect().center())
    card.shuffle_button.click()
    card.mix_button.click()
    assert opened.count() == 1 and opened.at(0)[0]["browseId"] == ARTIST
    assert shuffled.count() == 1 and mixed.count() == 1


class ProfileCatalog:
    def __init__(self):
        self.profiles = []
        self.albums = []
        self.playlists = []

    def artist_profile(self, browse_id, on_done, on_error=None):
        self.profiles.append((browse_id, on_done, on_error))

    def album(self, browse_id, on_done, on_error=None):
        self.albums.append((browse_id, on_done, on_error))

    def playlist(self, playlist_id, on_done, on_error=None):
        self.playlists.append((playlist_id, on_done, on_error))


class FakeOpener:
    def __init__(self):
        self.opened, self.shuffled, self.mixed = [], [], []

    def open(self, item):
        self.opened.append(item)

    def shuffle_artist(self, artist_id, name=""):
        self.shuffled.append((artist_id, name))

    def mix_artist(self, artist_id):
        self.mixed.append(artist_id)


def album_data(**over):
    tracks = [normalize_track(raw_song(n)) for n in (1, 2, 3)]
    return {"id": "MPREb_3", "title": "Release 3", "kind": "Sencillo", "year": "2025",
            "artists": [{"name": "Band", "id": ARTIST}], "thumbnails": [], "track_count": 3, "duration": "",
            "tracks": tracks, "more": [], **over}


@pytest.fixture
def nav(rig):
    catalog, opener, navigator = ProfileCatalog(), FakeOpener(), Navigator()
    presenter = rig.keep(ProfilePresenter(rig.window, catalog, rig.playback, opener, navigator, rig.notifier))
    rig.window.show_view("search")
    return rig, presenter, catalog, opener, navigator


def test_artist_request_shows_the_profile_page(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    assert rig.window.current_view == "artist" and rig.window.artist_panel.isVisible()
    assert not rig.window.search_panel.isVisible()
    catalog.profiles[-1][1](profile_data())
    assert rig.window.artist_panel.songs.row_count == 5


def test_a_late_answer_for_a_previous_artist_is_ignored(nav):
    rig, _, catalog, _, navigator = nav
    navigator.artist_requested.emit("UC_first")
    navigator.artist_requested.emit("UC_second")
    catalog.profiles[0][1](profile_data())
    assert rig.window.artist_panel.songs is None
    catalog.profiles[1][1](dict(profile_data(), name="Second"))
    assert rig.window.artist_panel.songs is not None


def test_back_returns_to_the_screen_the_user_came_from(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    catalog.profiles[-1][1](profile_data())
    rig.window.artist_panel.back_requested.emit()
    assert rig.window.current_view == "search" and rig.window.search_panel.isVisible()
    assert presenter._history == [] and presenter._current is None


def test_back_from_an_album_returns_to_the_artist_then_to_the_screen(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    catalog.profiles[-1][1](profile_data())
    navigator.album_requested.emit("MPREb_3")
    assert rig.window.current_view == "album"
    catalog.albums[-1][1](album_data())
    rig.window.album_panel.back_requested.emit()
    assert rig.window.current_view == "artist" and presenter._current == ("artist", ARTIST)
    assert catalog.profiles[-1][0] == ARTIST
    catalog.profiles[-1][1](profile_data())
    rig.window.artist_panel.back_requested.emit()
    assert rig.window.current_view == "search"


def test_choosing_a_main_screen_drops_the_trail(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    navigator.album_requested.emit("MPREb_3")
    rig.window.show_view("home")
    assert presenter._history == [] and presenter._current is None
    navigator.artist_requested.emit(ARTIST)
    assert presenter._history == [("view", "home")]


def test_reopening_the_same_page_does_not_stack_history(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    navigator.artist_requested.emit(ARTIST)
    assert presenter._history == [("view", "search")]


def test_back_with_nothing_behind_goes_home(nav):
    rig, presenter, *_ = nav
    presenter.back()
    assert rig.window.current_view == "home"


def test_show_all_songs_and_back_to_the_profile(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    catalog.profiles[-1][1](profile_data())
    rig.window.artist_panel.show_all_requested.emit()
    assert presenter._current == ("songs", ARTIST)
    catalog.profiles[-1][1](profile_data())
    assert catalog.playlists[-1][0] == "VLOLAKsongs"
    catalog.playlists[-1][1]({"title": "Top songs", "tracks": [normalize_track(raw_song(n)) for n in range(1, 21)]})
    assert rig.window.artist_panel.songs.row_count == 20
    rig.window.artist_panel.back_requested.emit()
    assert presenter._current == ("artist", ARTIST)


def test_empty_songs_list_and_failures_show_a_message_with_a_way_back(nav):
    from PySide6.QtWidgets import QLabel

    rig, presenter, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    catalog.profiles[-1][2](RuntimeError("offline"))
    labels = [l.text() for l in rig.window.artist_panel.findChildren(QLabel)]
    assert any("No se pudo cargar" in t for t in labels)
    navigator.album_requested.emit("MPREb_3")
    catalog.albums[-1][2](RuntimeError("offline"))
    assert any("No se pudo cargar" in l.text() for l in rig.window.album_panel.findChildren(QLabel))
    navigator.album_requested.emit("MPREb_4")
    catalog.albums[-1][1](None)
    assert any("No hay canciones disponibles" in l.text() for l in rig.window.album_panel.findChildren(QLabel))


def test_artist_buttons_delegate_to_the_opener(nav):
    rig, _, catalog, opener, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    catalog.profiles[-1][1](profile_data())
    rig.window.artist_panel.shuffle_requested.emit()
    rig.window.artist_panel.mix_requested.emit()
    assert opener.shuffled == [(ARTIST, "Band")] and opener.mixed == [ARTIST]


def test_artist_buttons_before_the_profile_arrives_do_nothing(nav):
    rig, _, _, opener, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    rig.window.artist_panel.shuffle_requested.emit()
    rig.window.artist_panel.mix_requested.emit()
    assert opener.shuffled == [] and opener.mixed == []


def test_choosing_a_top_song_starts_a_radio(nav):
    rig, _, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    catalog.profiles[-1][1](profile_data())
    rig.window.artist_panel.song_chosen.emit(normalize_track(raw_song(2)))
    assert rig.queue.current["videoId"] == "v2" and rig.streams.requests[-1] == "v2"


def test_shelf_items_go_through_the_opener(nav):
    rig, _, catalog, opener, navigator = nav
    item = {"type": "album", "browseId": "MPREb_1"}
    rig.window.artist_panel.item_clicked.emit(item)
    rig.window.album_panel.item_clicked.emit(item)
    assert opener.opened == [item, item]


def test_album_play_plays_the_whole_album_and_a_track_starts_from_there(nav):
    rig, _, catalog, _, navigator = nav
    navigator.album_requested.emit("MPREb_3")
    catalog.albums[-1][1](album_data())
    rig.window.album_panel.play_requested.emit()
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v1", "v2", "v3"] and rig.queue.current["videoId"] == "v1"
    rig.window.album_panel.track_chosen.emit(2, normalize_track(raw_song(3)))
    assert rig.queue.current["videoId"] == "v3" and len(rig.queue) == 3


def test_album_shuffle_plays_every_track(nav):
    rig, _, catalog, _, navigator = nav
    navigator.album_requested.emit("MPREb_3")
    catalog.albums[-1][1](album_data())
    rig.window.album_panel.shuffle_requested.emit()
    assert sorted(s["videoId"] for s in rig.queue.snapshot()) == ["v1", "v2", "v3"]


def test_album_artist_link_opens_that_artist(nav):
    rig, presenter, catalog, _, navigator = nav
    navigator.album_requested.emit("MPREb_3")
    catalog.albums[-1][1](album_data())
    rig.window.album_panel.artist_clicked.emit(ARTIST)
    assert presenter._current == ("artist", ARTIST) and rig.window.current_view == "artist"
    assert presenter._history == [("view", "search"), ("album", "MPREb_3")]


def test_now_playing_hides_the_profile_pages(nav):
    rig, _, catalog, _, navigator = nav
    navigator.artist_requested.emit(ARTIST)
    rig.window.toggle_now_playing()
    assert rig.window.now_playing_panel.isVisible() and not rig.window.artist_panel.isVisible()
    rig.window.toggle_now_playing()
    assert rig.window.artist_panel.isVisible() and not rig.window.now_playing_panel.isVisible()


def test_main_window_announces_the_page_it_shows(rig):
    seen = QSignalSpy(rig.window.view_shown)
    rig.window.show_view("album")
    rig.window.show_view("home")
    assert [seen.at(i)[0] for i in range(seen.count())] == ["album", "home"]
    assert rig.window.album_panel.isHidden() and rig.window.home_panel.isVisible()


def test_playlist_requests_from_the_new_pages_reach_the_window_signal(rig):
    spy = QSignalSpy(rig.window.save_to_playlist_requested)
    rig.window.artist_panel.add_playlist_clicked.emit(song(1))
    rig.window.album_panel.add_playlist_clicked.emit(song(2))
    assert spy.count() == 2
