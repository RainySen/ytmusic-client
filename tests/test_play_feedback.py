import pytest

from presenters.player_presenter import PlayerPresenter
from tests.test_presenters import Rig


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def song(n):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}]}


def icon_key(window):
    return window.player_panel.play_button.icon().cacheKey()


def test_play_button_spins_while_the_track_loads(rig):
    window = rig.window
    window.set_loading(True)
    assert window._spinner.isActive()
    spinning = icon_key(window)
    window.set_playing(True)
    assert icon_key(window) == spinning
    window.set_loading(False)
    assert not window._spinner.isActive()
    assert icon_key(window) == window.icons["pause"].cacheKey()


def test_loading_starts_on_load_and_stops_when_audio_starts_or_fails(rig):
    rig.keep(PlayerPresenter(rig.window, rig.playback))
    rig.queue.replace([song(1), song(2)], 0)
    rig.playback.play_track(rig.queue.current)
    assert rig.window._loading
    rig.streams.resolve("v1")
    assert not rig.window._loading
    rig.playback.play_track(rig.queue.current)
    assert rig.window._loading
    rig.playback.playing_changed.emit(False)
    assert not rig.window._loading


def test_icon_buttons_have_a_pressed_state():
    from ui import theme
    from ui.components.icon_button import icon_button
    assert "QPushButton:pressed" in icon_button("fa5s.play").styleSheet()
    theme.apply("classic")
