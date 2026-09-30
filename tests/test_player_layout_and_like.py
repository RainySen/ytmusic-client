import pytest
from PySide6.QtWidgets import QApplication

from domain.models import parse_home_section
from domain.volume import gain
from PySide6.QtCore import QRect
from ui.components.track_list import _cells


class Thumbs:
    def request(self, url, callback):
        pass


def song(n=1, **extra):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}], **extra}


def test_volume_is_no_longer_curved(qapp):
    assert [gain(v) for v in (0, 10, 30, 50, 70, 100)] == [0, 10, 30, 50, 70, 100]


def test_home_section_keeps_the_like_status_when_the_api_sends_it():
    section = {"title": "S", "contents": [
        {"videoId": "a", "title": "A", "artists": [], "likeStatus": "LIKE"},
        {"videoId": "b", "title": "B", "artists": [], "likeStatus": "INDIFFERENT"},
        {"videoId": "c", "title": "C", "artists": []},
    ]}
    items = parse_home_section(section)
    assert items[0]["likeStatus"] == "LIKE"
    assert items[1]["likeStatus"] == "INDIFFERENT"
    assert "likeStatus" not in items[2]


def test_track_row_shows_a_heart_only_for_liked_songs(qapp):
    def has_heart(track):
        return "heart" in _cells(QRect(0, 0, 1000, 56), track, {})

    assert has_heart(song(1, likeStatus="LIKE"))
    assert not has_heart(song(2, likeStatus="INDIFFERENT")) and not has_heart(song(3))


def test_player_bar_progress_spans_the_top_full_width_above_the_buttons(rig_window):
    from PySide6.QtCore import QPoint

    panel = rig_window.player_panel
    panel.resize(1200, 80)
    panel.show()
    QApplication.processEvents()

    def top_of(widget):
        return widget.mapTo(panel, QPoint(0, 0)).y()

    slider, play = panel.progress_slider, panel.play_button
    assert top_of(slider) < top_of(play)
    assert slider.width() > play.width() * 5
    assert top_of(panel.time_label) < top_of(play) and top_of(panel.total_time_label) < top_of(play)
    panel.close()


@pytest.fixture
def rig_window(qapp):
    import qtawesome as qta

    from ui.main_window import MainWindow

    window = MainWindow(Thumbs(), qta.icon("fa5s.music"))
    yield window
    window.close()
    window.deleteLater()
