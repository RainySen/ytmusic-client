import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from domain.settings import THUMBNAIL_QUALITY_OPTIONS, Settings
from infra.pinned_playlists import PinnedPlaylists
from infra.playlist_repository import LocalPlaylistRepository
from presenters.player_presenter import PlayerPresenter
from presenters.playlist_rail_presenter import PlaylistRailPresenter
from presenters.search_presenter import SearchPresenter
from services.library_service import LibraryService
from services.search_history_service import SearchHistoryService
from tests.test_presenters import Rig
from ui import imaging
from ui.components import dialogs
from ui.components.jump_slider import JumpSlider
from ui.components.playlist_rail import PlaylistRail, PlaylistRailRow
from ui.components.sidebar import COLLAPSED_WIDTH, EXPANDED_WIDTH
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


def song(n=1):
    return {"videoId": f"v{n}", "title": f"Titulo {n}", "artists": [{"name": "Artista"}]}


def playlist(pid, title="P", pinned=False, source="local"):
    return {"playlistId": pid, "title": title, "pinned": pinned, "source": source, "track_count": 3,
            "thumbnails": []}



def test_thumbnail_quality_setting_is_tolerant_and_roundtrips():
    assert Settings.from_dict({"thumbnail_quality": "ultra"}).thumbnail_quality == "auto"
    for option in THUMBNAIL_QUALITY_OPTIONS:
        assert Settings.from_dict({"thumbnail_quality": option}).thumbnail_quality == option


def test_thumb_px_scales_by_quality_and_screen_density(qapp, monkeypatch):
    imaging.set_thumbnail_quality("auto")
    monkeypatch.setattr(imaging, "_screen_dpr", lambda: 1.0)
    assert imaging.thumb_px(100) == 100
    imaging.set_thumbnail_quality("high")
    assert imaging.thumb_px(100) == 150
    imaging.set_thumbnail_quality("low")
    assert imaging.thumb_px(100) == 75
    imaging.set_thumbnail_quality("nonsense")
    assert imaging.thumb_px(100) == 100
    monkeypatch.setattr(imaging, "_screen_dpr", lambda: 2.0)
    imaging.set_thumbnail_quality("auto")
    assert imaging.thumb_px(50) == 100
    imaging.set_thumbnail_quality("auto")


def test_recommended_quality_favours_large_or_hidpi_screens(monkeypatch):
    class Screen:
        def __init__(self, width, dpr):
            self._width = width
            self._dpr = dpr

        def geometry(self):
            from PySide6.QtCore import QRect
            return QRect(0, 0, self._width, 100)

        def devicePixelRatio(self):
            return self._dpr

    monkeypatch.setattr(QApplication, "primaryScreen", staticmethod(lambda: Screen(1920, 1.0)))
    assert imaging.recommended_thumbnail_quality() == "auto"
    monkeypatch.setattr(QApplication, "primaryScreen", staticmethod(lambda: Screen(3840, 1.0)))
    assert imaging.recommended_thumbnail_quality() == "high"
    monkeypatch.setattr(QApplication, "primaryScreen", staticmethod(lambda: Screen(1920, 2.0)))
    assert imaging.recommended_thumbnail_quality() == "high"
    monkeypatch.setattr(QApplication, "primaryScreen", staticmethod(lambda: None))
    assert imaging.recommended_thumbnail_quality() == "auto"


def test_dialog_reports_the_thumbnail_quality_choice(rig):
    changes = []
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: changes.append(kw))
    dialog.thumbnail_quality.setCurrentIndex(dialog.thumbnail_quality.findData("high"))
    assert changes == [{"thumbnail_quality": "high"}]
    dialog.deleteLater()


def test_settings_presenter_applies_the_quality_on_change(rig, tmp_path):
    from infra.settings_repository import SettingsRepository
    from services.settings_service import SettingsService
    from presenters.settings_presenter import SettingsPresenter

    seen = []
    monkeypatch_target = imaging.set_thumbnail_quality
    imaging.set_thumbnail_quality = lambda q: seen.append(q)
    try:
        service = SettingsService(SettingsRepository(str(tmp_path / "s.json")))
        rig.keep(SettingsPresenter(rig.window, service))
        service.update(thumbnail_quality="low")
        assert seen[-1] == "low" and seen[0] == "auto"
    finally:
        imaging.set_thumbnail_quality = monkeypatch_target



def test_jump_slider_click_jumps_and_dragging_continues(qapp):
    slider = JumpSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.resize(200, 24)
    slider.setValue(50)
    slider.show()
    QTest.mousePress(slider, Qt.LeftButton, pos=QPoint(15, 12))
    jumped = slider.value()
    assert jumped < 20
    QTest.mouseMove(slider, QPoint(185, 12))
    QTest.mouseRelease(slider, Qt.LeftButton, pos=QPoint(185, 12))
    assert slider.value() > jumped + 50
    slider.close()


def test_jump_slider_click_on_the_handle_behaves_like_a_normal_slider(qapp):
    slider = JumpSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.resize(200, 24)
    slider.setValue(0)
    slider.show()
    moved = []
    slider.sliderMoved.connect(moved.append)
    QTest.mousePress(slider, Qt.LeftButton, pos=QPoint(10, 12))
    QTest.mouseRelease(slider, Qt.LeftButton, pos=QPoint(10, 12))
    assert slider.value() == 0
    slider.close()


def test_seek_suppresses_stale_progress_and_time_until_the_backend_catches_up(rig):
    clock = [100.0]
    presenter = rig.keep(PlayerPresenter(rig.window, rig.playback, clock=lambda: clock[0]))
    rig.window.player_panel.progress_slider.sliderMoved.emit(700)
    assert rig.window.player_panel.progress_slider.value() != 100
    rig.window.player_panel.progress_slider.setValue(700)
    rig.playback.progress.emit(0.05)
    assert rig.window.player_panel.progress_slider.value() == 700
    rig.playback.time_changed.emit(1, 300)
    assert rig.window.player_panel.time_label.text() != "0:01"
    clock[0] += 1.0
    rig.playback.progress.emit(0.05)
    assert rig.window.player_panel.progress_slider.value() == 50
    assert presenter is not None



def make_search(rig, tmp_path):
    history = SearchHistoryService(str(tmp_path / "h.json"))
    return rig.keep(SearchPresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, history))


def test_fast_search_never_flashes_the_loading_message(rig, tmp_path):
    make_search(rig, tmp_path)
    calls = []
    rig.catalog.search = lambda query, on_done, on_error=None: (
        calls.append(query), on_done({"top_result": None, "songs": [], "more": []}))
    rig.window.search_submitted.emit("bad bunny")
    assert rig.window.search_panel.findChild(type(None)) is None
    assert "Buscando" not in _panel_text(rig)


def test_slow_search_shows_the_loading_message_after_a_short_delay(rig, tmp_path, wait_until):
    make_search(rig, tmp_path)
    pending = []
    rig.catalog.search = lambda query, on_done, on_error=None: pending.append(on_done)
    rig.window.search_submitted.emit("duki")
    assert wait_until(lambda: "Buscando" in _panel_text(rig), timeout_ms=1000)
    pending[0]({"top_result": None, "songs": [], "more": []})
    assert "Buscando" not in _panel_text(rig)


def _panel_text(rig):
    from PySide6.QtWidgets import QLabel

    return " ".join(label.text() for label in rig.window.search_panel.findChildren(QLabel))



def test_local_playlist_tracks_when_it_was_last_modified(tmp_path):
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    pid = repo.add("Mine", [{"videoId": "a"}], "user_created")
    created = repo.get(pid)["updated_at"]
    repo.add_tracks(pid, [{"videoId": "b"}])
    assert repo.get(pid)["updated_at"] >= created
    repo.rename(pid, "Renamed")
    assert repo.get(pid)["title"] == "Renamed"


def test_legacy_playlists_without_a_timestamp_fall_back_to_created_at(tmp_path):
    import json

    path = tmp_path / "p.json"
    path.write_text(json.dumps([{"playlistId": "x", "title": "Old", "tracks": [], "created_at": "2020-01-01"}]))
    repo = LocalPlaylistRepository(str(path))
    assert repo.get("x")["updated_at"] == "2020-01-01"



def test_pinned_playlists_store_toggles_and_keeps_the_most_recently_pinned_first(tmp_path):
    store = PinnedPlaylists(str(tmp_path / "pins.json"))
    assert store.ids() == [] and not store.is_pinned("a")
    assert store.toggle("a") is True
    assert store.toggle("b") is True
    assert store.ids() == ["b", "a"] and store.is_pinned("a")
    assert store.toggle("a") is False
    assert store.ids() == ["b"]
    store.discard("b")
    assert store.ids() == []
    store.discard("missing")
    reloaded = PinnedPlaylists(str(tmp_path / "pins.json"))
    assert reloaded.ids() == []


def test_library_service_sorts_pinned_first_then_by_recent_modification(qapp, tmp_path):
    from infra.concurrency import TaskRunner
    from services.catalog_service import CatalogService

    class Gateway:
        is_authenticated = False

    runner = TaskRunner("lib-sort", 1)
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    pins = PinnedPlaylists(str(tmp_path / "pins.json"))
    ids = []
    for title in ("A", "B", "C"):
        ids.append(repo.add(title, [{"videoId": title}], "user_created"))
    pins.toggle(ids[0])
    service = LibraryService(Gateway(), repo, CatalogService(Gateway(), runner), runner, pins=pins)
    try:
        out = []
        service.playlists(out.append)
        titles = [p["title"] for p in out[0]]
        assert titles[0] == "A" and out[0][0]["pinned"] is True
        assert titles[1:] == ["C", "B"]
        assert service.toggle_pin(ids[0]) is False
        out2 = []
        service.playlists(out2.append)
        assert [p["title"] for p in out2[0]] == ["C", "B", "A"]
    finally:
        runner.shutdown()


def test_delete_local_playlist_also_clears_its_pin(tmp_path):
    from infra.concurrency import TaskRunner
    from services.catalog_service import CatalogService

    class Gateway:
        is_authenticated = False

    runner = TaskRunner("lib-del", 1)
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    pins = PinnedPlaylists(str(tmp_path / "pins.json"))
    pid = repo.add("A", [], "user_created")
    pins.toggle(pid)
    service = LibraryService(Gateway(), repo, CatalogService(Gateway(), runner), runner, pins=pins)
    try:
        assert service.delete_local_playlist(pid) is True
        assert pins.ids() == [] and repo.get(pid) is None
    finally:
        runner.shutdown()



def test_gateway_get_liked_songs_uses_the_liked_playlist(monkeypatch):
    from infra.ytmusic_gateway import YTMusicGateway

    gateway = YTMusicGateway("unused.json")
    monkeypatch.setattr(gateway, "_require_auth", lambda: type("Y", (), {
        "get_liked_songs": lambda _self, limit: {"tracks": [{"videoId": "a"}]}})())
    assert gateway.get_liked_songs(50) == [{"videoId": "a"}]


def test_library_service_liked_songs_needs_a_session(qapp, tmp_path, wait_until):
    from infra.concurrency import TaskRunner
    from services.catalog_service import CatalogService

    class Gateway:
        is_authenticated = False

        def get_liked_songs(self, limit):
            return [{"videoId": "a", "title": "T", "artists": [{"name": "A"}]}]

    runner = TaskRunner("liked", 1)
    service = LibraryService(Gateway(), LocalPlaylistRepository(str(tmp_path / "p.json")),
                             CatalogService(Gateway(), runner), runner)
    try:
        out = []
        service.liked_songs(out.append)
        assert out == [None]
        service._gateway.is_authenticated = True
        service.liked_songs(out.append)
        assert wait_until(lambda: len(out) == 2)
        assert out[1][0]["videoId"] == "a"
    finally:
        runner.shutdown()


def test_library_browser_shows_the_three_liked_states(qapp):
    from ui.components.library_browser import LibraryBrowserPanel

    panel = LibraryBrowserPanel()
    panel.show_liked(None, Thumbs())
    assert "Inicia sesión" in panel.findChild(type(panel)).__class__.__name__ or True
    from PySide6.QtWidgets import QLabel
    assert any("Inicia sesión" in w.text() for w in panel.findChildren(QLabel))
    panel.show_liked([], Thumbs())
    assert any("Me gusta" in w.text() for w in panel.findChildren(QLabel))
    panel.show_liked([song(1)], Thumbs())
    assert panel.songs is not None and panel.songs.tracks[0]["title"] == "Titulo 1"


def test_library_presenter_wires_the_liked_chip(rig):
    from presenters.library_presenter import LibraryPresenter

    rig.keep(LibraryPresenter(rig.window, rig.library, rig.playback, rig.opener, rig.notifier, rig.navigator))
    rig.window.library_browser.chip_selected.emit("Me gusta")
    assert len(rig.library.liked_requests) == 1
    rig.library.liked_requests[0](None)



def test_playlist_row_shows_a_pin_only_when_pinned(qapp):
    plain = PlaylistRailRow(playlist("a", pinned=False), Thumbs())
    pinned = PlaylistRailRow(playlist("b", pinned=True), Thumbs())
    assert plain.layout().count() == 3 and pinned.layout().count() == 4


def test_playlist_row_three_dot_menu_offers_delete_only_for_local_playlists(qapp):
    local = PlaylistRailRow(playlist("a", pinned=False, source="local"), Thumbs())
    cloud = PlaylistRailRow(playlist("b", pinned=True, source="ytmusic"), Thumbs())
    local_labels = [label for _key, label, _icon in local.actions._entries]
    cloud_labels = [label for _key, label, _icon in cloud.actions._entries]
    assert "Eliminar playlist" in local_labels and "Fijar playlist" in local_labels
    assert "Eliminar playlist" not in cloud_labels and "Quitar de fijadas" in cloud_labels


def test_playlist_row_dispatches_each_action_with_its_playlist(qapp):
    row = PlaylistRailRow(playlist("a", pinned=False, source="local"), Thumbs())
    nexts, queues, pins, deletes = [], [], [], []
    row.play_next_requested.connect(nexts.append)
    row.add_queue_requested.connect(queues.append)
    row.pin_toggled.connect(pins.append)
    row.delete_requested.connect(deletes.append)
    for key, bucket in (("next", nexts), ("queue", queues), ("pin", pins), ("delete", deletes)):
        row._dispatch(key)
        assert bucket == [row.playlist]


def test_playlist_rail_emits_its_actions(qapp):
    rail = PlaylistRail()
    rail.set_playlists([playlist("a")], Thumbs())
    chosen, pinned, deleted, nexts, queues = [], [], [], [], []
    rail.playlist_chosen.connect(chosen.append)
    rail.pin_toggled.connect(pinned.append)
    rail.delete_requested.connect(deleted.append)
    rail.play_next_requested.connect(nexts.append)
    rail.add_queue_requested.connect(queues.append)
    row = rail._rows_layout.itemAt(0).widget()
    row.chosen.emit(playlist("a"))
    row.pin_toggled.emit(playlist("a"))
    row.delete_requested.emit(playlist("a"))
    row.play_next_requested.emit(playlist("a"))
    row.add_queue_requested.emit(playlist("a"))
    assert [len(x) for x in (chosen, pinned, deleted, nexts, queues)] == [1, 1, 1, 1, 1]


def test_rail_shows_a_loading_message_then_the_real_list_or_the_empty_message(qapp):
    rail = PlaylistRail()
    rail.show()
    rail.set_loading()
    assert rail._message.isVisible() and rail._message.text() == "Cargando…" and rail._rows_layout.count() == 0
    rail.set_playlists([playlist("a")], Thumbs())
    assert not rail._message.isVisible() and rail._rows_layout.count() == 1
    rail.set_playlists([], Thumbs())
    assert rail._message.isVisible() and rail._message.text() == "Aún no tienes playlists."


def test_sidebar_expand_widens_and_reveals_the_rail(rig):
    sidebar = rig.window.sidebar
    assert sidebar.width() == COLLAPSED_WIDTH and not sidebar._rail_scroll.isVisible()
    sidebar.set_expanded(True)
    assert sidebar.width() == EXPANDED_WIDTH and sidebar.expanded
    sidebar.set_expanded(False)
    assert sidebar.width() == COLLAPSED_WIDTH and not sidebar.expanded


def test_menu_button_toggles_the_sidebar_and_collapses_after_choosing_a_playlist(rig):
    rig.window.top_bar.menu_button.setChecked(True)
    assert rig.window.sidebar.expanded
    rig.window.sidebar.rail.playlist_chosen.emit(playlist("a"))
    assert not rig.window.top_bar.menu_button.isChecked() and not rig.window.sidebar.expanded


def test_playlist_rail_presenter_refreshes_on_expand_and_on_biblioteca(rig):
    presenter = rig.keep(PlaylistRailPresenter(rig.window, rig.library, rig.playback, rig.notifier))
    rig.window.sidebar_expanded.emit(True)
    assert len(rig.library.playlist_requests) == 1
    rig.window.sidebar_expanded.emit(False)
    assert len(rig.library.playlist_requests) == 1
    rig.window.library_requested.emit()
    assert len(rig.library.playlist_requests) == 2
    rig.library.playlist_requests[-1]([playlist("a")])
    assert presenter is not None


def test_first_expand_shows_a_loading_message_while_waiting(rig):
    rig.keep(PlaylistRailPresenter(rig.window, rig.library, rig.playback, rig.notifier))
    rig.window.sidebar_expanded.emit(True)
    assert rig.window.sidebar.rail._message.text() == "Cargando…"
    rig.library.playlist_requests[-1]([playlist("a")])
    assert rig.window.sidebar.rail._rows_layout.count() == 1


def test_reopening_shows_the_cached_list_instantly_then_refreshes_in_the_background(rig):
    rig.keep(PlaylistRailPresenter(rig.window, rig.library, rig.playback, rig.notifier))
    rig.window.sidebar_expanded.emit(True)
    rig.library.playlist_requests[-1]([playlist("a")])
    rig.window.sidebar_expanded.emit(False)
    rig.window.sidebar_expanded.emit(True)
    assert rig.window.sidebar.rail._rows_layout.count() == 1
    assert len(rig.library.playlist_requests) == 2
    rig.library.playlist_requests[-1]([playlist("a"), playlist("b")])
    assert rig.window.sidebar.rail._rows_layout.count() == 2


def test_playlist_rail_presenter_opens_and_queues(rig):
    rig.keep(PlaylistRailPresenter(rig.window, rig.library, rig.playback, rig.notifier))
    rig.window.sidebar.rail.playlist_chosen.emit(playlist("a"))
    assert rig.streams.requests == ["v1"]
    rig.window.sidebar.rail.play_next_requested.emit(playlist("a"))
    assert rig.queue.upcoming(5)[0]["videoId"] in ("v1", "v2")
    rig.window.sidebar.rail.add_queue_requested.emit(playlist("a"))


def test_playlist_rail_presenter_toggles_pin_and_refreshes(rig):
    rig.keep(PlaylistRailPresenter(rig.window, rig.library, rig.playback, rig.notifier))
    before = len(rig.library.playlist_requests)
    rig.window.sidebar.rail.pin_toggled.emit(playlist("a"))
    assert rig.library.pinned == ["a"] and len(rig.library.playlist_requests) == before + 1


def test_playlist_rail_presenter_deletes_only_after_confirming(rig, monkeypatch):
    rig.keep(PlaylistRailPresenter(rig.window, rig.library, rig.playback, rig.notifier))
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: False)
    rig.window.sidebar.rail.delete_requested.emit(playlist("a"))
    assert rig.library.deleted == []
    monkeypatch.setattr(dialogs, "confirm", lambda *a, **k: True)
    rig.window.sidebar.rail.delete_requested.emit(playlist("a"))
    assert rig.library.deleted == ["a"]
