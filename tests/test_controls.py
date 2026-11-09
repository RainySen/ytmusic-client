import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest

from tests.test_presenters import Rig


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def press(window, keys):
    action = next(a for a in window.actions() if a.shortcut() == QKeySequence(keys))
    action.trigger()


def test_keyboard_shortcuts_drive_playback(rig):
    window = rig.window
    hits = []
    window.play_pause_clicked.connect(lambda: hits.append("pp"))
    window.next_clicked.connect(lambda: hits.append("next"))
    window.previous_clicked.connect(lambda: hits.append("prev"))
    window.seek_by_requested.connect(lambda ms: hits.append(ms))
    for keys in ("Space", "Right", "Left", "Ctrl+Right", "Ctrl+Left"):
        press(window, keys)
    assert hits == ["pp", 5000, -5000, "next", "prev"]


def test_volume_mute_and_search_shortcuts(rig):
    window = rig.window
    window.player_panel.volume_slider.setValue(50)
    press(window, "Up")
    assert window.volume == 55
    press(window, "Down")
    press(window, "Down")
    assert window.volume == 45
    press(window, "M")
    assert window.volume == 0
    press(window, "Ctrl+F")
    assert window.top_bar.search_box.hasFocus() or window.focusWidget() is window.top_bar.search_box


def test_dragging_the_progress_bar_seeks_once_on_release(rig):
    window = rig.window
    window.player_panel.show()
    window.set_time(10, 200)
    seeks = []
    window.seek_requested.connect(seeks.append)
    slider = window.player_panel.progress_slider
    slider.setSliderDown(True)
    for value in (250, 500):
        slider.setValue(value)
        slider.sliderMoved.emit(value)
    assert seeks == [] and window.player_panel.time_label.text() == "1:40"
    slider.setSliderDown(False)
    assert seeks == [0.5]


def test_progress_hover_text_shows_the_time_under_the_cursor(rig):
    window = rig.window
    window.set_time(0, 200)
    assert window.player_panel.progress_slider.hover_text(0.25) == "0:50"


def test_seek_by_moves_relative_to_the_current_position(qapp):
    from domain.play_queue import PlayQueue
    from services.playback_service import PlaybackService
    from tests.fakes import FakeAudio, FakeCatalog, FakeNotifier, FakeStreams
    audio = FakeAudio()
    service = PlaybackService(PlayQueue(), FakeStreams(), audio, FakeCatalog(), FakeNotifier())
    service.seek_by(5000)
    service.rewind(10)
    assert audio.seeks == [("by", 5000), ("by", -10000)]
