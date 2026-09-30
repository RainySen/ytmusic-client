import json

import pytest

from infra.listen_again_pins import ListenAgainPins
from presenters.home_presenter import LISTEN_AGAIN_TITLE, HomePresenter
from presenters.song_menu_presenter import SongMenuPresenter
from tests.test_presenters import Rig
from ui.components.track_actions import SongMenuHub, TrackActionsButton, song_entries, song_hub


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def song(n, artist_id="UC1"):
    artists = [{"name": "A", "id": artist_id}] if artist_id else [{"name": "A"}]
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": artists, "type": "song"}


def test_pins_toggle_persist_newest_first_and_respect_the_limit(tmp_path):
    path = tmp_path / "pins.json"
    pins = ListenAgainPins(str(path), limit=2)
    assert pins.toggle(song(1)) is True and pins.toggle(song(2)) is True and pins.toggle(song(3)) is True
    assert [s["videoId"] for s in pins.songs()] == ["v3", "v2"]
    assert pins.toggle(song(2)) is False and not pins.is_pinned("v2")
    assert [s["videoId"] for s in json.loads(path.read_text(encoding="utf-8"))] == ["v3"]
    assert [s["videoId"] for s in ListenAgainPins(str(path)).songs()] == ["v3"]
    assert pins.toggle({"title": "sin id"}) is False


def test_song_entries_add_artist_only_when_linked_and_flip_the_pin_label():
    hub = song_hub
    old = hub.is_pinned
    try:
        hub.is_pinned = lambda s: s["videoId"] == "v1"
        labels = [label for _k, label, _i in song_entries(song(1))]
        assert "Ir al artista" in labels and "Quitar de volver a escuchar" in labels
        labels = [label for _k, label, _i in song_entries(song(2, artist_id=None))]
        assert "Ir al artista" not in labels and "Fijar en volver a escuchar" in labels
    finally:
        hub.is_pinned = old


def test_track_button_sends_artist_and_pin_to_the_hub_and_keeps_the_rest(qapp):
    button = TrackActionsButton()
    button.song = song(1)
    got, queued = [], []
    song_hub.artist_requested.connect(got.append)
    song_hub.pin_toggled.connect(got.append)
    button.add_queue.connect(lambda: queued.append(1))
    try:
        button.action_chosen.emit("artist")
        button.action_chosen.emit("pin")
        button.action_chosen.emit("queue")
        assert [s["videoId"] for s in got] == ["v1", "v1"] and queued == [1]
    finally:
        song_hub.artist_requested.disconnect(got.append)
        song_hub.pin_toggled.disconnect(got.append)


def test_home_puts_pins_first_in_listen_again_or_creates_the_shelf(rig, tmp_path):
    pins = ListenAgainPins(str(tmp_path / "pins.json"))
    home = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, pins=pins))
    shelf = [("Volver a escucharlo", [song(5), song(6)]), ("Otro", [song(7)])]
    assert home._with_pins(shelf) == shelf
    pins.toggle(song(6))
    merged = home._with_pins(shelf)
    assert [s["videoId"] for s in merged[0][1]] == ["v6", "v5"] and merged[1] == shelf[1]
    created = home._with_pins([("Otro", [song(7)])])
    assert created[0][0] == LISTEN_AGAIN_TITLE and created[0][1][0]["videoId"] == "v6"
    home._mood = "Fiesta"
    assert home._with_pins(shelf) == shelf


def test_song_menu_presenter_opens_the_artist_and_toggles_pins(rig, tmp_path):
    hub = SongMenuHub()
    pins = ListenAgainPins(str(tmp_path / "pins.json"))
    home = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, pins=pins))
    rig.keep(SongMenuPresenter(hub, rig.navigator, pins, rig.notifier, home))
    artists = []
    rig.navigator.artist_requested.connect(artists.append)
    hub.artist_requested.emit(song(1))
    assert artists == ["UC1"]
    hub.artist_requested.emit(song(2, artist_id=None))
    assert rig.notifier.messages[-1][0] == "warning"
    hub.pin_toggled.emit(song(3))
    assert hub.is_pinned(song(3)) and "fijada" in rig.notifier.messages[-1][1]
    hub.pin_toggled.emit(song(3))
    assert not hub.is_pinned(song(3))


def test_player_bar_menu_offers_artist_and_pin_for_the_current_song(rig):
    panel = rig.window.player_panel
    assert "Ir al artista" not in [a.text() for a in panel.build_menu().actions()]
    panel.song = song(1)
    labels = [a.text() for a in panel.build_menu().actions()]
    assert "Ir al artista" in labels and "Fijar en volver a escuchar" in labels


def test_logging_out_clears_the_pins_but_an_expired_session_keeps_them(rig, tmp_path):
    hub = SongMenuHub()
    pins = ListenAgainPins(str(tmp_path / "pins.json"))
    home = rig.keep(HomePresenter(rig.window, rig.catalog, rig.playback, rig.opener, rig.notifier, pins=pins))
    rig.keep(SongMenuPresenter(hub, rig.navigator, pins, rig.notifier, home, auth=rig.auth))
    pins.toggle(song(1))
    rig.auth.auth_changed.emit(False)
    rig.auth.session_expired.emit()
    assert pins.is_pinned("v1")
    rig.auth.logout()
    assert pins.songs() == [] and json.loads((tmp_path / "pins.json").read_text(encoding="utf-8")) == []
