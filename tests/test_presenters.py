import pytest
import qtawesome as qta
from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from domain.models import LyricLine, Lyrics
from domain.play_queue import PlayQueue
from presenters.auth_presenter import AuthPresenter
from presenters.home_presenter import HomePresenter
from presenters.library_presenter import LibraryPresenter
from presenters.lyrics_presenter import LyricsPresenter
from presenters.player_presenter import PlayerPresenter
from presenters.playlist_presenter import PlaylistPresenter
from presenters.search_presenter import SearchPresenter
from presenters.similar_presenter import SimilarPresenter
from services.playback_service import PlaybackService
from tests.fakes import FakeAudio, FakeCatalog, FakeNotifier, FakeStreams
from ui.components.section_feed import CompactSection
from ui.main_window import MainWindow


class NullThumbnails:
    def request(self, url, callback):
        pass


def song(n, **extra):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}], **extra}


class ScriptedCatalog(FakeCatalog):
    def __init__(self):
        super().__init__()
        self.stored = None
        self.home_calls = []
        self.mood_calls = []
        self.search_calls = []
        self.related_calls = []
        self.playlist_calls = []
        self.cleared = 0

    def stored_home(self):
        return self.stored

    def load_home(self, on_done, on_error=None, force=False):
        self.home_calls.append({"on_done": on_done, "on_error": on_error, "force": force})

    def load_mood(self, mood, on_done):
        self.mood_calls.append({"mood": mood, "on_done": on_done})

    def search(self, query, on_done, on_error=None):
        self.search_calls.append({"query": query, "on_done": on_done, "on_error": on_error})

    def related(self, video_id, on_done, on_error=None):
        self.related_calls.append({"video_id": video_id, "on_done": on_done, "on_error": on_error})

    def playlist(self, playlist_id, on_done, on_error=None):
        self.playlist_calls.append({"id": playlist_id, "on_done": on_done, "on_error": on_error})

    def clear_cache(self):
        self.cleared += 1


class FakeAuth(QObject):
    auth_changed = Signal(bool)
    session_expired = Signal()

    def __init__(self):
        super().__init__()
        self.is_authenticated = False
        self.logouts = 0
        self.verifications = 0

    def verify_session(self):
        self.verifications += 1

    def logout(self):
        self.logouts += 1
        self.is_authenticated = False
        self.auth_changed.emit(False)
        return True


class FakeLibrary:
    def __init__(self):
        self.playlist_requests = []
        self.song_requests = []
        self.saved = []
        self.imported = []
        self.target_requests = []
        self.added = []
        self.artist_list = [{"name": "X", "count": 2}]

    def playlists(self, on_done):
        self.playlist_requests.append(on_done)

    def songs(self, on_done):
        self.song_requests.append(on_done)

    def artists(self):
        return self.artist_list

    def playlist_tracks(self, entry, on_done, on_error=None):
        on_done({"title": entry["title"], "tracks": [song(1), song(2)]})

    def save_playlist(self, title, tracks, *, cloud, on_done):
        self.saved.append((title, [t["videoId"] for t in tracks], cloud))
        on_done((True, cloud))

    def save_targets(self, on_done):
        self.target_requests.append(on_done)

    def add_to_playlist(self, entry, track, on_done):
        self.added.append((entry["playlistId"], [t["videoId"] for t in track]))
        on_done(self.add_outcome)

    add_outcome = "added"

    def save_imported(self, title, tracks, *, cloud, on_done):
        self.imported.append((title, cloud))
        on_done(("YouTube Music" if cloud else "local", True))


class Rig:
    def __init__(self):
        self.window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
        self.window.resize(1200, 700)
        self.window.show()
        self.notifier = FakeNotifier()
        self.catalog = ScriptedCatalog()
        self.audio = FakeAudio()
        self.streams = FakeStreams()
        self.queue = PlayQueue()
        self.playback = PlaybackService(self.queue, self.streams, self.audio, self.catalog, self.notifier)
        self.opened = []
        self.opener = type("Opener", (), {"open": lambda _self, item: self.opened.append(item)})()
        self.library = FakeLibrary()
        self.auth = FakeAuth()
        self._alive = []

    def dispose(self):
        self.window.close()
        self.window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def keep(self, presenter):
        self._alive.append(presenter)
        return presenter


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def test_show_view_switches_panels_and_nav(rig):
    w = rig.window
    w.show_view("search")
    assert w.search_panel.isVisible() and not w.home_panel.isVisible()
    w.show_view("library")
    assert w.library_browser.isVisible() and not w.search_panel.isVisible()


def test_now_playing_toggle_restores_previous_view(rig):
    w = rig.window
    w.show_view("library")
    w.toggle_now_playing()
    assert w.now_playing_panel.isVisible() and w.side_panel.isVisible() and not w.library_browser.isVisible()
    w.toggle_now_playing()
    assert w.library_browser.isVisible() and not w.now_playing_panel.isVisible()


def test_window_emits_transport_signals(rig):
    w = rig.window
    spies = {name: QSignalSpy(getattr(w, name)) for name in
             ("play_pause_clicked", "next_clicked", "previous_clicked", "loop_clicked")}
    w.player_panel.play_button.click()
    w.player_panel.next_button.click()
    w.player_panel.prev_button.click()
    w.player_panel.loop_button.click()
    assert all(spy.count() == 1 for spy in spies.values())


def test_window_search_submit_and_blank_ignored(rig):
    w = rig.window
    spy = QSignalSpy(w.search_submitted)
    w.top_bar.search_box.setText("   ")
    w._submit_search()
    assert spy.count() == 0
    w.top_bar.search_box.setText(" daft punk ")
    w._submit_search()
    assert spy.at(0) == ["daft punk"]


def test_window_toast_shows_message(rig):
    rig.window.show_toast("error", "boom")
    assert rig.window._toast.isVisible() and rig.window._toast.text() == "boom"


def test_progress_slider_not_fought_while_dragging(rig):
    slider = rig.window.player_panel.progress_slider
    slider.setSliderDown(True)
    rig.window.set_progress(0.9)
    assert slider.value() == 0
    slider.setSliderDown(False)
    rig.window.set_progress(0.5)
    assert slider.value() == 500


SECTIONS = [("Quick", [{"type": "song", "videoId": "v1", "title": "S", "artists": []}])]


def make_home(rig):
    return rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))


def test_home_shows_stored_feed_instantly_then_refreshes(rig):
    rig.catalog.stored = SECTIONS
    home = make_home(rig)
    home.start()
    assert rig.window.home_panel.feed._built and rig.window.home_panel.feed._layout.count() > 1
    assert rig.catalog.home_calls[-1]["force"] is True
    fresh = [("Fresh", [{"type": "song", "videoId": "v2", "title": "N", "artists": []}])]
    rig.catalog.home_calls[-1]["on_done"](fresh)
    assert home._has_content


def test_home_shows_loading_without_stored_feed(rig):
    home = make_home(rig)
    home.start()
    assert rig.window.home_panel.feed._message.text() == "Cargando…"


def test_home_error_without_content_shows_message(rig):
    home = make_home(rig)
    home.start()
    rig.catalog.home_calls[-1]["on_error"](RuntimeError("offline"))
    assert "No se pudo cargar" in rig.window.home_panel.feed._message.text()


def test_home_error_with_content_only_warns(rig):
    rig.catalog.stored = SECTIONS
    home = make_home(rig)
    home.start()
    rig.catalog.home_calls[-1]["on_error"](RuntimeError("offline"))
    assert rig.notifier.messages[-1][0] == "warning"


def test_mood_result_for_a_previous_selection_is_ignored(rig):
    home = make_home(rig)
    home.start()
    home.select_mood("Fiesta")
    home.select_mood("Romance")
    rig.catalog.mood_calls[0]["on_done"]([("Late", [{"type": "song", "videoId": "x", "title": "x", "artists": []}])])
    assert rig.window.home_panel.feed._message.text() == "Cargando…"
    rig.catalog.mood_calls[1]["on_done"](SECTIONS)
    assert home._has_content


def test_returning_to_all_moods_reloads_home(rig):
    home = make_home(rig)
    home.start()
    home.select_mood("Fiesta")
    calls = len(rig.catalog.home_calls)
    home.select_mood("Todos")
    assert len(rig.catalog.home_calls) == calls + 1 and rig.catalog.home_calls[-1]["force"] is False


def test_home_feed_ignored_while_a_mood_is_selected(rig):
    home = make_home(rig)
    home.start()
    home.select_mood("Fiesta")
    rig.catalog.home_calls[0]["on_done"](SECTIONS)
    assert rig.window.home_panel.feed._message.text() == "Cargando…"


def test_empty_mood_shows_message(rig):
    home = make_home(rig)
    home.start()
    home.select_mood("Fiesta")
    rig.catalog.mood_calls[0]["on_done"]([])
    assert "Fiesta" in rig.window.home_panel.feed._message.text()


def test_refresh_keeps_the_selected_mood(rig):
    home = make_home(rig)
    home.start()
    home.select_mood("Fiesta")
    home.refresh(force=True)
    assert len(rig.catalog.mood_calls) == 2 and home._mood == "Fiesta"


def test_home_routes_clicks_to_opener_and_playback(rig):
    make_home(rig)
    item = {"type": "playlist", "playlistId": "p"}
    rig.window.home_panel.item_clicked.emit(item)
    assert rig.opened == [item]
    rig.window.home_panel.add_queue_clicked.emit(song(1))
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v1"]
    rig.window.home_panel.play_all_requested.emit([song(5), song(6)])
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v5", "v6"]


def test_search_flow_and_error(rig):
    rig.keep(SearchPresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
    rig.window.search_submitted.emit("daft punk")
    assert rig.window.search_panel.isVisible()
    call = rig.catalog.search_calls[-1]
    assert call["query"] == "daft punk"
    call["on_done"]({"top_result": None, "songs": [], "more": []})
    assert "Sin resultados" in rig.window.search_panel._layout.itemAt(0).widget().text()
    rig.window.search_submitted.emit("again")
    rig.catalog.search_calls[-1]["on_error"](RuntimeError("x"))
    assert rig.notifier.messages[-1] == ("error", "Error de búsqueda.")


def test_library_ignores_stale_tab_results(rig):
    rig.keep(LibraryPresenter(rig.window, rig.library, rig.playback, rig.opener, rig.notifier))
    rig.window.library_requested.emit()
    assert rig.window.library_browser.isVisible()
    playlists_answer = rig.library.playlist_requests[-1]
    rig.window.library_browser.chip_selected.emit("Canciones")
    playlists_answer([{"playlistId": "p", "title": "P", "source": "local"}])
    assert "Cargando" in rig.window.library_browser._layout.itemAt(0).widget().text()
    rig.library.song_requests[-1]([song(1)])
    assert rig.window.library_browser._layout.count() == 2


def test_library_artists_are_synchronous(rig):
    rig.keep(LibraryPresenter(rig.window, rig.library, rig.playback, rig.opener, rig.notifier))
    rig.window.library_browser.chip_selected.emit("Artistas")
    assert rig.window.library_browser._chips["Artistas"].isChecked()


def test_library_playlist_activation_plays_it(rig):
    rig.keep(LibraryPresenter(rig.window, rig.library, rig.playback, rig.opener, rig.notifier))
    rig.window.library_browser.playlist_activated.emit({"playlistId": "p", "title": "Mine", "source": "local"})
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v1", "v2"]
    assert rig.streams.requests == ["v1"]


def test_player_reflects_loading_then_playing(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.queue.replace([song(1), song(2)], 0)
    rig.playback.play_track(rig.queue.current)
    assert rig.window.player_panel.song_label.text() == "Cargando: T1"
    rig.streams.resolve("v1")
    assert rig.window.player_panel.song_label.text() == "T1"
    assert rig.window.player_panel.play_button.icon().cacheKey() == rig.window.icons["pause"].cacheKey()


def test_player_queue_list_follows_queue(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.queue.replace([song(1), song(2), song(3)], 1)
    assert rig.window.side_panel._queue_count.text() == "(3)"
    rig.window.side_panel.queue_item_removed.emit(0)
    assert rig.window.side_panel._queue_count.text() == "(2)"


def test_player_controls_drive_playback(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.queue.replace([song(1), song(2)], 0)
    rig.playback.play_track(rig.queue.current)
    rig.streams.resolve("v1")
    rig.window.next_clicked.emit()
    assert rig.streams.requests[-1] == "v2"
    rig.window.seek_requested.emit(0.25)
    rig.window.volume_changed.emit(30)
    assert rig.audio.seeks == [0.25] and rig.audio.volume == 30
    rig.window.side_panel.queue_item_activated.emit(0)
    assert rig.streams.requests[-1] == "v1"


def test_player_start_shows_restored_song_without_playing(rig):
    presenter = PlayerPresenter(rig.window, rig.playback)
    rig.queue.restore([song(1), song(2)], 1)
    presenter.start()
    assert rig.window.player_panel.song_label.text() == "T2"
    assert rig.streams.requests == [] and rig.audio.volume == rig.window.volume


def test_loop_mode_icon_follows_queue(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.window.loop_clicked.emit()
    assert "Cola" in rig.window.player_panel.loop_button.toolTip()


def test_clear_confirmed_keeps_only_current(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.queue.replace([song(1), song(2), song(3)], 1)
    rig.window.queue_clear_confirmed.emit()
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v2"]


class FakeLyrics:
    def __init__(self):
        self.calls = []

    def fetch(self, video_id, on_done, on_error=None):
        self.calls.append((video_id, on_done, on_error))


def timed(*pairs):
    return Lyrics(tuple(LyricLine(text, ms) for text, ms in pairs), synced=True)


def test_lyrics_highlight_follows_time_including_seeking_back(rig):
    lyrics = FakeLyrics()
    rig.keep(LyricsPresenter(rig.window, rig.playback, lyrics))
    rig.queue.replace([song(1)], 0)
    rig.playback.play_track(rig.queue.current)
    lyrics.calls[-1][1](timed(("a", 1000), ("b", 5000), ("c", 9000)))
    panel = rig.window.side_panel
    rig.playback.time_ms.emit(5500)
    assert panel._lyrics.currentRow() == 1
    rig.playback.time_ms.emit(9500)
    assert panel._lyrics.currentRow() == 2
    rig.playback.time_ms.emit(1200)
    assert panel._lyrics.currentRow() == 0


def test_lyrics_for_a_skipped_song_are_ignored(rig):
    lyrics = FakeLyrics()
    rig.keep(LyricsPresenter(rig.window, rig.playback, lyrics))
    rig.queue.replace([song(1), song(2)], 0)
    rig.playback.play_track(song(1))
    rig.queue.jump_to(1)
    rig.playback.play_track(song(2))
    lyrics.calls[0][1](timed(("old", 1000)))
    assert rig.window.side_panel._lyrics.item(0).text() == "…"
    lyrics.calls[1][1](None)
    assert rig.window.side_panel._lyrics.item(0).text() == "Letra no encontrada."


def test_unsynced_lyrics_do_not_highlight(rig):
    lyrics = FakeLyrics()
    rig.keep(LyricsPresenter(rig.window, rig.playback, lyrics))
    rig.playback.play_track(song(1))
    lyrics.calls[-1][1](Lyrics((LyricLine("x"), LyricLine("y")), synced=False))
    rig.playback.time_ms.emit(3000)
    assert rig.window.side_panel._lyrics.currentRow() == -1


def test_lyrics_error_shows_not_found(rig):
    lyrics = FakeLyrics()
    rig.keep(LyricsPresenter(rig.window, rig.playback, lyrics))
    rig.playback.play_track(song(1))
    lyrics.calls[-1][2](RuntimeError("x"))
    assert rig.window.side_panel._lyrics.item(0).text() == "Letra no encontrada."


def test_similar_item_click_goes_to_opener(rig):
    rig.keep(SimilarPresenter(rig.window, rig.catalog, rig.playback, rig.opener))
    item = {"type": "playlist", "playlistId": "p"}
    rig.window.side_panel.similar_item_chosen.emit(item)
    assert rig.opened == [item]


def make_playlists(rig):
    return rig.keep(PlaylistPresenter(rig.window, rig.catalog, rig.library, rig.playback, rig.auth, rig.notifier))


def test_import_rejects_invalid_url(rig):
    make_playlists(rig)
    rig.window.import_url_submitted.emit("https://example.com/nothing")
    assert rig.notifier.messages[-1][0] == "error" and rig.catalog.playlist_calls == []


def test_import_plays_and_saves_locally(rig, monkeypatch):
    make_playlists(rig)
    monkeypatch.setattr(rig.window, "ask_save_target", lambda title, auth: "local")
    rig.window.import_url_submitted.emit("https://music.youtube.com/playlist?list=PLabc")
    call = rig.catalog.playlist_calls[-1]
    assert call["id"] == "PLabc"
    call["on_done"]({"title": "Mix", "tracks": [song(1), song(2)]})
    assert rig.streams.requests == ["v1"]
    assert rig.library.imported == [("Mix", False)]
    assert rig.notifier.messages[-1] == ("info", "«Mix» guardada en local.")


def test_import_can_be_declined(rig, monkeypatch):
    make_playlists(rig)
    monkeypatch.setattr(rig.window, "ask_save_target", lambda title, auth: None)
    rig.window.import_url_submitted.emit("https://music.youtube.com/playlist?list=PLabc")
    rig.catalog.playlist_calls[-1]["on_done"]({"title": "Mix", "tracks": [song(1)]})
    assert rig.library.imported == []


def test_import_empty_or_failed(rig):
    make_playlists(rig)
    rig.window.import_url_submitted.emit("https://music.youtube.com/playlist?list=PLabc")
    rig.catalog.playlist_calls[-1]["on_done"](None)
    assert rig.notifier.messages[-1][0] == "error"
    rig.window.import_url_submitted.emit("https://music.youtube.com/playlist?list=PLxyz")
    rig.catalog.playlist_calls[-1]["on_error"](RuntimeError("x"))
    assert rig.notifier.messages[-1][0] == "error"


def test_save_queue_as_playlist(rig):
    make_playlists(rig)
    rig.queue.replace([song(1), song(2)], 0)
    rig.window.queue_save_requested.emit("Mi Cola")
    assert rig.library.saved == [("Mi Cola", ["v1", "v2"], False)]
    assert rig.notifier.messages[-1] == ("info", "«Mi Cola» guardada en local.")


def test_save_empty_queue_warns(rig):
    make_playlists(rig)
    rig.window.queue_save_requested.emit("X")
    assert rig.notifier.messages[-1] == ("warning", "La cola está vacía.") and rig.library.saved == []


def test_save_queue_reports_partial_cloud_failure(rig):
    make_playlists(rig)
    rig.auth.is_authenticated = True
    rig.library.save_playlist = lambda title, tracks, *, cloud, on_done: on_done((True, False))
    rig.queue.replace([song(1)], 0)
    rig.window.queue_save_requested.emit("Q")
    assert rig.notifier.messages[-1][0] == "warning"


def test_auth_change_refreshes_state_and_content(rig):
    home = make_home(rig)
    home.start()
    rig.keep(AuthPresenter(rig.window, rig.auth, rig.catalog, home, lambda: None, rig.notifier))
    before = len(rig.catalog.home_calls)
    rig.auth.auth_changed.emit(True)
    assert rig.window._logged_in is True and rig.catalog.cleared == 1
    assert len(rig.catalog.home_calls) == before + 1 and rig.catalog.home_calls[-1]["force"] is True


def test_logout_reports(rig):
    home = make_home(rig)
    rig.keep(AuthPresenter(rig.window, rig.auth, rig.catalog, home, lambda: None, rig.notifier))
    rig.window.logout_requested.emit()
    assert rig.auth.logouts == 1 and rig.notifier.messages[-1] == ("info", "Sesión cerrada.")


def test_login_window_opened_once_and_closed_on_success(rig):
    home = make_home(rig)
    created = []

    class FakeLogin(QObject):
        login_success = Signal()
        login_skipped = Signal()

        def __init__(self):
            super().__init__()
            self.closed = False
            created.append(self)

        def show(self):
            pass

        def raise_(self):
            pass

        def activateWindow(self):
            pass

        def close(self):
            self.closed = True

    presenter = AuthPresenter(rig.window, rig.auth, rig.catalog, home, FakeLogin, rig.notifier)
    rig.window.login_requested.emit()
    rig.window.login_requested.emit()
    assert len(created) == 1
    created[0].login_success.emit()
    assert created[0].closed and rig.notifier.messages[-1] == ("info", "Sesión iniciada.")
    rig.window.login_requested.emit()
    assert len(created) == 2 and presenter._login_window is created[1]


def test_hovering_a_song_preloads_its_stream(rig):
    make_home(rig)
    rig.window.home_panel.item_hovered.emit(song(9))
    rig.window.home_panel.item_hovered.emit({"type": "playlist", "playlistId": "p"})
    assert rig.streams.prefetched == ["v9"]


def test_hover_preload_from_search_and_library(rig):
    rig.keep(SearchPresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
    rig.keep(LibraryPresenter(rig.window, rig.library, rig.playback, rig.opener, rig.notifier))
    rig.window.search_panel.item_hovered.emit(song(1))
    rig.window.library_browser.song_hovered.emit(song(2))
    assert rig.streams.prefetched == ["v1", "v2"]


from presenters.explore_presenter import ExplorePresenter


class ExploreCatalog(ScriptedCatalog):
    def __init__(self):
        super().__init__()
        self.explore_calls = []
        self.mood_playlist_calls = []

    def load_explore(self, on_done, on_error=None):
        self.explore_calls.append({"on_done": on_done, "on_error": on_error})

    def mood_playlists(self, params, on_done, on_error=None):
        self.mood_playlist_calls.append({"params": params, "on_done": on_done, "on_error": on_error})


def explore_rig(rig):
    rig.catalog = ExploreCatalog()
    rig.playback._catalog = rig.catalog
    return rig.keep(ExplorePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))


SHELVES = [
    ("Álbumes y sencillos nuevos", [{"type": "album", "title": "A", "browseId": "MPREb_1", "thumbnails": []}]),
    ("Tendencias", [{"type": "song", "videoId": "v1", "title": "T", "artists": [], "thumbnails": []}]),
    ("Estados de ánimo y géneros", [{"type": "mood", "title": "Calma", "params": "p"}]),
]


def test_explore_opens_loads_once_and_renders(rig):
    explore_rig(rig)
    rig.window.explore_requested.emit()
    assert rig.window.explore_panel.isVisible() and len(rig.catalog.explore_calls) == 1
    assert rig.window.explore_panel.feed._message.text() == "Cargando…"
    rig.catalog.explore_calls[0]["on_done"](SHELVES)
    assert len(rig.window.explore_panel.feed._built) >= 1
    rig.window.explore_requested.emit()
    assert len(rig.catalog.explore_calls) == 1


def test_explore_no_longer_runs_a_search(rig):
    explore_rig(rig)
    rig.keep(SearchPresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier))
    rig.window.explore_requested.emit()
    assert rig.catalog.search_calls == []


def test_explore_error_message(rig):
    explore_rig(rig)
    rig.window.explore_requested.emit()
    rig.catalog.explore_calls[0]["on_error"](RuntimeError("x"))
    assert "No se pudo cargar" in rig.window.explore_panel.feed._message.text()


def test_explore_mood_opens_playlists_with_back_button(rig):
    explore_rig(rig)
    rig.window.explore_requested.emit()
    rig.catalog.explore_calls[0]["on_done"](SHELVES)
    panel = rig.window.explore_panel
    panel.item_clicked.emit({"type": "mood", "title": "Calma", "params": "p"})
    assert rig.catalog.mood_playlist_calls[-1]["params"] == "p"
    assert panel._back.isVisible() and not panel._jump_row.isVisible()
    playlists = [{"type": "playlist", "playlistId": f"p{i}", "title": f"P{i}", "thumbnails": []} for i in range(40)]
    rig.catalog.mood_playlist_calls[-1]["on_done"](playlists)
    assert len(panel.feed._built) + len(panel.feed._pending) == 3
    panel.back_requested.emit()
    assert not panel._back.isVisible() and panel._jump_row.isVisible()
    assert len(rig.catalog.explore_calls) == 1


def test_explore_stale_mood_result_is_ignored(rig):
    explore_rig(rig)
    rig.window.explore_requested.emit()
    rig.catalog.explore_calls[0]["on_done"](SHELVES)
    panel = rig.window.explore_panel
    panel.item_clicked.emit({"type": "mood", "title": "Calma", "params": "p"})
    panel.back_requested.emit()
    rig.catalog.mood_playlist_calls[-1]["on_done"]([{"type": "playlist", "playlistId": "x", "title": "x", "thumbnails": []}])
    assert not panel._back.isVisible()


def test_explore_other_items_go_to_opener_and_jump_buttons_reveal(rig):
    explore_rig(rig)
    rig.window.explore_requested.emit()
    rig.catalog.explore_calls[0]["on_done"](SHELVES)
    panel = rig.window.explore_panel
    album = {"type": "album", "browseId": "MPREb_1"}
    panel.item_clicked.emit(album)
    assert rig.opened == [album]
    revealed = []
    panel.feed.reveal = revealed.append
    panel.jump_requested.emit(2)
    assert revealed == [2]


def test_explore_hover_preloads_trending_songs(rig):
    explore_rig(rig)
    rig.window.explore_panel.item_hovered.emit(song(4))
    assert rig.streams.prefetched == ["v4"]


def test_shuffle_button_shuffles_the_queue(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.queue.replace([song(i) for i in range(12)], 0)
    before = [s["videoId"] for s in rig.queue.snapshot()]
    import random
    random.seed(3)
    rig.window.player_panel.shuffle_button.click()
    after = [s["videoId"] for s in rig.queue.snapshot()]
    assert after[0] == "v0" and sorted(after) == sorted(before) and after != before


RELATED = {
    "songs": [dict(song(i), type="song") for i in range(20)],
    "playlists": [{"type": "playlist", "playlistId": f"p{i}", "title": f"P{i}", "thumbnails": []} for i in range(6)],
    "artists": [{"type": "artist", "browseId": f"UC{i}", "title": f"A{i}", "thumbnails": []} for i in range(6)],
}


def similar_rig(rig):
    return rig.keep(SimilarPresenter(rig.window, rig.catalog, rig.playback, rig.opener))


def test_similar_is_not_fetched_until_the_tab_is_opened(rig):
    similar_rig(rig)
    rig.queue.replace([song(1)], 0)
    rig.playback.play_track(song(1))
    assert rig.catalog.related_calls == []
    rig.window.side_panel._select_tab(2)
    assert [c["video_id"] for c in rig.catalog.related_calls] == ["v1"]


def test_similar_result_is_cached_for_the_same_song(rig):
    similar_rig(rig)
    rig.playback.play_track(song(1))
    panel = rig.window.side_panel
    panel._select_tab(2)
    rig.catalog.related_calls[0]["on_done"](RELATED)
    panel._select_tab(0)
    panel._select_tab(2)
    assert len(rig.catalog.related_calls) == 1
    assert panel._similar_layout.count() == 4


def test_similar_cache_is_dropped_when_the_track_changes(rig):
    similar_rig(rig)
    rig.playback.play_track(song(1))
    panel = rig.window.side_panel
    panel._select_tab(2)
    rig.catalog.related_calls[0]["on_done"](RELATED)
    rig.playback.play_track(song(2))
    assert [c["video_id"] for c in rig.catalog.related_calls] == ["v1", "v2"]
    assert panel._similar_layout.count() == 2
    panel._select_tab(0)
    rig.playback.play_track(song(3))
    assert len(rig.catalog.related_calls) == 2
    panel._select_tab(2)
    assert rig.catalog.related_calls[-1]["video_id"] == "v3"


def test_similar_ignores_an_answer_for_a_previous_song(rig):
    similar_rig(rig)
    rig.playback.play_track(song(1))
    panel = rig.window.side_panel
    panel._select_tab(2)
    rig.playback.play_track(song(2))
    rig.catalog.related_calls[0]["on_done"](RELATED)
    assert panel._similar_layout.count() == 2 and not any(
        isinstance(panel._similar_layout.itemAt(i).widget(), CompactSection) for i in range(2))


def test_similar_failure_can_be_retried_by_reopening_the_tab(rig):
    similar_rig(rig)
    rig.playback.play_track(song(1))
    panel = rig.window.side_panel
    panel._select_tab(2)
    rig.catalog.related_calls[0]["on_error"](RuntimeError("x"))
    panel._select_tab(2)
    assert len(rig.catalog.related_calls) == 2


def test_similar_without_a_song_shows_a_hint(rig):
    similar_rig(rig)
    rig.window.side_panel._select_tab(2)
    assert rig.catalog.related_calls == []
    assert "Reproduce una canción" in rig.window.side_panel._similar_layout.itemAt(0).widget().text()


def test_similar_uses_the_restored_current_song(rig):
    similar_rig(rig)
    rig.queue.restore([song(4), song(5)], 1)
    rig.window.side_panel._select_tab(2)
    assert rig.catalog.related_calls[0]["video_id"] == "v5"


def test_similar_clicks_hover_and_queue_actions_are_routed(rig):
    similar_rig(rig)
    panel = rig.window.side_panel
    item = {"type": "artist", "browseId": "UC1"}
    panel.similar_item_chosen.emit(item)
    assert rig.opened == [item]
    rig.queue.replace([song(1)], 0)
    panel.similar_item_hovered.emit(song(8))
    panel.similar_add_next.emit(song(9))
    assert rig.streams.prefetched == ["v8", "v9"]


TARGETS = {"recent": [], "all": [{"playlistId": "local_1", "title": "Mine", "source": "local"}]}


def open_picker(rig, monkeypatch, choice):
    make_playlists(rig)
    shown = []
    monkeypatch.setattr(rig.window, "choose_playlist", lambda targets: shown.append(targets) or choice)
    rig.window.save_to_playlist_requested.emit(song(3))
    rig.library.target_requests[-1](TARGETS)
    return shown


def test_song_menu_requests_from_every_screen_reach_the_presenter(rig):
    make_playlists(rig)
    window = rig.window
    for signal in (window.home_panel.add_playlist_clicked, window.explore_panel.add_playlist_clicked,
                   window.search_panel.add_playlist_clicked, window.library_browser.song_add_playlist,
                   window.side_panel.similar_add_playlist):
        before = len(rig.library.target_requests)
        signal.emit(song(1))
        assert len(rig.library.target_requests) == before + 1


def test_picking_a_playlist_adds_the_song_and_says_so(rig, monkeypatch):
    shown = open_picker(rig, monkeypatch, ("existing", TARGETS["all"][0]))
    assert shown == [TARGETS] and rig.library.added == [("local_1", ["v3"])]
    assert rig.notifier.messages[-1] == ("info", "«T3» agregada a «Mine».")


def test_adding_a_duplicate_or_failing_is_reported(rig, monkeypatch):
    rig.library.add_outcome = "duplicate"
    open_picker(rig, monkeypatch, ("existing", TARGETS["all"][0]))
    assert rig.notifier.messages[-1] == ("info", "«T3» ya estaba en «Mine».")
    rig.library.add_outcome = "failed"
    rig.library.target_requests[-1](TARGETS)
    assert rig.notifier.messages[-1][0] == "error"


def test_dismissing_the_picker_changes_nothing(rig, monkeypatch):
    open_picker(rig, monkeypatch, None)
    assert rig.library.added == [] and rig.library.saved == [] and rig.notifier.messages == []


def test_new_playlist_from_the_picker_holds_the_song(rig, monkeypatch):
    open_picker(rig, monkeypatch, ("new", "Gym"))
    assert rig.library.saved == [("Gym", ["v3"], False)]
    assert rig.notifier.messages[-1] == ("info", "«T3» agregada a la nueva playlist «Gym».")


def test_new_playlist_is_also_created_in_the_account_when_signed_in(rig, monkeypatch):
    rig.auth.is_authenticated = True
    open_picker(rig, monkeypatch, ("new", "Gym"))
    assert rig.library.saved == [("Gym", ["v3"], True)]


def test_a_song_without_id_cannot_be_saved(rig):
    make_playlists(rig)
    rig.window.save_to_playlist_requested.emit({"title": "no id"})
    assert rig.library.target_requests == [] and rig.notifier.messages[-1][0] == "warning"
