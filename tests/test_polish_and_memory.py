import pytest
from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSystemTrayIcon

from domain.settings import DEFAULT_THUMBNAIL_CACHE, THUMBNAIL_CACHE_OPTIONS, Settings
from infra.thumbnail_cache import ThumbnailCache
from presenters.memory_presenter import MemoryPresenter
from presenters.settings_presenter import SettingsPresenter
from services.settings_service import SettingsService
from infra.settings_repository import SettingsRepository
from tests.test_presenters import Rig
from ui.components.no_scroll_combo import NoScrollComboBox
from ui.components.sidebar import _spaced_icon
from ui.settings_dialog import SettingsDialog
from ui.styles import APP_STYLESHEET


@pytest.fixture(autouse=True)
def tray_present(monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def make_settings(tmp_path, **initial):
    service = SettingsService(SettingsRepository(str(tmp_path / "s.json")))
    if initial:
        service.update(**initial)
    return service



def test_expanded_icons_get_blank_space_so_the_text_is_not_glued_to_them(qapp):
    import qtawesome as qta

    icon = qta.icon("fa5s.home", color="white")
    plain = icon.pixmap(22, 22)
    spaced = _spaced_icon(icon, 22, 12).pixmap(22 + 12, 22)
    assert spaced.width() == plain.width() + 12 and spaced.height() == plain.height()


def test_expanded_nav_text_is_bigger_than_collapsed(rig):
    sidebar = rig.window.sidebar
    assert "font-size: 11px" in sidebar.nav_buttons["Inicio"].styleSheet()
    sidebar.set_expanded(True)
    assert "font-size: 15px" in sidebar.nav_buttons["Inicio"].styleSheet()


def test_top_bar_and_sidebar_no_longer_have_a_divider_border():
    assert "border-bottom: 1px solid #333" not in APP_STYLESHEET
    assert "border-right: 1px solid #333" not in APP_STYLESHEET


def test_new_music_videos_shelf_was_removed_from_explore_and_home(qapp, wait_until):
    from infra.concurrency import TaskRunner
    from services.catalog_service import CatalogService

    class Gateway:
        is_authenticated = False

        def get_explore(self):
            return {"new_releases": [], "trending": {"items": []}, "moods_and_genres": [],
                    "new_videos": [{"title": "Vid", "videoId": "v1", "thumbnails": []}]}

        def get_home(self, limit):
            return []

        def get_charts(self):
            return {"videos": []}

    runner = TaskRunner("no-video", 1)
    service = CatalogService(Gateway(), runner)
    try:
        explore, home = [], []
        service.load_explore(explore.append)
        assert wait_until(lambda: explore)
        assert not any(title == "Videos musicales nuevos" for title, _ in explore[0])
        service.load_home(home.append)
        assert wait_until(lambda: home)
        assert not any(title == "Videos musicales nuevos" for title, _ in home[0])
    finally:
        runner.shutdown()



def test_combo_ignores_the_wheel_when_closed_but_not_when_open(qapp):
    box = NoScrollComboBox()
    box.addItem("Uno", 1)
    box.addItem("Dos", 2)
    box.addItem("Tres", 3)
    box.resize(150, 30)
    box.show()
    before = box.currentIndex()
    event = QWheelEvent(QPoint(10, 10).toPointF(), QPoint(10, 10).toPointF(), QPoint(), QPoint(0, -120),
                        Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
    box.wheelEvent(event)
    assert box.currentIndex() == before
    box.showPopup()
    box.wheelEvent(event)
    box.hidePopup()
    box.close()


def test_settings_dialog_uses_the_no_scroll_combo(rig):
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: None)
    assert isinstance(dialog.radio, NoScrollComboBox)
    assert isinstance(dialog.thumbnail_quality, NoScrollComboBox)
    assert isinstance(dialog.thumbnail_cache_limit, NoScrollComboBox)
    dialog.deleteLater()



def test_clicking_outside_the_search_box_and_history_clears_its_focus(rig, monkeypatch):
    box = rig.window.top_bar.search_box
    box.show()
    monkeypatch.setattr(type(box), "hasFocus", lambda _self: True)
    cleared = []
    monkeypatch.setattr(type(box), "clearFocus", lambda _self: cleared.append(1))
    outside = QMouseEvent(QEvent.MouseButtonPress, QPoint(-500, -500), rig.window.mapToGlobal(QPoint(-500, -500)),
                          Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    rig.window.top_bar.eventFilter(rig.window, outside)
    assert cleared == [1]


def test_clicking_inside_the_search_box_or_the_open_history_keeps_the_focus(rig, monkeypatch):
    box = rig.window.top_bar.search_box
    box.show()
    monkeypatch.setattr(type(box), "hasFocus", lambda _self: True)
    cleared = []
    monkeypatch.setattr(type(box), "clearFocus", lambda _self: cleared.append(1))
    center = box.mapToGlobal(box.rect().center())
    click = QMouseEvent(QEvent.MouseButtonPress, box.mapFromGlobal(center), center,
                        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    rig.window.top_bar.eventFilter(rig.window, click)
    assert cleared == []



def test_thumbnail_cache_limit_setting_is_tolerant_and_defaults():
    assert Settings().thumbnail_cache_limit == DEFAULT_THUMBNAIL_CACHE
    assert Settings.from_dict({"thumbnail_cache_limit": 999}).thumbnail_cache_limit == DEFAULT_THUMBNAIL_CACHE
    for option in THUMBNAIL_CACHE_OPTIONS:
        assert Settings.from_dict({"thumbnail_cache_limit": option}).thumbnail_cache_limit == option


def test_thumbnail_cache_set_max_items_trims_immediately(qapp):
    from PySide6.QtGui import QPixmap

    cache = ThumbnailCache(None, max_items=10)
    for i in range(10):
        cache._memory[f"u{i}"] = QPixmap()
    cache.set_max_items(3)
    assert len(cache._memory) == 3


def test_dialog_reports_the_thumbnail_cache_limit_choice(rig):
    changes = []
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: changes.append(kw))
    dialog.thumbnail_cache_limit.setCurrentIndex(dialog.thumbnail_cache_limit.findData(100))
    assert changes == [{"thumbnail_cache_limit": 100}]
    dialog.deleteLater()


def test_settings_presenter_applies_the_cache_limit_on_start_and_on_change(rig, tmp_path):
    seen = []

    class FakeThumbs:
        def set_max_items(self, n):
            seen.append(n)

    service = make_settings(tmp_path, thumbnail_cache_limit=200)
    rig.keep(SettingsPresenter(rig.window, service, thumbnails=FakeThumbs()))
    assert seen == [200]
    service.update(thumbnail_cache_limit=800)
    assert seen == [200, 800]


class _View:
    def release(self):
        pass


def test_release_and_free_now_also_clear_the_collapsed_playlist_rail(rig, tmp_path):
    rig.window.sidebar.set_playlists([{"playlistId": "a", "title": "A"}], None)
    assert rig.window.sidebar.rail._rows_layout.count() == 1
    rig.window.thumbnails = type("T", (), {"clear_memory": lambda _s: None, "request": lambda *_a: None})()
    presenter = MemoryPresenter(rig.window, _View(), _View(), settings=make_settings(tmp_path))
    rig.window.hide()
    presenter.release()
    assert rig.window.sidebar.rail._rows_layout.count() == 0


def test_release_rail_does_nothing_while_the_sidebar_is_expanded(rig):
    rig.window.sidebar.set_expanded(True)
    rig.window.sidebar.set_playlists([{"playlistId": "a", "title": "A"}], None)
    rig.window.sidebar.release_rail()
    assert rig.window.sidebar.rail._rows_layout.count() == 1
    rig.window.sidebar.set_expanded(False)
