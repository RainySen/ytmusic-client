import json

import pytest
from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QPushButton, QSystemTrayIcon

from domain.models import normalize_track
from domain.play_queue import PlayQueue
from domain.settings import Settings
from domain.volume import gain
from infra.concurrency import TaskRunner
from presenters.player_presenter import PlayerPresenter, album_of, artist_id_of
from presenters.search_presenter import SearchPresenter
from services.library_service import LibraryService
from services.navigation import Navigator
from services.playback_service import PlaybackService
from services.search_history_service import SearchHistoryService
from tests.fakes import FakeAudio, FakeCatalog, FakeNotifier, FakeStreams
from tests.test_presenters import Rig
from ui.components.jump_slider import JumpSlider
from ui.components.link_label import LinkLabel
from ui.components.queue_widgets import ImprovedQueueItem
from ui.components.track_list import _cells
from ui.settings_dialog import SettingsDialog


@pytest.fixture(autouse=True)
def tray_present(monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


class Thumbs:
    def request(self, url, callback):
        pass


def song(n=1, **extra):
    return {"videoId": f"v{n}", "title": f"Titulo {n}", "artists": [{"name": "Artista", "id": "UC1"}], **extra}


def test_volume_maps_one_to_one_and_only_clamps_out_of_range_values():
    assert gain(0) == 0 and gain(100) == 100 and gain(50) == 50 and gain(30) == 30
    assert gain(-5) == 0 and gain(500) == 100
    assert [gain(v) for v in range(0, 101, 10)] == list(range(0, 101, 10))


def test_jump_slider_moves_to_the_clicked_point_and_reports_it(qapp):
    slider = JumpSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.resize(200, 24)
    slider.show()
    moved = []
    slider.sliderMoved.connect(moved.append)
    QTest.mouseClick(slider, Qt.LeftButton, pos=QPoint(150, 12))
    assert 65 <= slider.value() <= 85 and moved and moved[0] == slider.value()
    QTest.mouseClick(slider, Qt.LeftButton, pos=QPoint(20, 12))
    assert slider.value() <= 15
    slider.close()


def test_progress_bar_click_seeks(rig):
    seeks = []
    rig.window.seek_requested.connect(seeks.append)
    slider = rig.window.player_panel.progress_slider
    rig.window.player_panel.show()
    QTest.mouseClick(slider, Qt.LeftButton, pos=QPoint(slider.width() // 2, slider.height() // 2))
    assert seeks and 0.4 <= seeks[-1] <= 0.6


def test_mute_button_silences_and_restores_the_previous_volume(rig):
    panel = rig.window.player_panel
    panel.volume_slider.setValue(70)
    volumes = []
    rig.window.volume_changed.connect(volumes.append)
    panel.mute_button.click()
    assert panel.volume_slider.value() == 0 and panel.volume_label.text() == "0%"
    assert panel.mute_button.toolTip() == "Activar sonido"
    panel.mute_button.click()
    assert panel.volume_slider.value() == 70 and volumes == [0, 70] and panel.mute_button.toolTip() == "Silenciar"
    panel.volume_slider.setValue(0)
    panel.mute_button.click()
    assert panel.volume_slider.value() == 70
    panel.volume_slider.setValue(0)
    panel._before_mute = 0
    panel.toggle_mute()
    assert panel.volume_slider.value() == 50


def test_volume_label_and_tooltip_follow_the_slider(rig):
    panel = rig.window.player_panel
    panel.volume_slider.setValue(35)
    assert panel.volume_label.text() == "35%" and panel.volume_slider.toolTip() == "Volumen 35%"


def test_clicking_the_bar_opens_the_player_but_buttons_do_not_double_fire(rig):
    panel = rig.window.player_panel
    panel.show()
    opened = QSignalSpy(panel.expand_clicked)
    QTest.mouseClick(panel, Qt.LeftButton, pos=QPoint(panel.width() // 2, 4))
    assert opened.count() == 1
    QTest.mouseClick(panel.time_label, Qt.LeftButton)
    assert opened.count() == 2
    plays = QSignalSpy(rig.window.play_pause_clicked)
    panel.play_button.click()
    assert plays.count() == 1 and opened.count() == 2
    QTest.mouseClick(panel, Qt.RightButton, pos=QPoint(10, 10))
    assert opened.count() == 2
    assert rig.window.now_playing_panel.isHidden()


def test_clicking_the_bar_toggles_the_expanded_player_in_the_window(rig):
    rig.window.player_panel.show()
    QTest.mouseClick(rig.window.player_panel, Qt.LeftButton, pos=QPoint(rig.window.player_panel.width() // 2, 4))
    assert rig.window.now_playing_panel.isVisible()
    QTest.mouseClick(rig.window.player_panel, Qt.LeftButton, pos=QPoint(rig.window.player_panel.width() // 2, 4))
    assert not rig.window.now_playing_panel.isVisible()


def test_right_click_menu_offers_the_quick_controls_and_they_work(rig):
    panel = rig.window.player_panel
    calls = []
    for name in ("play_pause_clicked", "next_clicked", "previous_clicked", "shuffle_clicked", "loop_clicked"):
        getattr(rig.window, name).connect(lambda n=name: calls.append(n))
    menu = panel.build_menu()
    labels = [a.text() for a in menu.actions() if a.text()]
    assert labels == ["Reproducir", "Anterior", "Siguiente", "Aleatorio", "Cambiar repetición", "Silenciar",
                      "Abrir el reproductor"]
    for action in menu.actions():
        if action.text() in ("Reproducir", "Anterior", "Siguiente", "Aleatorio", "Cambiar repetición"):
            action.trigger()
    assert calls == ["play_pause_clicked", "previous_clicked", "next_clicked", "shuffle_clicked", "loop_clicked"]
    volume_before = panel.volume_slider.value()
    next(a for a in menu.actions() if a.text() == "Silenciar").trigger()
    assert panel.volume_slider.value() == 0
    opened = QSignalSpy(panel.expand_clicked)
    next(a for a in menu.actions() if a.text() == "Abrir el reproductor").trigger()
    assert opened.count() == 1
    rig.window.set_playing(True)
    panel.volume_slider.setValue(volume_before)
    labels = [a.text() for a in panel.build_menu().actions() if a.text()]
    assert labels[0] == "Pausar" and labels[5] == "Silenciar"
    panel.volume_slider.setValue(0)
    assert "Activar sonido" in [a.text() for a in panel.build_menu().actions()]
    assert "Cerrar el reproductor" in [a.text() for a in panel.build_menu().actions()]


def test_context_menu_event_opens_the_menu(rig, monkeypatch):
    from PySide6.QtGui import QContextMenuEvent
    from ui.components.player_panel import PlayerPanel

    shown = []
    monkeypatch.setattr(PlayerPanel, "_show_menu", lambda _self, menu, _pos: shown.append([a.text() for a in menu.actions()]))
    panel = rig.window.player_panel
    panel.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(5, 5), QPoint(5, 5)))
    assert shown and "Silenciar" in shown[0]


def test_link_label_emits_only_when_linked(qapp):
    label = LinkLabel("Artista")
    clicks = QSignalSpy(label.clicked)
    QTest.mouseClick(label, Qt.LeftButton)
    assert clicks.count() == 0 and not label.linked
    label.set_linked(True)
    QTest.mouseClick(label, Qt.LeftButton)
    QTest.mouseClick(label, Qt.RightButton)
    assert clicks.count() == 1 and label.cursor().shape() == Qt.PointingHandCursor
    QApplication.sendEvent(label, QEvent(QEvent.Enter))
    assert "underline" in label.styleSheet()
    QApplication.sendEvent(label, QEvent(QEvent.Leave))
    assert "underline" not in label.styleSheet()
    label.set_linked(False)
    assert label.cursor().shape() == Qt.ArrowCursor


def test_queue_row_click_plays_that_song_but_buttons_and_drag_handle_do_not(qapp):
    item = ImprovedQueueItem(song(1), 3, False, Thumbs())
    item.resize(360, 56)
    item.show()
    played = []
    item.play_clicked.connect(played.append)
    QTest.mouseClick(item, Qt.LeftButton, pos=QPoint(200, 28))
    assert played == [3]
    QTest.mouseClick(item, Qt.RightButton, pos=QPoint(200, 28))
    assert played == [3]
    QTest.mouseClick(item, Qt.LeftButton, pos=item.play_indicator.geometry().center())
    assert played == [3]
    QTest.mousePress(item, Qt.LeftButton, pos=QPoint(200, 28))
    QTest.mouseRelease(item, Qt.LeftButton, pos=QPoint(900, 28))
    assert played == [3]
    removed = []
    item.remove_clicked.connect(removed.append)
    play_button, remove_button = item.findChildren(QPushButton)
    remove_button.click()
    assert removed == [3] and played == [3]
    play_button.click()
    assert played == [3, 3]
    item.close()


def test_track_row_columns_never_overlap_even_in_a_narrow_list(qapp):
    tracks = [{"videoId": "a", "title": "Titulo", "artists": [{"name": "X"}], "duration": "2:40",
               "views": "409 K reproducciones"}]
    for width, options in ((740, dict(show_cover=False, show_artist=False, show_album=False)),
                           (900, dict(show_cover=True, show_artist=True, show_album=False))):
        boxes = sorted(_cells(QRect(0, 0, width, 56), tracks[0], dict(numbered=True, **options)).values(),
                       key=lambda rect: rect.x())
        assert len(boxes) >= 4
        for left, right in zip(boxes, boxes[1:]):
            assert left.right() < right.x(), (width, left, right)
        assert boxes[-1].right() <= width


def make_playback(auto_queue):
    queue = PlayQueue(radio_limit=6)
    catalog = FakeCatalog()
    service = PlaybackService(queue, FakeStreams(), FakeAudio(), catalog, FakeNotifier(), auto_queue=auto_queue)
    return service, queue, catalog


def test_auto_queue_off_plays_only_the_chosen_song_and_never_extends(qapp):
    state = {"on": False}
    service, queue, catalog = make_playback(lambda: state["on"])
    service.start_radio(song(0))
    assert [c["key"] for c in catalog.calls] == [] and len(queue) == 1
    service.play_collection([song(1), song(2)])
    service.next()
    assert [c["key"] for c in catalog.calls] == []
    state["on"] = True
    service.start_radio(song(5))
    assert [c["key"] for c in catalog.calls] == ["radio"]
    service._radio_pending = False
    service.play_collection([song(1), song(2)])
    service.next()
    assert "extend" in [c["key"] for c in catalog.calls]


def test_dialog_auto_queue_switch_reports_and_locks_the_radio_size(rig):
    changes = []
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: changes.append(kw))
    assert dialog.auto_queue.isChecked() and dialog.radio.isEnabled()
    dialog.auto_queue.setChecked(False)
    assert changes == [{"auto_queue": False}] and not dialog.radio.isEnabled()
    dialog.auto_queue.setChecked(True)
    assert dialog.radio.isEnabled()
    off = SettingsDialog(rig.window, Settings(auto_queue=False), True, lambda **kw: None)
    assert not off.auto_queue.isChecked() and not off.radio.isEnabled()
    dialog.deleteLater()
    off.deleteLater()


def test_auto_queue_setting_is_tolerant():
    assert Settings.from_dict({"auto_queue": "no"}).auto_queue is True
    assert Settings.from_dict({"auto_queue": False}).auto_queue is False


def test_import_option_is_gone_from_the_sidebar_and_window(rig):
    assert not hasattr(rig.window.sidebar, "import_button") and not hasattr(rig.window, "import_url_submitted")


def test_tracks_keep_the_album_id_and_like_status():
    track = normalize_track({"videoId": "a", "title": "T", "album": {"name": "Disco", "id": "MPRE1"},
                             "likeStatus": "LIKE"})
    assert track["album"] == "Disco" and track["albumId"] == "MPRE1" and track["likeStatus"] == "LIKE"
    plain = normalize_track({"videoId": "a", "album": "Solo nombre"})
    assert plain["album"] == "Solo nombre" and "albumId" not in plain and "likeStatus" not in plain


def test_album_and_artist_helpers():
    assert album_of({"album": "Disco", "albumId": "MPRE1"}) == ("Disco", "MPRE1")
    assert album_of({"album": {"name": "Disco", "id": "MPRE2"}}) == ("Disco", "MPRE2")
    assert album_of({}) == ("", "")
    assert artist_id_of({"artists": [{"name": "x"}, {"name": "y", "id": "UC9"}]}) == "UC9"
    assert artist_id_of({"artists": ["texto"]}) == "" and artist_id_of({}) == ""


class FakeLibrary:
    def __init__(self):
        self.status_requests, self.rated, self.result = [], [], True

    def like_status(self, video_id, on_done):
        self.status_requests.append((video_id, on_done))

    def set_like(self, video_id, liked, on_done):
        self.rated.append((video_id, liked))
        on_done(self.result)


def make_player(rig, library=None, navigator=None):
    navigator = navigator or Navigator()
    library = library if library is not None else FakeLibrary()
    presenter = rig.keep(PlayerPresenter(rig.window, rig.playback, navigator, library, rig.notifier))
    return presenter, navigator, library


def test_now_playing_shows_album_and_links_only_when_ids_exist(rig):
    make_player(rig)
    rig.playback.track_loading.emit(song(1, album="Disco", albumId="MPRE1"))
    panel = rig.window.player_panel
    assert panel.album_label.text() == "Disco" and panel.artist_label.linked and panel.album_label.linked
    assert not panel.album_label.isHidden()
    rig.playback.track_loading.emit({"videoId": "x", "title": "T", "artists": [{"name": "Sin id"}], "album": "Disco"})
    assert not panel.artist_label.linked and not panel.album_label.linked and panel.album_label.text() == "Disco"
    rig.playback.track_loading.emit({"videoId": "y", "title": "T", "artists": [{"name": "A"}]})
    assert panel.album_label.isHidden()


def test_clicking_artist_and_album_navigates(rig):
    _presenter, navigator, _library = make_player(rig)
    artists, albums = [], []
    navigator.artist_requested.connect(artists.append)
    navigator.album_requested.connect(albums.append)
    rig.playback.track_loading.emit(song(1, album="Disco", albumId="MPRE1"))
    QTest.mouseClick(rig.window.player_panel.artist_label, Qt.LeftButton)
    QTest.mouseClick(rig.window.player_panel.album_label, Qt.LeftButton)
    assert artists == ["UC1"] and albums == ["MPRE1"]
    rig.playback.track_loading.emit({"videoId": "x", "title": "T", "artists": [{"name": "Sin id"}]})
    rig.window.now_artist_clicked.emit()
    rig.window.now_album_clicked.emit()
    assert artists == ["UC1"] and albums == ["MPRE1"]


def test_links_are_off_without_a_navigator(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.playback.track_loading.emit(song(1, album="Disco", albumId="MPRE1"))
    assert not rig.window.player_panel.artist_label.linked
    rig.window.like_clicked.emit()
    rig.window.now_artist_clicked.emit()


def test_like_state_comes_from_the_track_or_is_asked_once_when_signed_in(rig):
    _presenter, _nav, library = make_player(rig)
    rig.window.set_auth_state(True)
    rig.playback.track_loading.emit(song(1, likeStatus="LIKE"))
    assert library.status_requests == [] and rig.window.player_panel.like_button.toolTip() == "Quitar de Me gusta"
    rig.playback.track_loading.emit(song(2, likeStatus="INDIFFERENT"))
    assert library.status_requests == [] and rig.window.player_panel.like_button.toolTip() == "Me gusta"
    rig.playback.track_loading.emit(song(3))
    video_id, answer = library.status_requests[0]
    assert video_id == "v3"
    answer("LIKE")
    assert rig.window.player_panel.like_button.toolTip() == "Quitar de Me gusta"
    rig.playback.track_loading.emit(song(4))
    late = library.status_requests[1][1]
    rig.playback.track_loading.emit(song(5, likeStatus="INDIFFERENT"))
    late("LIKE")
    assert rig.window.player_panel.like_button.toolTip() == "Me gusta"
    library.status_requests[1][1](None)


def test_like_state_is_not_requested_when_signed_out(rig):
    _presenter, _nav, library = make_player(rig)
    rig.playback.track_loading.emit(song(1))
    assert library.status_requests == [] and not rig.window.player_panel.like_button.isEnabled()
    rig.window.set_auth_state(True)
    assert rig.window.player_panel.like_button.isEnabled()
    rig.window.set_auth_state(False)
    assert not rig.window.player_panel.like_button.isEnabled()


def test_like_button_toggles_and_reverts_on_failure(rig):
    _presenter, _nav, library = make_player(rig)
    rig.window.set_auth_state(True)
    rig.window.like_clicked.emit()
    assert library.rated == []
    rig.playback.track_loading.emit(song(1, likeStatus="INDIFFERENT"))
    rig.window.player_panel.like_button.click()
    assert library.rated == [("v1", True)] and rig.window.player_panel.like_button.toolTip() == "Quitar de Me gusta"
    rig.window.player_panel.like_button.click()
    assert library.rated[-1] == ("v1", False) and rig.window.player_panel.like_button.toolTip() == "Me gusta"
    library.result = False
    rig.window.player_panel.like_button.click()
    assert rig.window.player_panel.like_button.toolTip() == "Me gusta"
    assert rig.notifier.messages[-1][0] == "error"


def test_failed_like_after_switching_song_does_not_touch_the_new_song(rig):
    presenter, _nav, library = make_player(rig)
    rig.window.set_auth_state(True)
    rig.playback.track_loading.emit(song(1, likeStatus="INDIFFERENT"))
    pending = []
    library.set_like = lambda video_id, liked, on_done: pending.append(on_done)
    rig.window.player_panel.like_button.click()
    rig.playback.track_loading.emit(song(2, likeStatus="LIKE"))
    pending[0](False)
    assert rig.window.player_panel.like_button.toolTip() == "Quitar de Me gusta" and presenter is not None


class FakeYtm:
    def __init__(self):
        self.rated = []

    def get_watch_playlist(self, videoId, limit):
        return {"tracks": [{"videoId": videoId, "likeStatus": "LIKE"}] if videoId == "liked" else []}

    def rate_song(self, video_id, status):
        self.rated.append((video_id, status))


def test_gateway_reads_the_like_status_and_rates_songs(monkeypatch):
    from infra.ytmusic_gateway import YTMusicGateway

    gateway = YTMusicGateway("unused.json")
    ytm = FakeYtm()
    monkeypatch.setattr(gateway, "_require_auth", lambda: ytm)
    assert gateway.get_like_status("liked") == "LIKE" and gateway.get_like_status("other") is None
    gateway.rate_song("a", "LIKE")
    assert ytm.rated == [("a", "LIKE")]


def test_library_service_rates_in_the_background_and_reports_failures(qapp, tmp_path, wait_until):
    from infra.playlist_repository import LocalPlaylistRepository
    from services.catalog_service import CatalogService

    class Gateway:
        def __init__(self):
            self.rated, self.fail = [], False

        def get_like_status(self, video_id):
            if self.fail:
                raise RuntimeError("sin red")
            return "LIKE"

        def rate_song(self, video_id, status):
            if self.fail:
                raise RuntimeError("sin red")
            self.rated.append((video_id, status))

    gateway = Gateway()
    runner = TaskRunner("like-test", 2)
    service = LibraryService(gateway, LocalPlaylistRepository(str(tmp_path / "p.json")),
                             CatalogService(gateway, runner), runner)
    try:
        got = []
        service.like_status("a", got.append)
        assert wait_until(lambda: got == ["LIKE"])
        service.set_like("a", True, got.append)
        assert wait_until(lambda: got[-1] is True)
        service.set_like("a", False, got.append)
        assert wait_until(lambda: len(got) == 3)
        assert gateway.rated == [("a", "LIKE"), ("a", "INDIFFERENT")]
        gateway.fail = True
        service.set_like("a", True, got.append)
        assert wait_until(lambda: got[-1] is False)
        service.like_status("a", got.append)
        assert wait_until(lambda: len(got) == 5 and got[-1] is None)
    finally:
        runner.shutdown()


def test_search_history_keeps_recent_unique_queries_and_persists(qapp, tmp_path):
    path = tmp_path / "h.json"
    history = SearchHistoryService(str(path), limit=3)
    seen = []
    history.changed.connect(seen.append)
    for query in ("uno", "dos", "  tres  ", "UNO", "cuatro", "   ", ""):
        history.add(query)
    assert history.items == ["cuatro", "UNO", "tres"] and seen[-1] == ["cuatro", "UNO", "tres"]
    history.add("cuatro")
    assert len(seen) == 5
    assert json.loads(path.read_text(encoding="utf-8")) == ["cuatro", "UNO", "tres"]
    history.remove("UNO")
    assert SearchHistoryService(str(path)).items == ["cuatro", "tres"]
    history.remove("nada")
    history.clear()
    history.clear()
    assert history.items == [] and SearchHistoryService(str(path)).items == []


@pytest.mark.parametrize("content", ["not json", '{"a": 1}', '[1, null, "ok", " "]'])
def test_search_history_ignores_a_damaged_file(qapp, tmp_path, content):
    path = tmp_path / "h.json"
    path.write_text(content, encoding="utf-8")
    assert SearchHistoryService(str(path)).items in ([], ["ok"])


def make_search(rig, tmp_path):
    history = SearchHistoryService(str(tmp_path / "h.json"))
    rig.keep(SearchPresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, history))
    return history


def test_searching_records_the_query_and_updates_the_popup(rig, tmp_path):
    history = make_search(rig, tmp_path)
    rig.catalog.search = lambda query, on_done, on_error=None: None
    rig.window.search_submitted.emit("bad bunny")
    rig.window.search_submitted.emit("duki")
    assert history.items == ["duki", "bad bunny"]
    assert rig.window.top_bar.history._items == ["duki", "bad bunny"]
    rig.window.history_removed.emit("duki")
    assert history.items == ["bad bunny"]
    rig.window.history_cleared.emit()
    assert history.items == []


def test_history_popup_shows_matches_while_typing_and_hides_without_focus(rig, tmp_path):
    make_search(rig, tmp_path)
    rig.window.set_search_history(["bad bunny", "blinding lights", "duki"])
    popup = rig.window.top_bar.history
    box = rig.window.top_bar.search_box
    assert not popup.isVisible()
    box.setFocus()
    popup.refresh()
    if box.hasFocus():
        assert popup.isVisible() and popup.shown_items() == ["bad bunny", "blinding lights", "duki"]
        box.setText("b")
        assert popup.shown_items() == ["bad bunny", "blinding lights"]
        box.setText("zzz")
        assert not popup.isVisible()
        box.setText("duki")
        assert popup.shown_items() == []
    box.clearFocus()
    assert not popup.isVisible()


def test_history_popup_rows_choose_remove_and_clear(rig, tmp_path):
    make_search(rig, tmp_path)
    popup = rig.window.top_bar.history
    rig.window.set_search_history(["bad bunny", "duki"])
    box = rig.window.top_bar.search_box
    picked, removed, cleared = [], [], []
    popup.chosen.connect(picked.append)
    popup.removed.connect(removed.append)
    popup.cleared.connect(lambda: cleared.append(1))
    box.hasFocus = lambda: True
    popup.refresh()
    from ui.components.search_history_popup import _Row
    row_widgets = popup.findChildren(_Row)
    assert len(row_widgets) == 2
    row_widgets[0].remove_button.click()
    QTest.mouseClick(row_widgets[1], Qt.LeftButton, pos=QPoint(60, 10))
    assert removed == ["bad bunny"] and picked == ["duki"]
    box.setText("")
    popup.refresh()
    next(b for b in popup.findChildren(QPushButton) if b.text() == "Borrar historial").click()
    assert cleared == [1]


def test_choosing_a_history_entry_searches_it_and_leaves_the_box(rig, tmp_path):
    make_search(rig, tmp_path)
    submitted = []
    rig.window.search_submitted.connect(submitted.append)
    rig.window.top_bar.history.chosen.emit("blinding lights")
    assert submitted == ["blinding lights"] and rig.window.top_bar.search_box.text() == "blinding lights"
    assert not rig.window.top_bar.search_box.hasFocus()


def test_paths_include_the_search_history_file(tmp_path):
    from core.config import AppPaths

    assert AppPaths(str(tmp_path)).search_history_file.endswith("search_history.json")
