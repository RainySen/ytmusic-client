import pytest
from PySide6.QtTest import QTest

from infra import memory
from infra.thumbnail_cache import ThumbnailCache
from presenters.explore_presenter import ExplorePresenter
from presenters.home_presenter import HomePresenter
from presenters.memory_presenter import MemoryPresenter
from tests.test_presenters import SECTIONS, Rig

@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


FRESH = [("Fresh", [{"type": "song", "videoId": "v9", "title": "N", "artists": []}])]


class MemoryRig:
    def __init__(self, rig):
        self.rig = rig
        rig.catalog.stored = SECTIONS
        self.home = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
        self.explore = rig.keep(ExplorePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
        rig.catalog.explore_calls = []
        rig.catalog.load_explore = lambda on_done, on_error=None: rig.catalog.explore_calls.append(on_done)
        self.cleared = []
        rig.window.thumbnails = type("T", (), {"clear_memory": lambda _s: self.cleared.append(1), "request": lambda *_a: None})()
        self.memory = rig.keep(MemoryPresenter(rig.window, self.home, self.explore, delay_ms=10))


def test_home_button_reloads_feed_resets_mood_and_scrolls_to_top(rig):
    home = HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier)
    rig.keep(home)
    home.start()
    rig.catalog.home_calls[-1]["on_done"](SECTIONS)
    home.select_mood("Fiesta")
    rig.window.show_view("library")
    before = len(rig.catalog.home_calls)
    rig.window.home_requested.emit()
    assert rig.window.home_panel.isVisible()
    assert home._mood == "Todos" and rig.catalog.home_calls[-1]["force"] is True
    assert len(rig.catalog.home_calls) == before + 1
    checked = [c.text() for c in rig.window.home_panel._chips if c.isChecked()]
    assert checked == ["Todos"]
    assert rig.window.home_panel.feed._built
    rig.catalog.home_calls[-1]["on_done"](FRESH)
    assert rig.window.home_panel.feed._built


def test_home_button_reloads_even_when_already_on_home(rig):
    home = HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier)
    rig.keep(home)
    home.start()
    calls = len(rig.catalog.home_calls)
    rig.window.home_requested.emit()
    rig.window.home_requested.emit()
    assert len(rig.catalog.home_calls) == calls + 2


def test_home_and_explore_are_released_when_hidden_and_restored_when_shown(rig):
    m = MemoryRig(rig)
    m.home.start()
    rig.catalog.home_calls[-1]["on_done"](SECTIONS)
    assert rig.window.home_panel.feed._built
    rig.window.hide()
    assert m.memory._timer.isActive()
    QTest.qWait(80)
    assert m.memory._released and m.cleared == [1]
    assert not rig.window.home_panel.feed._built and m.home._released
    calls = len(rig.catalog.home_calls)
    rig.window.show()
    assert not m.memory._released and not m.home._released
    assert rig.window.home_panel.feed._built
    assert len(rig.catalog.home_calls) == calls + 1 and rig.catalog.home_calls[-1]["force"] is False


def test_showing_again_before_the_delay_keeps_everything(rig):
    m = MemoryRig(rig)
    m.home.start()
    rig.catalog.home_calls[-1]["on_done"](SECTIONS)
    rig.window.hide()
    rig.window.show()
    QTest.qWait(80)
    assert not m.memory._released and m.cleared == [] and rig.window.home_panel.feed._built


def test_minimizing_also_counts_as_background(rig):
    m = MemoryRig(rig)
    rig.window.showMinimized()
    QTest.qWait(80)
    assert m.memory._released
    rig.window.showNormal()
    assert not m.memory._released


def test_explore_is_rendered_again_after_being_released(rig):
    m = MemoryRig(rig)
    rig.window.explore_requested.emit()
    m.explore._on_shelves(SECTIONS)
    assert rig.window.explore_panel.feed._built
    rig.window.hide()
    QTest.qWait(80)
    assert not rig.window.explore_panel.feed._built
    rig.window.show()
    assert rig.window.explore_panel.feed._built and not m.explore._released


def test_queue_widgets_are_dropped_and_rebuilt_on_demand(rig):
    m = MemoryRig(rig)
    songs = [{"videoId": f"v{n}", "title": f"T{n}", "artists": []} for n in range(30)]
    side = rig.window.side_panel
    rig.window.toggle_now_playing()
    side.set_queue(songs, 2, rig.window.thumbnails)
    assert side._queue_layout.count() > 1
    rig.window.hide()
    QTest.qWait(80)
    assert side._queue_layout.count() == 1 and m.memory._released


def test_thumbnail_cache_memory_can_be_cleared_but_keeps_working(qapp, tmp_path):
    cache = ThumbnailCache(str(tmp_path))
    cache._memory["http://x/1"] = object()
    cache.clear_memory()
    assert len(cache._memory) == 0


def test_memory_trim_never_raises():
    memory.trim()


def test_every_click_on_the_sidebar_home_button_forces_a_reload(rig):
    home = HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier)
    rig.keep(home)
    home.start()
    rig.catalog.home_calls[-1]["on_done"](SECTIONS)
    button = rig.window.sidebar.nav_buttons["Inicio"]
    calls = len(rig.catalog.home_calls)
    for _ in range(3):
        button.click()
    assert len(rig.catalog.home_calls) == calls + 3
    assert all(call["force"] is True for call in rig.catalog.home_calls[calls:])


def songs(n, start=0):
    return [{"type": "song", "videoId": f"v{k}", "title": f"T{k}", "artists": []} for k in range(start, start + n)]


def make_swap_home(rig, seed=3):
    import random

    home = HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, rng=random.Random(seed))
    rig.keep(home)
    home.start()
    shelves = [("Vuelve a escucharlo", songs(10)), ("Albumes", [{"type": "album", "browseId": "MPREb_1", "title": "A"}])]
    rig.catalog.home_calls[-1]["on_done"](shelves)
    return home, shelves


def ids_of(home, title):
    return [i.get("videoId") for t, items in home._sections if t == title for i in items]


def test_reload_keeps_the_feed_visible_and_asks_for_recommendations_of_recent_songs(rig):
    home, _ = make_swap_home(rig)
    rig.window.home_requested.emit()
    assert rig.window.home_panel.feed._built and rig.window.home_panel.feed._message.isHidden()
    call = rig.catalog.pool_calls[-1]
    assert len(call["seeds"]) == 2 and set(call["seeds"]) <= {f"v{k}" for k in range(10)}
    assert rig.catalog.home_calls[-1]["force"] is True


def test_recommendations_replace_some_songs_with_new_ones(rig):
    home, shelves = make_swap_home(rig)
    rig.window.home_requested.emit()
    before = ids_of(home, "Vuelve a escucharlo")
    rig.catalog.pool_calls[-1]["on_done"](songs(30, start=100))
    after = ids_of(home, "Vuelve a escucharlo")
    kept = set(before) & set(after)
    assert len(after) == len(before) == 10 and len(set(after)) == 10
    assert 4 <= len(kept) <= 8 and any(i.startswith("v1") and len(i) == 4 for i in after)
    assert ids_of(home, "Albumes") == [None]


def test_swaps_survive_the_fresh_feed_arriving_later(rig):
    home, shelves = make_swap_home(rig)
    rig.window.home_requested.emit()
    rig.catalog.pool_calls[-1]["on_done"](songs(30, start=100))
    swapped = ids_of(home, "Vuelve a escucharlo")
    rig.catalog.home_calls[-1]["on_done"](shelves)
    assert ids_of(home, "Vuelve a escucharlo") == swapped


def test_recommendations_arriving_after_the_fresh_feed_still_apply(rig):
    home, shelves = make_swap_home(rig)
    rig.window.home_requested.emit()
    rig.catalog.home_calls[-1]["on_done"](shelves)
    rig.catalog.pool_calls[-1]["on_done"](songs(30, start=100))
    assert set(ids_of(home, "Vuelve a escucharlo")) != {f"v{k}" for k in range(10)}


def test_every_reload_swaps_different_songs_and_empty_recommendations_change_nothing(rig):
    home, shelves = make_swap_home(rig)
    rig.window.home_requested.emit()
    rig.catalog.pool_calls[-1]["on_done"]([])
    assert ids_of(home, "Vuelve a escucharlo") == [f"v{k}" for k in range(10)]
    rig.window.home_requested.emit()
    rig.catalog.home_calls[-1]["on_done"](shelves)
    rig.catalog.pool_calls[-1]["on_done"](songs(30, start=100))
    first = ids_of(home, "Vuelve a escucharlo")
    rig.window.home_requested.emit()
    rig.catalog.home_calls[-1]["on_done"](shelves)
    rig.catalog.pool_calls[-1]["on_done"](songs(30, start=200))
    second = ids_of(home, "Vuelve a escucharlo")
    assert first != second and not (set(first) & set(second) & {f"v{k}" for k in range(100, 130)})


def test_small_shelves_and_pool_duplicates_are_left_alone(rig):
    import random

    home = HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, rng=random.Random(1))
    rig.keep(home)
    home.start()
    rig.catalog.home_calls[-1]["on_done"]([("Corta", songs(3))])
    rig.window.home_requested.emit()
    rig.catalog.pool_calls[-1]["on_done"](songs(10, start=100))
    assert ids_of(home, "Corta") == ["v0", "v1", "v2"]


def test_reload_without_content_shows_loading_and_skips_recommendations(rig):
    home = HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier)
    rig.keep(home)
    rig.window.home_requested.emit()
    assert rig.window.home_panel.feed._message.text() == "Cargando…" and rig.catalog.pool_calls == []


def test_recommendations_prefetched_in_the_background_make_the_next_click_instant(rig):
    home, shelves = make_swap_home(rig)
    prefetch = rig.catalog.pool_calls[-1]
    assert len(prefetch["seeds"]) == 2
    prefetch["on_done"](songs(30, start=100))
    before = ids_of(home, "Vuelve a escucharlo")
    calls = len(rig.catalog.pool_calls)
    rig.window.home_requested.emit()
    after = ids_of(home, "Vuelve a escucharlo")
    assert after != before and any(len(i) == 4 for i in after)
    assert len(rig.catalog.pool_calls) == calls + 1
    rig.catalog.pool_calls[-1]["on_done"](songs(30, start=200))
    rig.window.home_requested.emit()
    assert any(i.startswith("v2") and len(i) == 4 for i in ids_of(home, "Vuelve a escucharlo"))


def test_prefetch_is_not_repeated_while_one_is_pending_or_when_the_pool_is_empty(rig):
    home, shelves = make_swap_home(rig)
    calls = len(rig.catalog.pool_calls)
    rig.catalog.home_calls[-1]["on_done"](shelves)
    assert len(rig.catalog.pool_calls) == calls
    rig.catalog.pool_calls[-1]["on_done"]([])
    assert home._pool_ready is None



def test_visible_window_is_cleaned_only_while_idle_or_in_the_background(qapp, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from infra.settings_repository import SettingsRepository
    from services.settings_service import SettingsService

    rig = Rig()
    try:
        settings = SettingsService(SettingsRepository(str(tmp_path / "s.json")))
        settings.update(free_memory=True, free_memory_seconds=60)
        home = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
        explore = rig.keep(ExplorePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
        presenter = rig.keep(MemoryPresenter(rig.window, home, explore, settings=settings))
        assert presenter._idle_timer.isActive() and presenter._idle_timer.interval() == 60_000
        freed = []
        monkeypatch.setattr(presenter, "free_now", lambda: freed.append(1))
        monkeypatch.setattr(QApplication, "activeWindow", staticmethod(lambda: rig.window))
        monkeypatch.setattr(memory, "idle_seconds", lambda: 5.0)
        presenter._on_idle_tick()
        assert freed == []
        monkeypatch.setattr(memory, "idle_seconds", lambda: 61.0)
        presenter._on_idle_tick()
        monkeypatch.setattr(memory, "idle_seconds", lambda: 0.0)
        monkeypatch.setattr(QApplication, "activeWindow", staticmethod(lambda: None))
        presenter._on_idle_tick()
        assert freed == [1, 1]
        settings.update(free_memory=False)
        assert not presenter._idle_timer.isActive()
    finally:
        rig.dispose()
