import pytest
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from domain.settings import DEFAULT_RADIO_SIZE, FREE_MEMORY_OPTIONS, RADIO_SIZE_OPTIONS, Settings
from infra.settings_repository import SettingsRepository
from presenters.memory_presenter import MemoryPresenter
from presenters.mini_player_presenter import MiniPlayerPresenter
from presenters.settings_presenter import SettingsPresenter
from services.settings_service import SettingsService
from tests.test_presenters import Rig
from ui.settings_dialog import SettingsDialog


@pytest.fixture(autouse=True)
def tray_present(monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def make_settings(tmp_path):
    return SettingsService(SettingsRepository(str(tmp_path / "settings.json")))


def song(n=1):
    return {"videoId": f"v{n}", "title": f"Titulo {n}", "artists": [{"name": "Artista"}]}


def test_defaults_are_the_documented_ones():
    settings = Settings()
    assert settings.background_on_close and settings.mini_player and settings.free_memory
    assert settings.radio_size == DEFAULT_RADIO_SIZE and settings.remember_volume and settings.restore_queue
    assert settings.volume == 100 and settings.mini_x is None


@pytest.mark.parametrize("raw", [None, [], "texto", 7, {"radio_size": 7, "free_memory_seconds": "20", "volume": 500,
                                                           "mini_player": "si", "mini_x": True}])
def test_garbage_settings_fall_back_to_defaults(raw):
    assert Settings.from_dict(raw) == Settings()


def test_valid_values_are_kept_and_roundtrip():
    original = Settings(background_on_close=False, mini_player=False, mini_x=10, mini_y=-4, auto_queue=False, radio_size=500,
                        free_memory=False, free_memory_seconds=60, remember_volume=False, volume=35, restore_queue=False)
    assert Settings.from_dict(original.to_dict()) == original
    assert all(Settings.from_dict({"radio_size": size}).radio_size == size for size in RADIO_SIZE_OPTIONS)
    assert all(Settings.from_dict({"free_memory_seconds": s}).free_memory_seconds == s for s in FREE_MEMORY_OPTIONS)


def test_unknown_setting_is_rejected():
    with pytest.raises(KeyError):
        Settings().with_changes(tema="claro")


def test_dialog_reports_every_change_immediately(rig):
    changes = []
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: changes.append(kw))
    dialog.mini.setChecked(False)
    dialog.background.setChecked(False)
    dialog.radio.setCurrentIndex(dialog.radio.findData(200))
    dialog.free_memory.setChecked(False)
    dialog.free_seconds.setCurrentIndex(dialog.free_seconds.findData(60))
    dialog.remember_volume.setChecked(False)
    dialog.restore_queue.setChecked(False)
    assert changes == [{"mini_player": False}, {"background_on_close": False}, {"radio_size": 200},
                       {"free_memory": False}, {"free_memory_seconds": 60}, {"remember_volume": False},
                       {"restore_queue": False}]
    dialog.deleteLater()


def test_dialog_shows_the_current_values_and_unlimited_radio(rig):
    settings = Settings(radio_size=0, free_memory_seconds=180, mini_player=False)
    dialog = SettingsDialog(rig.window, settings, True, lambda **kw: None)
    assert dialog.radio.currentData() == 0 and "Ilimitada" in dialog.radio.currentText()
    assert dialog.free_seconds.currentData() == 180 and not dialog.mini.isChecked()
    dialog.deleteLater()


def test_dialog_disables_background_option_without_tray(rig):
    dialog = SettingsDialog(rig.window, Settings(), False, lambda **kw: None)
    assert not dialog.background.isEnabled() and not dialog.background.isChecked()
    dialog.deleteLater()


def test_closing_the_window_respects_the_background_setting(rig, tmp_path, monkeypatch):
    service = make_settings(tmp_path)
    rig.keep(SettingsPresenter(rig.window, service))
    quits = []
    monkeypatch.setattr(QApplication, "quit", staticmethod(lambda: quits.append(1)))
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))
    rig.window.close()
    assert not rig.window.isVisible() and quits == []
    rig.window.show()
    service.update(background_on_close=False)
    rig.window.close()
    assert quits == [1]


def test_closing_quits_when_the_system_has_no_tray(rig, tmp_path, monkeypatch):
    rig.keep(SettingsPresenter(rig.window, make_settings(tmp_path)))
    quits = []
    monkeypatch.setattr(QApplication, "quit", staticmethod(lambda: quits.append(1)))
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))
    rig.window.close()
    assert quits == [1]


def test_volume_is_saved_after_a_pause_and_restored_on_start(rig, tmp_path):
    service = make_settings(tmp_path)
    presenter = rig.keep(SettingsPresenter(rig.window, service))
    rig.window.player_panel.volume_slider.setValue(40)
    assert service.settings.volume == 100
    QTest.qWait(800)
    assert service.settings.volume == 40
    restored = make_settings(tmp_path)
    other = Rig()
    try:
        SettingsPresenter(other.window, restored).start()
        assert other.window.volume == 40
    finally:
        other.dispose()
    assert presenter is not None


def test_volume_is_not_saved_or_restored_when_remembering_is_off(rig, tmp_path):
    service = make_settings(tmp_path)
    service.update(remember_volume=False, volume=25)
    presenter = rig.keep(SettingsPresenter(rig.window, service))
    presenter.start()
    assert rig.window.volume != 25
    rig.window.player_panel.volume_slider.setValue(70)
    QTest.qWait(800)
    assert service.settings.volume == 25


def test_settings_button_opens_the_dialog_with_the_current_values(rig, tmp_path, monkeypatch):
    service = make_settings(tmp_path)
    service.update(radio_size=200)
    rig.keep(SettingsPresenter(rig.window, service))
    opened = []
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: opened.append(self.radio.currentData()))
    rig.window.top_bar.settings_button.click()
    assert opened == [200]


def make_mini(rig, tmp_path):
    service = make_settings(tmp_path)
    presenter = rig.keep(MiniPlayerPresenter(rig.window, rig.playback, service))
    return presenter, service


def test_mini_player_appears_when_the_window_is_hidden_and_a_song_is_loaded(rig, tmp_path):
    presenter, _ = make_mini(rig, tmp_path)
    rig.queue.replace([song(1), song(2)], 0)
    rig.playback.track_loading.emit(song(1))
    assert not presenter.mini.isVisible()
    rig.window.hide()
    assert presenter.mini.isVisible() and presenter.mini._title.text() == "Titulo 1"
    rig.window.show()
    assert not presenter.mini.isVisible()
    presenter.mini.hide()


def test_mini_player_needs_a_song_and_can_be_disabled(rig, tmp_path):
    presenter, service = make_mini(rig, tmp_path)
    rig.window.hide()
    assert not presenter.mini.isVisible()
    rig.queue.replace([song(1)], 0)
    rig.playback.track_started.emit(song(1))
    assert presenter.mini.isVisible()
    service.update(mini_player=False)
    assert not presenter.mini.isVisible()
    service.update(mini_player=True)
    assert presenter.mini.isVisible()
    presenter.mini.hide()


def test_mini_player_buttons_use_the_normal_player_controls(rig, tmp_path):
    presenter, _ = make_mini(rig, tmp_path)
    spies = {name: QSignalSpy(getattr(rig.window, name)) for name in ("play_pause_clicked", "next_clicked", "previous_clicked")}
    mini = presenter.mini
    mini._toggle.click()
    mini._next.click()
    mini._previous.click()
    assert all(spy.count() == 1 for spy in spies.values())
    rig.playback.playing_changed.emit(True)
    rig.playback.progress.emit(0.5)
    assert mini._progress.value() == 500


def test_mini_player_close_button_hides_it_until_the_window_comes_back(rig, tmp_path):
    presenter, _ = make_mini(rig, tmp_path)
    rig.queue.replace([song(1), song(2)], 0)
    rig.playback.track_loading.emit(song(1))
    rig.window.hide()
    assert presenter.mini.isVisible()
    presenter.mini._close.click()
    assert not presenter.mini.isVisible()
    rig.playback.track_started.emit(song(2))
    assert not presenter.mini.isVisible()
    rig.window.show()
    rig.window.hide()
    assert presenter.mini.isVisible()
    presenter.mini.hide()


def test_mini_player_expand_restores_the_window_and_position_is_remembered(rig, tmp_path):
    presenter, service = make_mini(rig, tmp_path)
    rig.queue.replace([song(1)], 0)
    rig.window.hide()
    presenter.mini.moved.emit(150, 260)
    assert (service.settings.mini_x, service.settings.mini_y) == (150, 260)
    presenter.mini.hide()
    rig.window.hide()
    rig.playback.track_started.emit(song(1))
    assert (presenter.mini.x(), presenter.mini.y()) == (150, 260)
    presenter.mini._expand.click()
    assert rig.window.isVisible() and not presenter.mini.isVisible()


class Home:
    released = 0

    def release(self):
        Home.released += 1

    def show(self):
        pass


class Explore(Home):
    pass


def test_memory_is_released_only_when_the_setting_is_on_and_after_the_chosen_wait(rig, tmp_path):
    service = make_settings(tmp_path)
    service.update(free_memory_seconds=60)
    Home.released = 0
    memory = rig.keep(MemoryPresenter(rig.window, Home(), Explore(), settings=service))
    rig.window.hide()
    assert memory._timer.isActive() and memory._timer.interval() == 60_000
    rig.window.show()
    service.update(free_memory=False)
    rig.window.hide()
    assert not memory._timer.isActive()
    rig.window.show()


def test_new_services_read_the_radio_size_from_the_saved_settings(tmp_path):
    import os
    import tempfile

    from tests.chaos.world import World

    tmp = tempfile.mkdtemp()
    with open(os.path.join(tmp, "settings.json"), "w", encoding="utf-8"):
        pass
    world = World(tmp, 1, authenticated=False)
    world.paths.ensure_dirs()
    SettingsRepository(world.paths.settings_file).save(Settings(radio_size=200))
    world.start(start_ui=False)
    try:
        assert world.services.queue.radio_limit == 200 and world.services.settings.settings.radio_size == 200
        assert world.services.playback._radio_size() == 200
    finally:
        world.stop()


def test_dialog_free_ram_button_reports_the_result_and_is_disabled_without_a_handler(rig):
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: None, lambda: (300, 120))
    dialog.free_button.click()
    assert dialog.free_button.isEnabled() and "Liberados 180 MB" in dialog.free_result.text()
    dialog.deleteLater()
    unavailable = SettingsDialog(rig.window, Settings(), True, lambda **kw: None)
    assert not unavailable.free_button.isEnabled()
    unavailable.deleteLater()
    grew = SettingsDialog(rig.window, Settings(), True, lambda **kw: None, lambda: (100, 130))
    grew.free_button.click()
    assert "Liberados 0 MB" in grew.free_result.text()
    grew.deleteLater()


def test_free_now_releases_hidden_views_and_keeps_the_visible_one(rig, tmp_path):
    class View:
        def __init__(self):
            self.released = 0

        def release(self):
            self.released += 1

    home, explore = View(), View()
    cleared = []
    rig.window.thumbnails = type("T", (), {"clear_memory": lambda _s: cleared.append(1), "request": lambda *_a: None})()
    memory_presenter = rig.keep(MemoryPresenter(rig.window, home, explore, settings=make_settings(tmp_path)))
    rig.window.show_view("home")
    before, after = memory_presenter.free_now()
    assert (home.released, explore.released) == (0, 1) and cleared == [1]
    assert isinstance(before, int) and isinstance(after, int)
    rig.window.show_view("library")
    memory_presenter.free_now()
    assert (home.released, explore.released) == (1, 2)


def test_free_now_button_is_wired_through_the_settings_presenter(rig, tmp_path, monkeypatch):
    seen = []
    presenter = rig.keep(SettingsPresenter(rig.window, make_settings(tmp_path), free_now=lambda: (10, 5)))
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: seen.append(self.free_button.isEnabled()))
    presenter.open()
    assert seen == [True]


def test_working_set_and_trim_are_safe_to_call():
    from infra import memory

    assert memory.working_set_mb() >= 0
    memory.trim()


def test_dialog_has_a_bounded_size_and_scrolls_its_content(rig):
    from PySide6.QtWidgets import QScrollArea

    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: None)
    screen = QApplication.primaryScreen().availableGeometry()
    assert dialog.height() <= 560 and dialog.height() <= screen.height()
    assert dialog.width() == 540
    scroll = dialog.findChild(QScrollArea)
    assert scroll is not None and scroll.widget().sizeHint().height() > 0
    dialog.deleteLater()


def test_turning_background_off_switches_the_mini_player_off_and_locks_it(rig):
    changes = []
    dialog = SettingsDialog(rig.window, Settings(mini_player=True), True, lambda **kw: changes.append(kw))
    assert dialog.mini.isChecked() and dialog.mini.isEnabled()
    dialog.background.setChecked(False)
    assert not dialog.mini.isChecked() and not dialog.mini.isEnabled()
    assert changes == [{"background_on_close": False}]
    dialog.background.setChecked(True)
    assert dialog.mini.isChecked() and dialog.mini.isEnabled()
    assert changes == [{"background_on_close": False}, {"background_on_close": True}]
    dialog.deleteLater()


def test_the_mini_player_choice_is_remembered_while_it_is_locked(rig):
    dialog = SettingsDialog(rig.window, Settings(mini_player=False), True, lambda **kw: None)
    dialog.background.setChecked(False)
    dialog.background.setChecked(True)
    assert not dialog.mini.isChecked() and dialog.mini.isEnabled()
    dialog.mini.setChecked(True)
    dialog.background.setChecked(False)
    dialog.background.setChecked(True)
    assert dialog.mini.isChecked()
    dialog.deleteLater()


def test_dialog_opens_with_the_mini_player_locked_when_background_is_already_off(rig):
    dialog = SettingsDialog(rig.window, Settings(background_on_close=False, mini_player=True), True, lambda **kw: None)
    assert not dialog.mini.isChecked() and not dialog.mini.isEnabled()
    without_tray = SettingsDialog(rig.window, Settings(), False, lambda **kw: None)
    assert not without_tray.mini.isChecked() and not without_tray.mini.isEnabled()
    dialog.deleteLater()
    without_tray.deleteLater()


def test_the_mini_player_never_shows_when_background_is_off_or_the_system_has_no_tray(rig, tmp_path, monkeypatch):
    presenter, service = make_mini(rig, tmp_path)
    rig.queue.replace([song(1)], 0)
    rig.window.hide()
    rig.playback.track_started.emit(song(1))
    assert presenter.mini.isVisible()
    service.update(background_on_close=False)
    assert not presenter.mini.isVisible()
    service.update(background_on_close=True)
    assert presenter.mini.isVisible()
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))
    service.update(mini_player=True, radio_size=25)
    assert not presenter.mini.isVisible()
    presenter.mini.hide()
