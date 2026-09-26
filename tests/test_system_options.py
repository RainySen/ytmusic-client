import json
import os
import sys

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon

from core.bootstrap import migrate_lyrics_file
from core.config import AppPaths
from domain.settings import CONTENT_LANGUAGES, LYRICS_PROVIDER_NAMES, Settings
from infra.autostart import BACKGROUND_FLAG, Autostart, launch_command
from infra.cache_store import CacheStore
from infra.media_keys import HOTKEY_BASE_ID, KEYS, MediaKeys
from infra.settings_repository import SettingsRepository
from presenters.explore_presenter import ExplorePresenter
from presenters.memory_presenter import MemoryPresenter
from presenters.settings_presenter import SettingsPresenter
from presenters.system_presenter import SystemPresenter
from services.lyrics_service import LyricsService
from services.settings_service import SettingsService
from tests.test_presenters import Rig
from ui.settings_dialog import SettingsDialog, format_size


@pytest.fixture(autouse=True)
def tray_present(monkeypatch):
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: True))


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def make_settings(tmp_path, **initial):
    service = SettingsService(SettingsRepository(str(tmp_path / "settings.json")))
    if initial:
        service.update(**initial)
    return service


def song(n=1):
    return {"videoId": f"v{n}", "title": f"Titulo {n}", "artists": [{"name": "Artista"}]}


def test_new_settings_have_safe_defaults_and_ignore_garbage():
    settings = Settings()
    assert not settings.start_with_windows and settings.media_keys and settings.notifications
    assert settings.content_language == "es" and settings.lyrics_providers == LYRICS_PROVIDER_NAMES
    garbage = Settings.from_dict({"content_language": "klingon", "lyrics_providers": "youtube", "better_lyrics_key": 7,
                                  "media_keys": "si", "start_with_windows": 1, "notifications": None})
    assert garbage == Settings()


def test_new_settings_roundtrip_and_sanitise():
    original = Settings(start_with_windows=True, content_language="ja", lyrics_providers=("youtube", "lrclib"),
                        better_lyrics_key="abc", media_keys=False, notifications=False)
    assert Settings.from_dict(json.loads(json.dumps(original.to_dict()))) == original
    cleaned = Settings.from_dict({"lyrics_providers": ["YouTube", "nope", "youtube", "lrclib"],
                                  "better_lyrics_key": "  k  "})
    assert cleaned.lyrics_providers == ("youtube", "lrclib") and cleaned.better_lyrics_key == "k"
    assert Settings.from_dict({"lyrics_providers": []}).lyrics_providers == ()
    assert all(Settings.from_dict({"content_language": code}).content_language == code for code in CONTENT_LANGUAGES)


def test_launch_command_for_the_installed_app_and_for_the_source_tree(tmp_path):
    installed = launch_command(True, r"C:\Apps\YTMusicClient.exe")
    assert installed == f'"C:\\Apps\\YTMusicClient.exe" {BACKGROUND_FLAG}'
    (tmp_path / "python.exe").write_text("")
    (tmp_path / "pythonw.exe").write_text("")
    source = launch_command(False, str(tmp_path / "python.exe"), r"C:\src\app.py")
    assert source == f'"{tmp_path / "pythonw.exe"}" "C:\\src\\app.py" {BACKGROUND_FLAG}'
    (tmp_path / "pythonw.exe").unlink()
    assert launch_command(False, str(tmp_path / "python.exe"), "app.py").startswith(f'"{tmp_path / "python.exe"}"')


@pytest.mark.skipif(sys.platform != "win32", reason="registro de windows")
def test_autostart_writes_and_removes_the_registry_entry():
    import winreg

    key = r"Software\YTMusicClientTests\Run"
    autostart = Autostart(key, "Probe")
    try:
        assert not autostart.is_enabled()
        assert autostart.set_enabled(False)
        assert autostart.set_enabled(True, '"C:\\x.exe" --background')
        assert autostart.is_enabled()
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
            assert winreg.QueryValueEx(handle, "Probe")[0] == '"C:\\x.exe" --background'
        assert autostart.set_enabled(False) and not autostart.is_enabled()
    finally:
        for name in (key, r"Software\YTMusicClientTests"):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, name)
            except OSError:
                pass


def test_autostart_reports_failure_and_is_off_without_windows(monkeypatch):
    autostart = Autostart(r"Software\YTMusicClientTests\Nope", "Probe")
    monkeypatch.setattr(Autostart, "available", property(lambda _self: False))
    assert not autostart.is_enabled() and not autostart.set_enabled(True)


class FakeHotkeys:
    def __init__(self, taken=()):
        self.taken, self.registered, self.removed = set(taken), {}, []

    def register(self, hotkey_id, key):
        if key in self.taken:
            return False
        self.registered[hotkey_id] = key
        return True

    def unregister(self, hotkey_id):
        self.removed.append(hotkey_id)


def test_media_keys_register_every_key_and_emit_the_matching_signal(qapp):
    hotkeys = FakeHotkeys()
    keys = MediaKeys(hotkeys)
    seen = []
    keys.play_pause.connect(lambda: seen.append("play"))
    keys.next_track.connect(lambda: seen.append("next"))
    keys.previous_track.connect(lambda: seen.append("prev"))
    assert keys.set_enabled(True) and keys.enabled and set(hotkeys.registered.values()) == set(KEYS.values())
    for offset in range(3):
        assert keys.handle(HOTKEY_BASE_ID + offset)
    assert sorted(seen) == ["next", "play", "prev"] and not keys.handle(1)
    assert keys.set_enabled(True)
    keys.set_enabled(False)
    assert not keys.enabled and sorted(hotkeys.removed) == sorted(hotkeys.registered) and not keys.handle(HOTKEY_BASE_ID)


def test_media_keys_survive_keys_taken_by_another_app_and_report_when_all_are_taken(qapp):
    partial = MediaKeys(FakeHotkeys(taken={KEYS["next"]}))
    assert partial.set_enabled(True) and len(partial._ids) == 2
    partial.set_enabled(False)
    none = MediaKeys(FakeHotkeys(taken=set(KEYS.values())))
    assert not none.set_enabled(True) and not none.enabled
    none.set_enabled(False)


def test_media_keys_do_nothing_without_a_hotkey_backend(qapp):
    keys = MediaKeys.__new__(MediaKeys)
    QObject.__init__(keys)
    keys._hotkeys, keys._ids, keys._filter = None, {}, None
    assert not keys.set_enabled(True)


class Keys(QObject):
    play_pause = Signal()
    next_track = Signal()
    previous_track = Signal()

    def __init__(self):
        super().__init__()
        self.state = []

    def set_enabled(self, enabled):
        self.state.append(enabled)
        return True


class FakeAutostart:
    available = True

    def __init__(self, enabled=False, works=True):
        self.enabled, self.works, self.calls = enabled, works, []

    def is_enabled(self):
        return self.enabled

    def set_enabled(self, enabled):
        self.calls.append(enabled)
        if self.works:
            self.enabled = enabled
        return self.works


def make_system(rig, tmp_path, autostart=None, **initial):
    service = make_settings(tmp_path, **initial)
    keys = Keys()
    shown = []
    rig.window.notify = lambda title, text: shown.append((title, text))
    system = rig.keep(SystemPresenter(rig.window, rig.playback, service, keys, autostart or FakeAutostart()))
    return system, service, keys, shown


def test_media_keys_drive_the_normal_player_controls(rig, tmp_path):
    system, _service, keys, _ = make_system(rig, tmp_path)
    calls = []
    rig.window.play_pause_clicked.connect(lambda: calls.append("play"))
    rig.window.next_clicked.connect(lambda: calls.append("next"))
    rig.window.previous_clicked.connect(lambda: calls.append("prev"))
    keys.play_pause.emit()
    keys.next_track.emit()
    keys.previous_track.emit()
    assert calls == ["play", "next", "prev"] and system is not None


def test_media_keys_follow_the_setting_and_only_react_to_real_changes(rig, tmp_path):
    system, service, keys, _ = make_system(rig, tmp_path)
    system.start()
    assert keys.state == [True]
    service.update(volume=30)
    service.update(media_keys=False)
    service.update(volume=31)
    service.update(media_keys=True)
    assert keys.state == [True, False, True]


def test_autostart_is_applied_on_start_and_when_toggled(rig, tmp_path):
    autostart = FakeAutostart()
    system, service, _keys, _ = make_system(rig, tmp_path, autostart, start_with_windows=True)
    system.start()
    assert autostart.enabled and autostart.calls == [True]
    service.update(start_with_windows=False)
    assert not autostart.enabled and autostart.calls == [True, False]


def test_autostart_is_left_alone_when_off_and_not_registered(rig, tmp_path):
    autostart = FakeAutostart()
    system, _service, _keys, _ = make_system(rig, tmp_path, autostart)
    system.start()
    assert autostart.calls == []


def test_autostart_that_cannot_be_written_turns_the_setting_back_off(rig, tmp_path):
    autostart = FakeAutostart(works=False)
    system, service, _keys, _ = make_system(rig, tmp_path, autostart)
    system.start()
    service.update(start_with_windows=True)
    assert autostart.calls == [True] and not service.settings.start_with_windows


def test_a_notification_appears_only_when_the_window_is_hidden_and_the_song_is_new(rig, tmp_path):
    _system, service, _keys, shown = make_system(rig, tmp_path)
    rig.playback.track_started.emit(song(1))
    assert shown == []
    rig.window.hide()
    rig.playback.track_started.emit(song(1))
    rig.playback.track_started.emit(song(1))
    rig.playback.track_started.emit(song(2))
    assert shown == [("Titulo 1", "Artista"), ("Titulo 2", "Artista")]
    service.update(notifications=False)
    rig.playback.track_started.emit(song(3))
    assert len(shown) == 2


def test_window_shows_tray_messages_only_when_a_tray_exists(rig, monkeypatch):
    shown = []
    monkeypatch.setattr(rig.window.tray_icon, "showMessage", lambda *args: shown.append(args))
    rig.window.notify("Titulo", "Artista")
    assert shown and shown[0][:2] == ("Titulo", "Artista")
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", staticmethod(lambda: False))
    rig.window.notify("otra", "cosa")
    assert len(shown) == 1


class FakeThumbnails:
    def __init__(self, size=0):
        self.size, self.cleared = size, 0

    def disk_size(self):
        return self.size

    def clear_disk(self):
        self.size = 0
        self.cleared += 1


def test_cache_store_sums_and_empties_directories_and_files(tmp_path):
    cache_dir = tmp_path / "yt"
    (cache_dir / "sub").mkdir(parents=True)
    (cache_dir / "a.bin").write_bytes(b"x" * 1000)
    (cache_dir / "sub" / "b.bin").write_bytes(b"x" * 500)
    home = tmp_path / "home.json"
    home.write_bytes(b"x" * 100)
    keep = tmp_path / "keep.json"
    keep.write_bytes(b"x" * 100)
    thumbs = FakeThumbnails(2000)
    store = CacheStore(thumbs, [str(cache_dir), str(tmp_path / "missing")], [str(home), str(tmp_path / "none.json")])
    assert store.size_bytes() == 2000 + 1500 + 100
    assert store.clear() == 3600
    assert thumbs.cleared == 1 and store.size_bytes() == 0
    assert cache_dir.exists() and not list(cache_dir.iterdir()) and not home.exists() and keep.exists()
    assert store.clear() == 0


def test_thumbnail_cache_reports_and_clears_its_disk_usage(qapp, tmp_path):
    from PySide6.QtCore import QUrl
    from PySide6.QtNetwork import QNetworkCacheMetaData

    from infra.thumbnail_cache import ThumbnailCache

    assert ThumbnailCache(None).disk_size() == 0
    cache = ThumbnailCache(str(tmp_path / "thumbs"))
    disk = cache._manager.cache()
    meta = QNetworkCacheMetaData()
    meta.setUrl(QUrl("http://t/1"))
    meta.setSaveToDisk(True)
    device = disk.prepare(meta)
    device.write(b"x" * 4096)
    disk.insert(device)
    cache._memory["http://t/1"] = object()
    assert cache.disk_size() >= 4096
    cache.clear_disk()
    assert cache.disk_size() == 0 and not cache._memory


def test_format_size_is_human_readable():
    assert format_size(0) == "0 KB" and format_size(2048) == "2 KB"
    assert format_size(5 * 1024 * 1024 + 300 * 1024) == "5,3 MB"
    assert format_size(3 * 1024 ** 3) == "3,00 GB"


def test_gateway_rebuilds_only_the_browse_client_when_the_language_changes(tmp_path, monkeypatch):
    import ytmusicapi

    from infra.ytmusic_gateway import YTMusicGateway

    built = []

    class Client:
        def __init__(self, auth=None, language="en", **_options):
            built.append(language)
            self.language = language

    monkeypatch.setattr(ytmusicapi, "YTMusic", Client)
    gateway = YTMusicGateway(str(tmp_path / "none.json"), "es")
    assert gateway._browse_client().language == "es"
    gateway.set_language("es")
    assert gateway._browse_client().language == "es" and built.count("es") == 1
    gateway.set_language("ja")
    assert gateway._browse_client().language == "ja"


def test_catalog_language_change_clears_caches_and_the_stored_home(tmp_path):
    from services.catalog_service import CatalogService

    class Gateway:
        language = None

        def set_language(self, language):
            self.language = language

    home = tmp_path / "home.json"
    home.write_text("[]")
    gateway = Gateway()
    catalog = CatalogService(gateway, runner=None, home_cache_file=str(home))
    catalog._cache.set("home", ["x"], 100)
    catalog.change_language("fr")
    assert gateway.language == "fr" and not home.exists() and catalog._cache.get("home") is None
    catalog.change_language("de")


def test_lyrics_service_switches_providers_and_forgets_old_results(qapp, wait_until):
    from infra.concurrency import TaskRunner
    from domain.models import LyricLine, Lyrics

    class Provider:
        def __init__(self, name, text):
            self.name, self.text, self.calls = name, text, 0

        def fetch(self, query):
            self.calls += 1
            return Lyrics([LyricLine(0, self.text)], True, self.name)

    old, new = Provider("Viejo", "a"), Provider("Nuevo", "b")
    runner = TaskRunner("lyrics-test", 1)
    service = LyricsService([old], runner)
    got = []
    track = {"videoId": "v1", "title": "T", "artists": [{"name": "A"}]}
    service.fetch(track, got.append)
    assert wait_until(lambda: len(got) == 1) and got[0].source == "Viejo"
    service.set_providers([new])
    service.fetch(track, got.append)
    assert wait_until(lambda: len(got) == 2) and got[1].source == "Nuevo"
    runner.shutdown()


def test_old_lyrics_file_is_migrated_once_into_the_settings(tmp_path):
    paths = AppPaths(str(tmp_path))
    paths.ensure_dirs()
    with open(paths.lyrics_settings_file, "w", encoding="utf-8") as handle:
        json.dump({"providers": ["youtube", "nonsense", "lrclib"], "better_lyrics_api_key": "vieja"}, handle)
    service = SettingsService(SettingsRepository(paths.settings_file))
    migrate_lyrics_file(paths, service)
    assert service.settings.lyrics_providers == ("youtube", "lrclib") and service.settings.better_lyrics_key == "vieja"
    assert not os.path.exists(paths.lyrics_settings_file) and os.path.exists(paths.lyrics_settings_file + ".migrated")
    assert SettingsRepository(paths.settings_file).load().better_lyrics_key == "vieja"
    migrate_lyrics_file(paths, service)


def test_editing_lyrics_options_updates_the_live_service_and_the_language_the_catalog(tmp_path):
    from tests.chaos.world import World

    world = World(str(tmp_path), 1, authenticated=False)
    world.paths.ensure_dirs()
    world.start(start_ui=False)
    try:
        services = world.services
        seen = []
        services.lyrics.set_providers = seen.append
        services.settings.update(volume=10)
        assert seen == []
        services.settings.update(lyrics_providers=("youtube",))
        services.settings.update(better_lyrics_key="k")
        assert len(seen) == 2
        services.settings.update(better_lyrics_key="k")
        assert len(seen) == 2
    finally:
        world.stop()


def test_a_saved_language_reaches_the_gateway_at_startup(tmp_path):
    from tests.chaos.world import World

    world = World(str(tmp_path), 1, authenticated=False)
    world.paths.ensure_dirs()
    SettingsRepository(world.paths.settings_file).save(Settings(content_language="pt"))
    world.start(start_ui=False)
    try:
        assert world.services.gateway._language == "pt"
    finally:
        world.stop()


def test_language_change_calls_the_handler_once_and_only_when_it_differs(rig, tmp_path):
    service = make_settings(tmp_path)
    changes = []
    rig.keep(SettingsPresenter(rig.window, service, on_language=changes.append))
    service.update(volume=20)
    service.update(content_language="en")
    service.update(content_language="en")
    service.update(content_language="es")
    assert changes == ["en", "es"]


def test_explore_invalidate_reloads_when_visible_and_defers_when_hidden(rig):
    presenter = ExplorePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier)
    rig.keep(presenter)
    loaded = []
    rig.catalog.load_explore = lambda on_done, on_error=None: loaded.append(on_done)
    presenter._sections = [("Estante", [song(1)])]
    rig.window.show_view("home")
    presenter.invalidate()
    assert presenter._sections == [] and loaded == [] and presenter._released
    presenter.show()
    assert len(loaded) == 1
    presenter._sections = [("Estante", [song(1)])]
    presenter.invalidate()
    assert len(loaded) == 2


def test_memory_presenter_can_start_hidden_and_respects_the_setting(rig, tmp_path):
    class View:
        def __init__(self):
            self.released = 0

        def release(self):
            self.released += 1

    service = make_settings(tmp_path, free_memory_seconds=10)
    presenter = rig.keep(MemoryPresenter(rig.window, View(), View(), settings=service))
    presenter.start_hidden()
    assert presenter._timer.isActive() and presenter._timer.interval() == 10_000
    presenter._timer.stop()
    service.update(free_memory=False)
    presenter.start_hidden()
    assert not presenter._timer.isActive()


def test_window_account_action_asks_to_log_in_or_confirms_the_logout(rig, monkeypatch):
    from ui import main_window

    events = []
    rig.window.login_requested.connect(lambda: events.append("login"))
    rig.window.logout_requested.connect(lambda: events.append("logout"))
    assert not rig.window.logged_in
    rig.window.account_action()
    rig.window.set_auth_state(True)
    assert rig.window.logged_in
    monkeypatch.setattr(main_window.dialogs, "confirm", lambda *a, **k: False)
    rig.window.account_action()
    monkeypatch.setattr(main_window.dialogs, "confirm", lambda *a, **k: True)
    rig.window.account_action()
    assert events == ["login", "logout"]


def make_dialog(rig, settings=None, **kwargs):
    changes = []
    dialog = SettingsDialog(rig.window, settings or Settings(), True, lambda **kw: changes.append(kw), **kwargs)
    return dialog, changes


def test_dialog_reports_the_new_simple_options(rig):
    dialog, changes = make_dialog(rig)
    dialog.autostart.setChecked(True)
    dialog.media_keys.setChecked(False)
    dialog.notifications.setChecked(False)
    dialog.language.setCurrentIndex(dialog.language.findData("ja"))
    assert changes == [{"start_with_windows": True}, {"media_keys": False}, {"notifications": False},
                       {"content_language": "ja"}]
    assert dialog.language.count() == len(CONTENT_LANGUAGES)
    dialog.deleteLater()


def test_dialog_disables_autostart_when_unavailable(rig):
    dialog, _ = make_dialog(rig, Settings(start_with_windows=True), autostart_available=False)
    assert not dialog.autostart.isEnabled() and not dialog.autostart.isChecked()
    dialog.deleteLater()


def test_dialog_lists_enabled_providers_first_in_their_saved_order(rig):
    dialog, _ = make_dialog(rig, Settings(lyrics_providers=("youtube", "betterlyrics")))
    assert dialog.provider_order() == ["youtube", "betterlyrics", "lrclib"]
    assert [n for n, s in dialog.provider_switches.items() if s.isChecked()] == ["youtube", "betterlyrics"]
    dialog.deleteLater()


def test_dialog_moves_and_toggles_providers_reporting_the_enabled_order(rig):
    dialog, changes = make_dialog(rig)
    dialog.move_provider("youtube", -1)
    assert dialog.provider_order() == ["betterlyrics", "youtube", "lrclib"]
    dialog.move_provider("betterlyrics", -1)
    dialog.move_provider("lrclib", 1)
    assert dialog.provider_order() == ["betterlyrics", "youtube", "lrclib"]
    dialog.provider_switches["youtube"].setChecked(False)
    assert changes[-1] == {"lyrics_providers": ("betterlyrics", "lrclib")}
    dialog.move_provider("lrclib", -1)
    assert changes[-1] == {"lyrics_providers": ("betterlyrics", "lrclib")}
    assert dialog.provider_order() == ["betterlyrics", "lrclib", "youtube"]
    dialog.deleteLater()


def test_dialog_saves_the_lyrics_key_when_editing_finishes_or_the_dialog_closes(rig):
    dialog, changes = make_dialog(rig, Settings(better_lyrics_key="vieja"))
    assert dialog.lyrics_key.text() == "vieja"
    dialog.lyrics_key.setText("  nueva  ")
    dialog.lyrics_key.editingFinished.emit()
    dialog.lyrics_key.editingFinished.emit()
    assert changes == [{"better_lyrics_key": "nueva"}]
    dialog.lyrics_key.setText("ultima")
    dialog.done(0)
    assert changes[-1] == {"better_lyrics_key": "ultima"} and len(changes) == 2


def test_dialog_shows_and_clears_the_cache(rig):
    state = {"size": 5 * 1024 * 1024}

    def clear():
        freed, state["size"] = state["size"], 0
        return freed

    dialog, _ = make_dialog(rig, cache_size=lambda: state["size"], clear_cache=clear)
    assert "Ocupa 5,0 MB" in dialog.cache_label.text() and dialog.cache_button.isEnabled()
    dialog.cache_button.click()
    assert "Ocupa 0 KB" in dialog.cache_label.text() and "Liberados 5,0 MB" in dialog.cache_label.text()
    dialog.deleteLater()
    unavailable, _ = make_dialog(rig)
    assert not unavailable.cache_button.isEnabled() and unavailable.cache_label.text() == ""
    unavailable.deleteLater()


def test_dialog_account_button_matches_the_session_and_closes_before_acting(rig):
    calls = []
    signed_in, _ = make_dialog(rig, logged_in=True, on_account=lambda: calls.append("action"))
    assert signed_in.account_button.text() == "Cerrar sesión"
    signed_in.account_button.click()
    assert calls == ["action"] and signed_in.result() == 1
    signed_out, _ = make_dialog(rig)
    assert signed_out.account_button.text() == "Iniciar sesión" and not signed_out.account_button.isEnabled()
    signed_out.deleteLater()


def test_settings_presenter_hands_the_cache_and_account_to_the_dialog(rig, tmp_path, monkeypatch, wait_until):
    cache = CacheStore(FakeThumbnails(3 * 1024 * 1024))
    presenter = rig.keep(SettingsPresenter(rig.window, make_settings(tmp_path), cache=cache, autostart_available=False))
    seen = []
    monkeypatch.setattr(SettingsDialog, "exec", lambda self: seen.append(
        (self.cache_label.text(), self.account_button.text(), self.autostart.isEnabled())))
    rig.window.set_auth_state(True)
    presenter.open()
    assert seen == [("Ocupa 3,0 MB.", "Cerrar sesión", False)]
    rig.window.set_auth_state(False)
    asked = []
    monkeypatch.setattr(rig.window, "account_action", lambda: asked.append(1))
    presenter._account_action()
    assert wait_until(lambda: asked == [1])
