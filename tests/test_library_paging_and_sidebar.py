import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from presenters.library_presenter import LibraryPresenter
from services.library_service import LIKED_PAGE, PAGE_STEP, SONGS_PAGE
from tests.test_presenters import Rig
from ui.components.sidebar import COLLAPSED_BTN, EXPANDED_BTN


@pytest.fixture(autouse=True)
def tray_present(monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def song(n):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}]}


def make_lib(rig):
    return rig.keep(LibraryPresenter(rig.window, rig.library, rig.playback, rig.opener, rig.notifier, rig.navigator))



def test_menu_button_has_no_checked_highlight(rig):
    assert "checked" not in rig.window.top_bar.menu_button.styleSheet()


def test_nav_buttons_switch_between_stacked_and_inline_layout(rig):
    sidebar = rig.window.sidebar
    home = sidebar.nav_buttons["Inicio"]
    assert home.toolButtonStyle() == Qt.ToolButtonTextUnderIcon and home.size() == COLLAPSED_BTN
    sidebar.set_expanded(True)
    assert home.toolButtonStyle() == Qt.ToolButtonTextBesideIcon and home.size() == EXPANDED_BTN
    sidebar.set_expanded(False)
    assert home.toolButtonStyle() == Qt.ToolButtonTextUnderIcon and home.size() == COLLAPSED_BTN


def test_active_nav_style_survives_expand_and_collapse(rig):
    sidebar = rig.window.sidebar
    sidebar.set_active("Explorar")
    sidebar.set_expanded(True)
    assert "700" in sidebar.nav_buttons["Explorar"].styleSheet()
    assert "700" not in sidebar.nav_buttons["Inicio"].styleSheet()
    sidebar.set_expanded(False)
    assert "700" in sidebar.nav_buttons["Explorar"].styleSheet()



def test_songs_chip_prefetches_the_next_page_from_what_is_shown(rig):
    make_lib(rig)
    rig.window.library_browser.chip_selected.emit("Canciones")
    assert rig.library.limits == [SONGS_PAGE]
    rig.library.song_requests[-1]([song(n) for n in range(200)])
    assert rig.window.library_browser._can_load_more is True
    assert rig.library.limits[-1] == 200 + PAGE_STEP


def test_scrolling_uses_the_prefetched_page_without_asking_again(rig):
    make_lib(rig)
    browser = rig.window.library_browser
    browser.chip_selected.emit("Canciones")
    rig.library.song_requests[-1]([song(n) for n in range(100)])
    rig.library.song_requests[-1]([song(n) for n in range(200)])
    asked = len(rig.library.song_requests)
    browser.load_more_requested.emit()
    assert browser.songs.row_count == 200
    assert len(rig.library.song_requests) == asked + 1


def test_scrolling_before_the_prefetch_arrives_shows_it_on_arrival(rig):
    make_lib(rig)
    browser = rig.window.library_browser
    browser.chip_selected.emit("Me gusta")
    rig.library.liked_requests[-1]([song(n) for n in range(100)])
    pending = rig.library.liked_requests[-1]
    browser.load_more_requested.emit()
    assert len(rig.library.liked_requests) == 2
    pending([song(n) for n in range(100)])
    assert browser._can_load_more is False and browser._loading_more is False


def test_paging_stops_at_the_cap(rig):
    from services.library_service import PAGE_CAP

    make_lib(rig)
    rig.window.library_browser.chip_selected.emit("Canciones")
    rig.library.song_requests[-1]([song(n) for n in range(PAGE_CAP + 50)])
    assert rig.window.library_browser._can_load_more is False
    assert len(rig.library.song_requests) == 1


def test_liked_chip_ignores_stale_pages_from_a_dropped_chip(rig):
    make_lib(rig)
    rig.window.library_browser.chip_selected.emit("Me gusta")
    on_liked = rig.library.liked_requests[-1]
    rig.window.library_browser.chip_selected.emit("Canciones")
    on_liked([song(n) for n in range(LIKED_PAGE)])
    assert rig.window.library_browser._can_load_more is False


def test_switching_away_and_back_restarts_the_page_from_zero(rig):
    make_lib(rig)
    rig.window.library_browser.chip_selected.emit("Canciones")
    rig.library.song_requests[-1]([song(n) for n in range(SONGS_PAGE)])
    rig.window.library_browser.chip_selected.emit("Playlists")
    rig.window.library_browser.chip_selected.emit("Canciones")
    assert rig.library.limits[-1] == SONGS_PAGE
    rig.library.song_requests[-1]([song(n) for n in range(SONGS_PAGE)])
    assert rig.window.library_browser._can_load_more is True


def test_opening_a_ytmusic_playlist_navigates_instead_of_loading_it_all(rig):
    make_lib(rig)
    calls = []
    rig.navigator.playlist_requested.connect(calls.append)
    rig.window.library_browser.playlist_activated.emit({"playlistId": "p", "title": "Big", "source": "ytmusic"})
    assert calls == ["p"] and rig.queue.snapshot() == []


def test_no_session_liked_songs_never_offers_to_load_more(rig):
    make_lib(rig)
    rig.window.library_browser.chip_selected.emit("Me gusta")
    rig.library.liked_requests[-1](None)
    assert rig.window.library_browser._can_load_more is False


def test_library_browser_scroll_near_the_bottom_emits_load_more_once(qapp, wait_until):
    from ui.components.library_browser import LibraryBrowserPanel

    panel = LibraryBrowserPanel()
    panel.resize(400, 300)
    panel.show()
    calls = []
    panel.load_more_requested.connect(lambda: calls.append(1))
    panel.show_songs([song(n) for n in range(SONGS_PAGE)], None, has_more=True)
    bar = panel._scroll.verticalScrollBar()
    assert wait_until(lambda: bar.maximum() > 0)
    bar.setValue(bar.maximum())
    assert calls == [1]
    bar.setValue(0)
    bar.setValue(bar.maximum())
    assert calls == [1]
    panel.show_songs([song(n) for n in range(SONGS_PAGE)], None, has_more=False)
    QApplication.processEvents()
    bar.setValue(bar.maximum())
    assert calls == [1]



def test_tray_icon_click_brings_the_window_forward_and_reloads_home(rig):
    reloaded = []
    rig.window.home_requested.connect(lambda: reloaded.append(1))
    rig.window.hide()
    rig.window._on_tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
    assert rig.window.isVisible() and reloaded == [1]
    rig.window._on_tray_activated(QSystemTrayIcon.ActivationReason.Context)
    assert reloaded == [1]



def test_explore_extras_no_longer_include_popular_artists(qapp, wait_until):
    from infra.concurrency import TaskRunner
    from services.catalog_service import CatalogService

    class Gateway:
        is_authenticated = False

        def get_home(self, limit):
            return []

        def get_charts(self):
            return {"artists": [{"title": "Art", "browseId": "UC1", "thumbnails": []}],
                    "videos": [{"title": "Top", "playlistId": "PL1", "thumbnails": []}]}

        def get_explore(self):
            return {"trending": {}, "new_videos": [], "new_releases": []}

    runner = TaskRunner("no-artists", 1)
    service = CatalogService(Gateway(), runner)
    try:
        out = []
        service.load_home(out.append)
        assert wait_until(lambda: out)
        titles = [t for t, _ in out[0]]
        assert "Artistas populares" not in titles and "Listas de éxitos" in titles
    finally:
        runner.shutdown()



class FixedRandom:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def sample(self, seq, k):
        return list(seq)[:k]

    def shuffle(self, seq):
        pass


def test_reload_sometimes_swaps_the_first_two_shelves():
    from presenters.home_presenter import ALL_MOODS, HomePresenter

    sections = [("Vuelve a escucharlo", [1]), ("Selecciones rápidas", [2]), ("Otro", [3])]
    home = HomePresenter.__new__(HomePresenter)
    home._mood = ALL_MOODS
    home._rng = FixedRandom(0.0)
    home._first_swapped = home._should_reorder()
    assert home._ordered(sections) == [("Selecciones rápidas", [2]), ("Vuelve a escucharlo", [1]), ("Otro", [3])]
    assert home._ordered([("Solo", [1])]) == [("Solo", [1])]
    home._mood = "Fiesta"
    assert home._ordered(sections) == sections

    home._rng = FixedRandom(0.99)
    home._mood = ALL_MOODS
    home._first_swapped = home._should_reorder()
    assert home._ordered(sections) == sections


def rendered_titles(rig, presenter):
    shown = []
    presenter._panel.set_sections = lambda sections, *_a, **_k: shown.append([t for t, _ in sections])
    return shown


def test_reload_reorders_before_rendering(rig):
    from presenters.home_presenter import HomePresenter

    presenter = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier,
                                       rng=FixedRandom(0.0)))
    shown = rendered_titles(rig, presenter)
    presenter._sections = [("A", [song(1)]), ("B", [song(2)])]
    presenter._has_content = True
    presenter.reload()
    assert shown[0] == ["B", "A"]


def test_fresh_feed_after_reload_keeps_the_new_order(rig):
    from presenters.home_presenter import HomePresenter

    presenter = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier,
                                       rng=FixedRandom(0.0)))
    shown = rendered_titles(rig, presenter)
    presenter._sections = [("A", [song(1)]), ("B", [song(2)])]
    presenter._has_content = True
    presenter.reload()
    rig.catalog.home_calls[-1]["on_done"]([("A", [song(1)]), ("B", [song(2)]), ("C", [song(3)])])
    assert shown[-1] == ["B", "A", "C"]
