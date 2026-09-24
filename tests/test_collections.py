import pytest
from PySide6.QtCore import QEvent, QPoint, QTimer, Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QPushButton

from domain.models import normalize_track
from domain.play_queue import PlayQueue
from infra.concurrency import TaskRunner
from presenters.collection_presenter import CollectionPresenter
from presenters.playlist_presenter import PlaylistPresenter
from presenters.profile_presenter import ProfilePresenter
from services.catalog_service import CatalogService
from services.collection_actions import CollectionActions
from services.navigation import Navigator
from tests.test_presenters import Rig
from tests.test_profiles import ProfileCatalog, FakeOpener, ProfileGateway, ask, raw_song
from tests.test_ui import FakeThumbnails, choose_from_open_menu, song
from ui.components.album_panel import AlbumPanel
from ui.components.section_feed import CardsSection, CompactSongItem, HomeCard, is_collection_card
from ui.components.track_actions import (
    COLLECTION_ACTIONS, SONG_ACTIONS, ActionsButton, CollectionActionsButton, TrackActionsButton,
)
from ui.components.track_list import TrackRow


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.window.close()


def tracks(n=3):
    return [normalize_track(raw_song(i)) for i in range(1, n + 1)]


PLAYLIST = {"type": "playlist", "playlistId": "PL1", "title": "Mix", "thumbnails": []}
ALBUM = {"type": "album", "browseId": "MPREb_1", "title": "Disc", "thumbnails": [], "subtitle": "Álbum • 2020"}


def hovered_card(item, qapp=None):
    card = HomeCard(item, FakeThumbnails())
    card.move(400, 400)
    card.show()
    QApplication.sendEvent(card, QEvent(QEvent.Enter))
    return card


def test_queue_appends_and_inserts_blocks_in_order():
    queue = PlayQueue()
    assert queue.append_many(tracks(2)) is True and queue.current["videoId"] == "v1"
    assert queue.append_many([normalize_track(raw_song(9))]) is False
    assert queue.insert_next_many([normalize_track(raw_song(7)), normalize_track(raw_song(8))]) is False
    assert [s["videoId"] for s in queue.snapshot()] == ["v1", "v7", "v8", "v2", "v9"]
    assert queue.append_many([]) is False and queue.insert_next_many([]) is False
    empty = PlayQueue()
    assert empty.insert_next_many(tracks(2)) is True and empty.current["videoId"] == "v1"


def test_enqueue_blocks_start_playing_only_when_nothing_was(rig):
    rig.playback.enqueue_next_many(tracks(3))
    assert rig.queue.current["videoId"] == "v1" and rig.streams.requests[-1] == "v1"
    rig.streams.requests.clear()
    rig.playback.enqueue_next_many([normalize_track(raw_song(8)), normalize_track(raw_song(9))])
    rig.playback.enqueue_last_many([normalize_track(raw_song(10)), {"title": "no id"}])
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v1", "v8", "v9", "v2", "v3", "v10"]
    assert rig.queue.current["videoId"] == "v1" and "v8" not in rig.streams.requests
    rig.playback.enqueue_next_many([])
    rig.playback.enqueue_last_many([{"title": "no id"}])
    assert len(rig.queue) == 6


def test_enqueue_last_block_plays_an_empty_queue(rig):
    rig.playback.enqueue_last_many(tracks(2))
    assert rig.queue.current["videoId"] == "v1" and rig.streams.requests[-1] == "v1"


class PlaylistGateway(ProfileGateway):
    def __init__(self):
        super().__init__()
        self.page_calls = 0
        self.page = {"title": "Replay", "author": {"name": "YouTube Music", "id": "UCyt"}, "year": "2026",
                     "description": "Hits", "thumbnails": [{"url": "c"}], "trackCount": 3,
                     "duration": "4 horas", "tracks": [raw_song(i) for i in (1, 2, 3)]}
        self.page_error = None

    def get_playlist_page(self, playlist_id):
        self.page_calls += 1
        if self.page_error:
            raise self.page_error
        return self.page


@pytest.fixture
def pages(qapp):
    gateway = PlaylistGateway()
    runner = TaskRunner("pages", 3)
    yield CatalogService(gateway, runner), gateway
    runner.shutdown()


def test_playlist_page_data_and_cache(pages, wait_until):
    catalog, gateway = pages
    page = ask(wait_until, lambda done: catalog.playlist_details("PL1", done))
    assert (page["title"], page["kind"], page["year"], page["author"], page["author_id"]) == \
        ("Replay", "Playlist", "2026", "YouTube Music", "UCyt")
    assert page["description"] == "Hits" and page["duration"] == "4 horas" and page["track_count"] == 3
    assert [t["videoId"] for t in page["tracks"]] == ["v1", "v2", "v3"]
    again = []
    catalog.playlist_details("PL1", again.append)
    assert again == [page] and gateway.page_calls == 1


def test_playlist_page_owner_shapes(pages, wait_until):
    catalog, gateway = pages
    gateway.page = dict(gateway.page, author=[{"name": "A", "id": "UC1"}, {"name": "B"}])
    assert ask(wait_until, lambda done: catalog.playlist_details("PLa", done))["author"] == "A"
    gateway.page = dict(gateway.page, author="Plain name")
    page = ask(wait_until, lambda done: catalog.playlist_details("PLb", done))
    assert page["author"] == "Plain name" and page["author_id"] == ""
    gateway.page = {"tracks": [raw_song(1)]}
    page = ask(wait_until, lambda done: catalog.playlist_details("PLc", done))
    assert page["title"] == "Mix" and page["author"] == "" and page["track_count"] == 1
    assert page["thumbnails"] == normalize_track(raw_song(1))["thumbnails"]


def test_generated_mixes_fall_back_to_their_queue(pages, wait_until):
    catalog, gateway = pages
    gateway.page_error = RuntimeError("not a browsable playlist")
    page = ask(wait_until, lambda done: catalog.playlist_details("RDAMPL", done))
    assert [t["videoId"] for t in page["tracks"]] == ["m0", "m1", "m2"] and page["title"] == "Mix"


def test_playlist_without_tracks_is_none(pages, wait_until):
    catalog, gateway = pages
    gateway.page = {"title": "Empty", "tracks": []}
    gateway.get_watch_playlist_for = lambda playlist_id, limit: {"tracks": []}
    assert ask(wait_until, lambda done: catalog.playlist_details("PLe", done)) is None


def test_playlist_page_errors_when_nothing_at_all_answers(pages, wait_until):
    catalog, gateway = pages
    gateway.page_error = RuntimeError("down")
    gateway.mix_fails = True
    errors = []
    catalog.playlist_details("PLz", lambda page: errors.append("done"), errors.append)
    assert wait_until(lambda: errors) and isinstance(errors[0], RuntimeError)


def test_library_adds_many_songs_at_once(qapp, tmp_path, wait_until):
    from infra.playlist_repository import LocalPlaylistRepository
    from services.library_service import LibraryService

    gateway = PlaylistGateway()
    runner = TaskRunner("lib", 2)
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    service = LibraryService(gateway, repo, CatalogService(gateway, runner), runner)
    pid = repo.add("Mine", [], "user_created")
    out = []
    entry = service.local_summaries()[0]
    service.add_to_playlist(entry, tracks(3), out.append)
    service.add_to_playlist(entry, tracks(3), out.append)
    assert out == ["added", "duplicate"] and [t["videoId"] for t in repo.get(pid)["tracks"]] == ["v1", "v2", "v3"]
    calls = []
    gateway.add_playlist_items = lambda playlist_id, ids: calls.append((playlist_id, ids)) or True
    service.add_to_playlist({"playlistId": "PLx", "source": "ytmusic"}, tracks(2) + [{"title": "no id"}], out.append)
    assert wait_until(lambda: len(out) == 3) and calls == [("PLx", ["v1", "v2"])]
    runner.shutdown()


class ActionCatalog:
    def __init__(self):
        self.albums, self.playlists = [], []
        self.data = {"title": "T", "tracks": tracks(3)}
        self.error = None

    def _answer(self, on_done, on_error):
        if self.error:
            on_error(self.error)
        else:
            on_done(self.data)

    def album(self, browse_id, on_done, on_error=None):
        self.albums.append(browse_id)
        self._answer(on_done, on_error)

    def playlist_details(self, playlist_id, on_done, on_error=None):
        self.playlists.append(playlist_id)
        self._answer(on_done, on_error)


@pytest.fixture
def actions(rig):
    catalog = ActionCatalog()
    return CollectionActions(catalog, rig.playback, rig.notifier), catalog, rig


def test_items_are_routed_to_albums_or_playlists(actions):
    service, catalog, _ = actions
    got = []
    service.tracks_of(ALBUM, got.append)
    service.tracks_of(PLAYLIST, got.append)
    service.tracks_of({"browseId": "VLPL2", "type": "album"}, got.append)
    assert catalog.albums == ["MPREb_1"] and catalog.playlists == ["PL1", "PL2"] and len(got) == 3


def test_play_replaces_the_queue_and_announces(actions):
    service, _, rig = actions
    service.perform("play", PLAYLIST)
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v1", "v2", "v3"] and rig.queue.current["videoId"] == "v1"
    assert rig.notifier.messages[0] == ("info", "Abriendo «Mix»…")


def test_shuffle_plays_every_track_and_announces(actions):
    service, _, rig = actions
    service.perform("shuffle", ALBUM)
    assert sorted(s["videoId"] for s in rig.queue.snapshot()) == ["v1", "v2", "v3"]
    assert rig.notifier.messages[0] == ("info", "Mezclando «Disc»…")


def test_mix_starts_a_radio_from_one_of_the_tracks(actions):
    service, _, rig = actions
    service.perform("mix", PLAYLIST)
    assert rig.queue.current["videoId"] in ("v1", "v2", "v3") and len(rig.queue) == 1


def test_next_and_queue_add_the_whole_collection(actions):
    service, _, rig = actions
    rig.queue.replace([song(1)], 0)
    service.perform("next", PLAYLIST)
    service.perform("queue", ALBUM)
    ids = [s["videoId"] for s in rig.queue.snapshot()]
    assert ids == ["v1", "v1", "v2", "v3", "v1", "v2", "v3"]
    assert rig.notifier.messages == []


def test_empty_and_failed_collections_tell_the_user(actions):
    service, catalog, rig = actions
    catalog.data = {"tracks": []}
    service.perform("play", PLAYLIST)
    assert rig.notifier.messages[-1][0] == "warning" and len(rig.queue) == 0
    catalog.error = RuntimeError("offline")
    service.perform("queue", PLAYLIST)
    assert rig.notifier.messages[-1][0] == "error"
    service.perform("bogus", PLAYLIST)
    assert len(rig.queue) == 0


def test_share_links():
    service = CollectionActions(None, None, None)
    assert service.share_url(PLAYLIST) == "https://music.youtube.com/playlist?list=PL1"
    assert service.share_url({"browseId": "VLPL7"}) == "https://music.youtube.com/playlist?list=PL7"
    assert service.share_url(ALBUM) == "https://music.youtube.com/browse/MPREb_1"


def test_collection_menu_actions_reach_the_service_and_the_clipboard(rig, monkeypatch):
    catalog = ActionCatalog()
    service = CollectionActions(catalog, rig.playback, rig.notifier)
    saved = []
    playlists = rig.keep(PlaylistPresenter(rig.window, rig.catalog, rig.library, rig.playback, rig.auth, rig.notifier))
    monkeypatch.setattr(playlists, "save_tracks", lambda songs: saved.append([s["videoId"] for s in songs]))
    rig.keep(CollectionPresenter(rig.window, service, playlists, rig.notifier))
    copied = []
    monkeypatch.setattr(rig.window, "copy_text", copied.append)

    rig.window.collection_action_requested.emit("play", PLAYLIST)
    assert rig.queue.current["videoId"] == "v1"
    rig.window.collection_action_requested.emit("playlist", ALBUM)
    assert saved == [["v1", "v2", "v3"]]
    rig.window.collection_action_requested.emit("share", PLAYLIST)
    assert copied == ["https://music.youtube.com/playlist?list=PL1"]
    assert rig.notifier.messages[-1] == ("info", "Enlace copiado al portapapeles.")


def test_window_copies_text_to_the_clipboard(rig):
    rig.window.copy_text("https://example.com")
    assert QApplication.clipboard().text() == "https://example.com"


def test_collection_requests_from_every_screen_reach_the_window_signal(rig):
    spy = QSignalSpy(rig.window.collection_action_requested)
    w = rig.window
    for signal in (w.home_panel.collection_action_requested, w.explore_panel.collection_action_requested,
                   w.artist_panel.collection_action_requested, w.album_panel.collection_action_requested,
                   w.side_panel.similar_collection_action):
        signal.emit("play", PLAYLIST)
    assert spy.count() == 5


def test_saving_several_songs_reports_a_count(rig, monkeypatch):
    presenter = rig.keep(PlaylistPresenter(rig.window, rig.catalog, rig.library, rig.playback, rig.auth, rig.notifier))
    target = {"playlistId": "local_1", "title": "Mine", "source": "local"}
    monkeypatch.setattr(rig.window, "choose_playlist", lambda t: ("existing", target))
    presenter.save_tracks(tracks(3))
    rig.library.target_requests[-1]({"recent": [], "all": [target]})
    assert rig.library.added == [("local_1", ["v1", "v2", "v3"])]
    assert rig.notifier.messages[-1] == ("info", "3 canciones agregadas a «Mine».")
    rig.library.add_outcome = "duplicate"
    presenter.save_tracks(tracks(3))
    rig.library.target_requests[-1]({"recent": [], "all": [target]})
    assert rig.notifier.messages[-1] == ("info", "Esas canciones ya estaban en «Mine».")
    monkeypatch.setattr(rig.window, "choose_playlist", lambda t: ("new", "Gym"))
    presenter.save_tracks(tracks(3))
    rig.library.target_requests[-1]({"recent": [], "all": []})
    assert rig.library.saved[-1] == ("Gym", ["v1", "v2", "v3"], False)
    assert rig.notifier.messages[-1] == ("info", "3 canciones agregadas a la nueva playlist «Gym».")
    presenter.save_tracks([{"title": "no id"}])
    assert rig.notifier.messages[-1][0] == "warning"


def test_only_playlists_and_albums_are_collection_cards():
    assert is_collection_card(PLAYLIST) and is_collection_card(ALBUM)
    assert not is_collection_card({"type": "artist", "browseId": "UC1"})
    assert not is_collection_card({"type": "album", "browseId": "UC1"})
    assert not is_collection_card({"type": "song", "videoId": "v"})
    assert not is_collection_card({"type": "video", "videoId": "v"})


def test_playlist_card_shows_play_and_menu_buttons_only_while_hovered(qapp):
    card = HomeCard(PLAYLIST, FakeThumbnails())
    card.move(400, 400)
    card.show()
    assert card._overlay is not None and not card._overlay.isVisible()
    QApplication.sendEvent(card, QEvent(QEvent.Enter))
    assert card._overlay.isVisible() and card._overlay.play_button.isVisible() and card._overlay.menu_button.isVisible()
    QApplication.sendEvent(card, QEvent(QEvent.Leave))
    assert not card._overlay.isVisible()


def test_artist_and_song_cards_have_no_overlay(qapp):
    assert HomeCard({"type": "artist", "browseId": "UC1", "title": "A"}, FakeThumbnails())._overlay is None
    assert HomeCard({"type": "video", "videoId": "v", "title": "V"}, FakeThumbnails())._overlay is None


def test_play_button_reports_play_without_opening_the_card(qapp):
    card = hovered_card(PLAYLIST)
    actions, opened = QSignalSpy(card.action_requested), QSignalSpy(card.chosen)
    card._overlay.play_button.click()
    assert actions.count() == 1 and actions.at(0) == ["play", PLAYLIST] and opened.count() == 0


def test_clicking_the_cover_still_opens_the_card(qapp):
    card = hovered_card(PLAYLIST)
    opened = QSignalSpy(card.chosen)
    QTest.mouseClick(card._overlay, Qt.LeftButton, pos=QPoint(20, 20))
    assert opened.count() == 1 and opened.at(0)[0] == PLAYLIST


@pytest.mark.parametrize("index, key", list(enumerate(k for k, _, _ in COLLECTION_ACTIONS)))
def test_card_menu_offers_every_collection_action(qapp, index, key):
    card = hovered_card(PLAYLIST)
    spy = QSignalSpy(card.action_requested)
    choose_from_open_menu(index)
    card._overlay.menu_button.click()
    assert spy.count() == 1 and spy.at(0) == [key, PLAYLIST]


def test_card_overlay_stays_while_its_menu_is_open_then_hides(qapp):
    card = hovered_card(ALBUM)
    states = []

    def leave_and_check():
        QApplication.sendEvent(card, QEvent(QEvent.Leave))
        states.append(card._overlay.isVisible())
        next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()).close()

    QTimer.singleShot(50, leave_and_check)
    card._overlay.menu_button.click()
    assert states == [True] and not card._overlay.isVisible()


def test_right_clicking_a_card_opens_its_menu(qapp):
    card = hovered_card(PLAYLIST)
    spy = QSignalSpy(card.action_requested)
    choose_from_open_menu(3)
    card.context_requested.emit(card.mapToGlobal(QPoint(50, 50)))
    assert spy.at(0) == ["queue", PLAYLIST]


def test_card_menu_labels():
    labels = [label for _, label, _ in COLLECTION_ACTIONS]
    assert labels == ["Reproducir aleatoriamente", "Comenzar mix", "Reproducir a continuación",
                      "Agregar a la cola", "Guardar en una playlist", "Compartir"]


def open_menu_texts(trigger):
    seen = []

    def read():
        menu = next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible())
        seen.extend(a.text() for a in menu.actions())
        menu.close()

    QTimer.singleShot(50, read)
    trigger()
    return seen


def test_context_request_signal_carries_the_global_position(qapp):
    from ui.components.clickable import ClickableWidget

    widget = ClickableWidget()
    widget.resize(100, 40)
    widget.move(400, 400)
    widget.show()
    spy = QSignalSpy(widget.context_requested)
    QApplication.sendEvent(widget, QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(5, 5), QPoint(405, 405)))
    assert spy.count() == 1 and spy.at(0)[0] == QPoint(405, 405)


@pytest.mark.parametrize("make", [
    lambda: CompactSongItem(song(1), FakeThumbnails()),
    lambda: TrackRow(normalize_track(raw_song(1)), FakeThumbnails()),
])
def test_song_rows_open_their_menu_on_right_click(qapp, make):
    row = make()
    row.resize(600, 60)
    row.move(400, 400)
    row.show()
    texts = open_menu_texts(lambda: row.context_requested.emit(row.mapToGlobal(QPoint(30, 30))))
    assert texts == [label for _, label, _ in SONG_ACTIONS]


def test_search_and_library_rows_open_their_menu_on_right_click(qapp):
    from ui.components.library_browser import SongRow
    from ui.components.search_panel import _ResultRow

    for row in (SongRow(song(1), FakeThumbnails()), _ResultRow(dict(song(1), resultType="song"), FakeThumbnails())):
        row.resize(600, 60)
        row.move(400, 400)
        row.show()
        texts = open_menu_texts(lambda: row.context_requested.emit(row.mapToGlobal(QPoint(30, 30))))
        assert texts == [label for _, label, _ in SONG_ACTIONS]


def test_rows_of_things_that_cannot_be_queued_ignore_right_click(qapp):
    from ui.components.search_panel import _ResultRow

    row = _ResultRow({"resultType": "artist", "title": "A", "browseId": "UC1"}, FakeThumbnails())
    row.resize(600, 60)
    row.move(400, 400)
    row.show()
    assert row._actions.isHidden()
    row.context_requested.emit(row.mapToGlobal(QPoint(30, 30)))
    assert not row._actions.menu_is_open


def test_right_click_choice_reaches_the_row_signals(qapp):
    row = CompactSongItem(song(1), FakeThumbnails())
    row.resize(600, 60)
    row.move(400, 400)
    row.show()
    spy = QSignalSpy(row.add_playlist)
    choose_from_open_menu(2)
    row.context_requested.emit(row.mapToGlobal(QPoint(30, 30)))
    assert spy.count() == 1 and spy.at(0)[0]["videoId"] == "v1"


def test_actions_button_variants(qapp):
    songs, cards = TrackActionsButton(), CollectionActionsButton()
    assert songs._entries == SONG_ACTIONS and cards._entries == COLLECTION_ACTIONS
    assert cards.isEnabled() and not songs.isEnabled()
    cards.set_revealed(False)
    assert cards.isEnabled()
    generic = ActionsButton([("a", "Alpha", "fa5s.play")])
    generic.show()
    chosen = QSignalSpy(generic.action_chosen)
    generic.set_revealed(True)
    choose_from_open_menu(0)
    generic.click()
    assert chosen.at(0) == ["a"]


def test_a_menu_cannot_be_opened_twice_at_once(qapp):
    button = ActionsButton([("a", "Alpha", "fa5s.play")])
    button.show()
    button.set_revealed(True)

    nested = []

    def probe():
        button.show_menu()
        nested.append(len([w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()]))
        next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()).close()

    QTimer.singleShot(50, probe)
    button.click()
    assert nested == [1]


def page_data(**over):
    return {"id": "PL1", "title": "Replay de Japón", "kind": "Playlist", "year": "2026", "author": "YouTube Music",
            "author_id": "", "description": "Disfruta los hits " * 30, "thumbnails": [], "track_count": 3,
            "duration": "4 horas y 39 minutos", "tracks": tracks(3), **over}


def test_playlist_panel_details_rows_and_menu(qapp):
    panel = AlbumPanel()
    panel.resize(1300, 900)
    panel.move(300, 300)
    panel.show()
    panel.show_playlist(page_data(), FakeThumbnails())
    texts = [label.text() for label in panel.findChildren(QLabel)]
    assert "Replay de Japón" in texts and "Playlist • 2026" in texts and "3 canciones • 4 horas y 39 minutos" in texts
    description = next(t for t in texts if t.startswith("Disfruta"))
    assert description.endswith("…") and len(description) <= 224
    assert "YouTube Music" in [b.text() for b in panel.findChildren(QPushButton)]
    rows = panel.tracks.findChildren(TrackRow)
    assert len(rows) == 3
    row_texts = {label.text() for label in rows[0].findChildren(QLabel)}
    assert "1" not in row_texts and "Song 1" in row_texts and "Band" in row_texts
    spy = QSignalSpy(panel.collection_action_requested)
    choose_from_open_menu(4)
    panel.menu_button.click()
    assert spy.at(0)[0] == "playlist" and spy.at(0)[1]["playlistId"] == "PL1" and spy.at(0)[1]["type"] == "playlist"


def test_album_panel_menu_reports_the_album(qapp):
    panel = AlbumPanel()
    panel.resize(1300, 900)
    panel.move(300, 300)
    panel.show()
    panel.show_album({"id": "MPREb_1", "title": "Disc", "kind": "Álbum", "year": "2020", "artists": [], "thumbnails": [],
                      "track_count": 3, "duration": "", "tracks": tracks(3), "more": []}, FakeThumbnails())
    spy = QSignalSpy(panel.collection_action_requested)
    choose_from_open_menu(5)
    panel.menu_button.click()
    assert spy.at(0)[0] == "share" and spy.at(0)[1] == {"type": "album", "browseId": "MPREb_1", "title": "Disc"}


def test_playlist_owner_links_to_a_channel_only_when_it_has_one(qapp):
    panel = AlbumPanel()
    panel.resize(1300, 900)
    panel.show()
    spy = QSignalSpy(panel.artist_clicked)
    panel.show_playlist(page_data(author="Some Artist", author_id="UC_owner"), FakeThumbnails())
    next(b for b in panel.findChildren(QPushButton) if b.text() == "Some Artist").click()
    assert spy.at(0)[0] == "UC_owner"
    panel.show_playlist(page_data(author="YouTube Music", author_id=""), FakeThumbnails())
    owner = next(b for b in panel.findChildren(QPushButton) if b.text() == "YouTube Music")
    owner.click()
    assert spy.count() == 1


def test_playlist_panel_without_owner_or_description(qapp):
    panel = AlbumPanel()
    panel.resize(1300, 900)
    panel.show()
    panel.show_playlist(page_data(author="", description="", year=""), FakeThumbnails())
    texts = [label.text() for label in panel.findChildren(QLabel)]
    assert "Playlist" in texts and not any(t.startswith("Disfruta") for t in texts)


def test_album_more_releases_cards_have_the_overlay(qapp):
    panel = AlbumPanel()
    panel.resize(1300, 900)
    panel.move(300, 300)
    panel.show()
    more = [dict(ALBUM, browseId=f"MPREb_{n}") for n in range(3)]
    panel.show_album({"id": "x", "title": "T", "kind": "Álbum", "year": "", "artists": [], "thumbnails": [],
                      "track_count": 1, "duration": "", "tracks": tracks(1), "more": more}, FakeThumbnails())
    spy = QSignalSpy(panel.collection_action_requested)
    section = panel.findChildren(CardsSection)[0]
    card = section.findChildren(HomeCard)[0]
    card._overlay.play_button.click()
    assert spy.count() == 1 and spy.at(0)[0] == "play"


class PageCatalog(ProfileCatalog):
    def __init__(self):
        super().__init__()
        self.details = []

    def playlist_details(self, playlist_id, on_done, on_error=None):
        self.details.append((playlist_id, on_done, on_error))


@pytest.fixture
def nav(rig):
    catalog, opener, navigator = PageCatalog(), FakeOpener(), Navigator()
    presenter = rig.keep(ProfilePresenter(rig.window, catalog, rig.playback, opener, navigator, rig.notifier))
    rig.window.show_view("home")
    return rig, presenter, catalog, navigator


def test_a_playlist_request_shows_its_page(nav):
    rig, presenter, catalog, navigator = nav
    navigator.playlist_requested.emit("PL1")
    assert rig.window.current_view == "album" and presenter._history == [("view", "home")]
    catalog.details[-1][1](page_data())
    assert rig.window.album_panel.tracks.row_count == 3
    assert "Replay de Japón" in [l.text() for l in rig.window.album_panel.findChildren(QLabel)]


def test_choosing_a_playlist_track_plays_from_there(nav):
    rig, _, catalog, navigator = nav
    navigator.playlist_requested.emit("PL1")
    catalog.details[-1][1](page_data())
    rig.window.album_panel.track_chosen.emit(1, tracks(3)[1])
    assert rig.queue.current["videoId"] == "v2" and len(rig.queue) == 3
    rig.window.album_panel.play_requested.emit()
    assert rig.queue.current["videoId"] == "v1"


def test_playlist_page_back_and_failures(nav):
    rig, presenter, catalog, navigator = nav
    navigator.playlist_requested.emit("PL1")
    catalog.details[-1][2](RuntimeError("offline"))
    assert any("No se pudo cargar" in l.text() for l in rig.window.album_panel.findChildren(QLabel))
    rig.window.album_panel.back_requested.emit()
    assert rig.window.current_view == "home"
    navigator.playlist_requested.emit("PL2")
    catalog.details[-1][1](None)
    assert any("No hay canciones disponibles" in l.text() for l in rig.window.album_panel.findChildren(QLabel))


def test_a_late_playlist_answer_is_ignored(nav):
    rig, _, catalog, navigator = nav
    navigator.playlist_requested.emit("PL1")
    navigator.playlist_requested.emit("PL2")
    catalog.details[0][1](page_data(title="First"))
    assert rig.window.album_panel.tracks is None
    catalog.details[1][1](page_data(title="Second"))
    assert rig.window.album_panel.tracks.row_count == 3
