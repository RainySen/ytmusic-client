import pytest
from PySide6.QtWidgets import QSystemTrayIcon

from domain.models import LyricLine, LyricWord, Lyrics, normalize_track
from domain.settings import Settings
from infra.concurrency import TaskRunner
from infra.romanization import UnisonRomanizer
from presenters.player_presenter import PlayerPresenter
from presenters.profile_presenter import ProfilePresenter
from services.library_service import CHANNEL_ID, LibraryService
from services.lyrics_service import LyricsService
from services.navigation import Navigator
from services.settings_service import SettingsService
from infra.settings_repository import SettingsRepository
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


def make_settings(tmp_path, **initial):
    service = SettingsService(SettingsRepository(str(tmp_path / "s.json")))
    if initial:
        service.update(**initial)
    return service


def song(n=1, **extra):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}], **extra}



class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self):
        return self._payload


def test_romanizer_posts_only_lines_missing_romanization_and_fills_them_in():
    calls = []

    def post(url, json):
        calls.append((url, json))
        return FakeResponse({"lines": [{"romanization": "konnichiwa"}]})

    romanizer = UnisonRomanizer("en", http_post=post)
    lyrics = Lyrics((LyricLine("a", 0), LyricLine("b", 1000, romanization="ya-tiene")), synced=True, source="x")
    out = romanizer.enrich(lyrics)
    assert calls[0][0] == UnisonRomanizer.URL
    assert calls[0][1] == {"lines": ["a"], "to": "en"}
    assert out.lines[0].romanization == "konnichiwa"
    assert out.lines[1].romanization == "ya-tiene"
    assert out.synced and out.source == "x"


def test_romanizer_leaves_lyrics_untouched_on_network_failure():
    def post(url, json):
        raise RuntimeError("down")

    romanizer = UnisonRomanizer("en", http_post=post)
    lyrics = Lyrics((LyricLine("a", 0),), synced=True)
    assert romanizer.enrich(lyrics) is lyrics


def test_romanizer_skips_empty_lines_and_giant_line_counts():
    calls = []
    romanizer = UnisonRomanizer("en", http_post=lambda *a, **k: calls.append(1) or FakeResponse({"lines": []}))
    assert romanizer.enrich(Lyrics((LyricLine(""),), synced=False)).lines[0].text == ""
    assert calls == []
    huge = Lyrics(tuple(LyricLine("x") for _ in range(201)), synced=False)
    assert romanizer.enrich(huge) is huge
    assert calls == []


def test_lyrics_service_applies_romanization_only_when_enabled(qapp, wait_until):
    romanized = Lyrics((LyricLine("a", 0, romanization="r"),), synced=True, source="p")

    class Romanizer:
        def __init__(self):
            self.calls = 0

        def enrich(self, lyrics):
            self.calls += 1
            return romanized

    class Provider:
        name = "p"

        def fetch(self, query):
            return Lyrics((LyricLine("a", 0),), synced=True, source="p")

    romanizer = Romanizer()
    runner = TaskRunner("lyr-rom", 1)
    service = LyricsService([Provider()], runner, romanizer=romanizer, romanize=True)
    try:
        got = []
        service.fetch(song(1), got.append)
        assert wait_until(lambda: got)
        assert got[0].lines[0].romanization == "r" and romanizer.calls == 1

        service.set_romanize(False)
        got2 = []
        service.fetch(song(1), got2.append)
        assert wait_until(lambda: got2)
        assert got2[0].lines[0].romanization == "" and romanizer.calls == 1
    finally:
        runner.shutdown()


def test_lyrics_service_tolerates_romanizer_errors(qapp, wait_until):
    class Boom:
        def enrich(self, lyrics):
            raise RuntimeError("boom")

    class Provider:
        name = "p"

        def fetch(self, query):
            return Lyrics((LyricLine("a", 0),), synced=True)

    runner = TaskRunner("lyr-boom", 1)
    service = LyricsService([Provider()], runner, romanizer=Boom(), romanize=True)
    try:
        got = []
        service.fetch(song(1), got.append)
        assert wait_until(lambda: got)
        assert got[0].lines[0].text == "a"
    finally:
        runner.shutdown()


def test_settings_default_and_dialog_toggle_for_romanization(rig):
    assert Settings().romanized_lyrics is True
    assert Settings.from_dict({"romanized_lyrics": "no"}).romanized_lyrics is True
    assert Settings.from_dict({"romanized_lyrics": False}).romanized_lyrics is False
    changes = []
    dialog = SettingsDialog(rig.window, Settings(), True, lambda **kw: changes.append(kw))
    dialog.romanized_lyrics.setChecked(False)
    assert changes[-1] == {"romanized_lyrics": False}
    dialog.deleteLater()


def test_side_panel_shows_romanization_under_plain_and_word_synced_lines(qapp):
    from ui.components.side_panel import SidePanel

    panel = SidePanel()
    panel.set_lyrics(Lyrics((LyricLine("hola", 0, romanization="hello"), LyricLine("sin", 1000)), synced=True))
    assert panel._lyrics.itemWidget(panel._lyrics.item(0)) is not None
    assert panel._lyrics.itemWidget(panel._lyrics.item(1)) is None
    assert panel._lyrics.item(1).text() == "sin"

    word = LyricLine("hi", 0, 1000, (LyricWord("hi", 0, 1000),), romanization="ro-ma-ji")
    panel.set_lyrics(Lyrics((word,), synced=True, source="s"))
    panel.set_lyric_progress(0, 0)
    label = panel._lyric_words[0][0]
    assert "ro-ma-ji" in label.text()



def test_queue_panel_starts_with_auto_queue_on_and_reports_toggles(rig):
    side = rig.window.side_panel
    assert side._auto_queue_switch.isChecked()
    seen = []
    side.auto_queue_toggled.connect(seen.append)
    side._auto_queue_switch.setChecked(False)
    assert seen == [False]


def test_set_auto_queue_does_not_re_emit_the_signal(rig):
    side = rig.window.side_panel
    seen = []
    side.auto_queue_toggled.connect(seen.append)
    side.set_auto_queue(False)
    assert seen == [] and not side._auto_queue_switch.isChecked()


def test_player_presenter_syncs_the_switch_with_settings_both_ways(rig, tmp_path):
    settings = make_settings(tmp_path, auto_queue=False)
    rig.keep(PlayerPresenter(rig.window, rig.playback, settings=settings))
    assert not rig.window.side_panel._auto_queue_switch.isChecked()
    rig.window.side_panel._auto_queue_switch.setChecked(True)
    assert settings.settings.auto_queue is True
    settings.update(auto_queue=False)
    assert not rig.window.side_panel._auto_queue_switch.isChecked()


def test_player_presenter_without_settings_leaves_the_switch_alone(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    assert rig.window.side_panel._auto_queue_switch.isChecked()



class FakeGateway:
    is_authenticated = True

    def __init__(self):
        self.history_calls = 0
        self.fail_history = False
        self.fail_artists = False

    def get_account_info(self):
        return {"accountName": "Rainy", "channelHandle": "@rainy", "accountPhotoUrl": "http://p/x"}

    def get_history(self):
        self.history_calls += 1
        if self.fail_history:
            raise RuntimeError("no history")
        return [{"videoId": "h1", "title": "H1", "artists": [{"name": "A"}]}]

    def get_library_artists(self, limit=8):
        if self.fail_artists:
            raise RuntimeError("no artists")
        return [{"browseId": "UC1", "artist": "Fav", "subscribers": "1", "thumbnails": []}]


def test_channel_profile_shape_and_graceful_partial_failures(qapp, wait_until):
    runner = TaskRunner("chan", 1)
    gateway = FakeGateway()
    service = LibraryService(gateway, None, None, runner)
    try:
        out = []
        service.channel_profile(out.append)
        assert wait_until(lambda: out)
        profile = out[0]
        assert profile["id"] == CHANNEL_ID and profile["name"] == "Rainy" and profile["subscribers"] == "@rainy"
        assert profile["banner"] == [{"url": "http://p/x"}]
        assert profile["top_songs"][0]["videoId"] == "h1"
        assert profile["sections"] == [("Tus artistas favoritos", [
            {"type": "artist", "browseId": "UC1", "title": "Fav", "subscribers": "1", "thumbnails": []}])]

        gateway.fail_history = True
        out2 = []
        service.channel_profile(out2.append)
        assert wait_until(lambda: out2)
        assert out2[0]["top_songs"] == []
    finally:
        runner.shutdown()


def test_channel_profile_needs_a_session(qapp, wait_until):
    class Gateway:
        is_authenticated = False

    runner = TaskRunner("chan2", 1)
    service = LibraryService(Gateway(), None, None, runner)
    try:
        out = []
        service.channel_profile(out.append)
        assert wait_until(lambda: out == [None])
    finally:
        runner.shutdown()


def make_profile_presenter(rig, library=None):
    navigator = Navigator()
    presenter = rig.keep(ProfilePresenter(rig.window, rig.catalog, rig.playback, rig.opener, navigator,
                                          rig.notifier, library=library))
    return presenter, navigator


def test_channel_requested_renders_the_artist_panel_from_the_library_profile(rig):
    profile = {"id": CHANNEL_ID, "name": "Rainy", "subscribers": "@rainy", "banner": [], "top_songs": [],
              "songs_title": "Escuchado recientemente", "songs_browse_id": "", "shuffle_id": "", "radio_id": "",
              "sections": []}

    class Library:
        def channel_profile(self, on_done):
            on_done(profile)

    _presenter, navigator = make_profile_presenter(rig, Library())
    navigator.channel_requested.emit()
    assert rig.window.current_view == "artist"


def test_channel_shuffle_and_mix_use_the_history_songs_without_a_fake_artist_call(rig):
    songs = [song(1), song(2), song(3)]
    profile = {"id": CHANNEL_ID, "name": "Rainy", "subscribers": "", "banner": [], "top_songs": songs,
              "songs_title": "x", "songs_browse_id": "", "shuffle_id": "", "radio_id": "", "sections": []}

    class Library:
        def channel_profile(self, on_done):
            on_done(profile)

    presenter, navigator = make_profile_presenter(rig, Library())
    navigator.channel_requested.emit()
    rig.window.artist_panel.shuffle_requested.emit()
    assert sorted(s["videoId"] for s in rig.queue.snapshot()) == ["v1", "v2", "v3"]
    rig.window.artist_panel.mix_requested.emit()
    assert rig.streams.requests[-1] in ("v1", "v2", "v3")
    assert presenter is not None


def test_channel_show_all_reuses_the_history_list_without_a_browse_id(rig):
    profile = {"id": CHANNEL_ID, "name": "Rainy", "subscribers": "", "banner": [], "top_songs": [song(1)],
              "songs_title": "Escuchado recientemente", "songs_browse_id": "", "shuffle_id": "", "radio_id": "",
              "sections": []}

    class Library:
        def channel_profile(self, on_done):
            on_done(profile)

    _presenter, navigator = make_profile_presenter(rig, Library())
    navigator.channel_requested.emit()
    rig.window.artist_panel.show_all_requested.emit()
    from PySide6.QtWidgets import QLabel
    assert any(w.text() == "Escuchado recientemente" for w in rig.window.artist_panel.findChildren(QLabel))


def test_channel_requested_fails_gracefully_without_a_session(rig):
    class Library:
        def channel_profile(self, on_done):
            on_done(None)

    _presenter, navigator = make_profile_presenter(rig, Library())
    navigator.channel_requested.emit()
    assert rig.window.current_view == "artist"


def test_main_window_account_menu_offers_channel_and_logout(rig, monkeypatch):
    shown = []
    monkeypatch.setattr(type(rig.window), "_show_account_menu", lambda _self, menu: shown.append(
        [a.text() for a in menu.actions() if a.text()]))
    rig.window.set_auth_state(True)
    rig.window.account_action()
    assert shown == [["Tu canal", "Cerrar sesión"]]


def test_main_window_channel_menu_item_emits_channel_requested(rig, monkeypatch):
    def fake_show(_self, menu):
        action = next(a for a in menu.actions() if a.text() == "Tu canal")
        action.trigger()

    monkeypatch.setattr(type(rig.window), "_show_account_menu", fake_show)
    seen = []
    rig.window.channel_requested.connect(lambda: seen.append(1))
    rig.window.set_auth_state(True)
    rig.window.account_action()
    assert seen == [1]


def test_main_window_logout_menu_item_still_confirms(rig, monkeypatch):
    def fake_show(_self, menu):
        action = next(a for a in menu.actions() if a.text() == "Cerrar sesión")
        action.trigger()

    monkeypatch.setattr(type(rig.window), "_show_account_menu", fake_show)
    from ui import main_window
    monkeypatch.setattr(main_window.dialogs, "confirm", lambda *a, **k: True)
    seen = []
    rig.window.logout_requested.connect(lambda: seen.append(1))
    rig.window.set_auth_state(True)
    rig.window.account_action()
    assert seen == [1]


def test_artist_panel_songs_heading_uses_the_profile_title(qapp):
    from ui.components.artist_panel import ArtistPanel

    class Thumbs:
        def request(self, url, callback):
            pass

    panel = ArtistPanel()
    panel.show_profile({"id": "x", "name": "N", "top_songs": [normalize_track(song(1))],
                        "songs_title": "Escuchado recientemente", "sections": []}, Thumbs())
    from PySide6.QtWidgets import QLabel
    assert any(w.text() == "Escuchado recientemente" for w in panel.findChildren(QLabel))



def autoplay_rig(radio_size=5):
    from domain.play_queue import PlayQueue
    from services.playback_service import PlaybackService
    from tests.fakes import FakeAudio, FakeCatalog, FakeNotifier, FakeStreams

    state = {"on": True}
    catalog = FakeCatalog()
    queue = PlayQueue(radio_limit=None)
    playback = PlaybackService(queue, FakeStreams(), FakeAudio(), catalog, FakeNotifier(),
                               radio_size=lambda: radio_size, auto_queue=lambda: state["on"])
    return playback, queue, catalog, state


def ids(queue):
    return [s["videoId"] for s in queue.snapshot()]


def test_turning_autoplay_off_drops_only_the_suggestions_still_to_play(qapp):
    playback, queue, _catalog, state = autoplay_rig()
    playback.play_collection([song(1), song(2)])
    queue.extend_unique([song(3), song(4)], auto=True)
    queue.append_many([song(5)])
    state["on"] = False
    playback.set_auto_queue(False)
    assert ids(queue) == ["v1", "v2", "v5"]


def test_turning_autoplay_on_refills_from_the_last_song_with_the_chosen_size(qapp):
    playback, queue, catalog, state = autoplay_rig(radio_size=5)
    playback.play_collection([song(1), song(2)])
    playback.set_auto_queue(True)
    call = catalog.calls[-1]
    assert call["video_id"] == "v2" and call["key"] == "extend"
    catalog.answer(len(catalog.calls) - 1, [song(n) for n in (2, 10, 11, 12, 13, 14, 15, 16)])
    assert ids(queue) == ["v1", "v2", "v10", "v11", "v12", "v13", "v14"]
    state["on"] = False
    playback.set_auto_queue(False)
    assert ids(queue) == ["v1", "v2"]


def test_suggestions_arriving_after_autoplay_is_off_are_ignored(qapp):
    playback, queue, catalog, state = autoplay_rig()
    playback.play_collection([song(1)])
    playback.set_auto_queue(True)
    state["on"] = False
    catalog.answer(len(catalog.calls) - 1, [song(9)])
    assert ids(queue) == ["v1"]


def test_changing_the_setting_reaches_the_playback_service(tmp_path, monkeypatch):
    from core import bootstrap
    from core.config import AppPaths
    from tests.chaos.world import ChaosAudio

    monkeypatch.setattr(bootstrap, "VlcAudioBackend", ChaosAudio)
    monkeypatch.setattr(bootstrap, "build_romanizer", lambda: None)
    services = bootstrap.build_services(AppPaths(str(tmp_path)))
    seen = []
    monkeypatch.setattr(services.playback, "set_auto_queue", seen.append)
    try:
        services.settings.update(auto_queue=False)
        services.settings.update(radio_size=10)
        services.settings.update(auto_queue=True)
        assert seen == [False, True]
    finally:
        services.shutdown()
