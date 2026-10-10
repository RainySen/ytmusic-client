import pytest
from PySide6.QtWidgets import QLabel

from domain.search_results import group_library_results, matches_query
from infra.concurrency import TaskRunner
from infra.playlist_repository import LocalPlaylistRepository
from infra.ytmusic_gateway import YTMusicGateway
from presenters.search_presenter import SearchPresenter
from services.catalog_service import CatalogService
from services.library_service import LibraryService
from tests.test_presenters import Rig
from tests.test_ui import FakeThumbnails
from ui.components.search_panel import SCOPE_LIBRARY, SCOPE_YTMUSIC, SearchPanel
from ui.components.track_actions import TrackActionsButton

RAW = [
    {"category": "Artists", "resultType": "artist", "title": None, "artist": "issey",
     "browseId": "MPLAUCfhD8Gq06PyrH70zKv7ZpCA"},
    {"category": "Albums", "resultType": "album", "title": "The Ugly Duckling", "browseId": "MPREb_1",
     "artists": [{"name": "issey"}]},
    {"category": "Songs", "resultType": "song", "title": "The Ugly Duckling", "videoId": "Ex91",
     "artists": [{"name": "issey"}]},
    {"category": "Episodes", "resultType": "episode", "title": "ignored"},
]


def song(n, title=None, artist="A"):
    return {"videoId": f"v{n}", "title": title or f"T{n}", "artists": [{"name": artist}]}


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def test_library_results_group_by_type_and_fix_library_artist_ids():
    sections = group_library_results(RAW, [song(1, "The Ugly Duckling"), {**song(2), "videoId": "Ex91"}])
    assert [title for title, _ in sections] == ["Artistas", "Álbumes", "Canciones"]
    artists, albums, songs = (items for _, items in sections)
    assert artists[0]["browseId"] == "UCfhD8Gq06PyrH70zKv7ZpCA" and RAW[0]["browseId"].startswith("MPLA")
    assert [s["videoId"] for s in songs] == ["Ex91", "v1"] and songs[1]["resultType"] == "song"
    assert group_library_results([]) == []


def test_matches_query_needs_every_word_in_title_artist_or_album():
    track = {"title": "The Ugly Duckling", "artists": [{"name": "issey"}], "album": {"name": "Single"}}
    assert matches_query(track, "ugly ISSEY") and matches_query(track, "single duckling")
    assert not matches_query(track, "ugly goose") and not matches_query(track, "   ")


class LibraryGateway:
    def __init__(self, authenticated):
        self.is_authenticated = authenticated
        self.calls = []
        self.fail = False

    def search(self, query, filter=None, limit=25, scope=None):
        self.calls.append((query, scope))
        if self.fail:
            raise RuntimeError("down")
        return RAW


@pytest.fixture
def library(qapp, tmp_path):
    runner = TaskRunner("library-search", 2)
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    repo.add("Mine", [song(7, "Ugly local", "issey")], "user_created")

    def make(authenticated):
        gateway = LibraryGateway(authenticated)
        return LibraryService(gateway, repo, CatalogService(gateway, runner), runner), gateway

    yield make
    runner.shutdown()


def test_library_search_uses_the_library_scope_and_adds_local_playlist_songs(library, wait_until):
    service, gateway = library(True)
    got = []
    service.search("ugly issey", got.append)
    assert wait_until(lambda: got)
    assert gateway.calls == [("ugly issey", "library")]
    songs = dict(got[0])["Canciones"]
    assert [s["videoId"] for s in songs] == ["Ex91", "v7"]


def test_library_search_without_session_or_network_still_shows_local_matches(library, wait_until):
    service, gateway = library(False)
    got = []
    service.search("ugly", got.append)
    assert [title for title, _ in got[0]] == ["Canciones"] and gateway.calls == []
    online, gateway = library(True)
    gateway.fail = True
    errors, results = [], []
    online.search("ugly", results.append, errors.append)
    assert wait_until(lambda: results) and errors == []
    online.search("nothing here", results.append, errors.append)
    assert wait_until(lambda: errors) and isinstance(errors[0], RuntimeError)


def test_search_panel_tabs_report_the_scope_and_render_sections(qapp):
    panel = SearchPanel()
    seen = []
    panel.scope_changed.connect(seen.append)
    assert panel._tabs[SCOPE_YTMUSIC].isChecked() and not panel._tabs[SCOPE_LIBRARY].isChecked()
    panel._tabs[SCOPE_LIBRARY].click()
    assert seen == [SCOPE_LIBRARY] and panel._tabs[SCOPE_LIBRARY].isChecked()
    panel.show_library_results(group_library_results(RAW), FakeThumbnails())
    texts = [label.text() for label in panel.findChildren(QLabel)]
    assert {"Artistas", "Álbumes", "Canciones", "issey"} <= set(texts)
    assert not [w for w in qapp.topLevelWidgets() if isinstance(w, TrackActionsButton) and w.isVisible()]
    panel.show_library_results([], FakeThumbnails())
    assert any("biblioteca" in label.text() for label in panel.findChildren(QLabel))


class ShelfCrashClient:
    def __init__(self):
        self.sent = []

    def search(self, query, filter=None, limit=25, scope=None):
        raise KeyError("contents")

    def _send_request(self, endpoint, body, *extra):
        self.sent.append((endpoint, body["query"]))
        lazy_shelf = {"musicShelfRenderer": {"title": {"runs": [{"text": "Songs"}]}, "bottomEndpoint": {}}}
        tab = {"tabRenderer": {"content": {"sectionListRenderer": {"contents": [lazy_shelf]}}}}
        return {"contents": {"tabbedSearchResultsRenderer": {"tabs": [tab, tab]}}}


def test_library_search_skips_lazy_shelves_instead_of_failing(tmp_path):
    client = ShelfCrashClient()
    gateway = YTMusicGateway(str(tmp_path / "none.json"))
    gateway._client = lambda: client
    assert gateway.search("mafumafu", limit=40, scope="library") == []
    assert client.sent == [("search", "mafumafu")]
    with pytest.raises(KeyError):
        gateway.search("mafumafu")


class FakeLibrarySearch:
    def __init__(self):
        self.calls = []

    def search(self, query, on_done, on_error=None):
        self.calls.append((query, on_done, on_error))


def test_switching_tabs_repeats_the_query_in_that_scope_and_ignores_stale_answers(rig):
    library = FakeLibrarySearch()
    rig.keep(SearchPresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, library=library))
    panel = rig.window.search_panel
    rig.window.search_submitted.emit("ugly issey")
    web_answer = rig.catalog.search_calls[-1]["on_done"]
    panel._tabs[SCOPE_LIBRARY].click()
    assert library.calls[-1][0] == "ugly issey"
    web_answer({"top_result": None, "songs": [song(1)], "more": []})
    library.calls[-1][1](group_library_results(RAW))
    assert "Artistas" in [label.text() for label in panel.findChildren(QLabel)]
    rig.window.search_submitted.emit("otra")
    assert library.calls[-1][0] == "otra"
    panel._tabs[SCOPE_YTMUSIC].click()
    assert rig.catalog.search_calls[-1]["query"] == "otra"
