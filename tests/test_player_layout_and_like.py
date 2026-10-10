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


def test_volume_compensates_vlc_cubing_like_the_windows_mixer(qapp):
    assert [gain(v) for v in (0, 10, 20, 50, 70, 100)] == [0, 32, 45, 71, 84, 100]


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


def test_liked_and_unliked_rows_keep_the_same_columns(qapp):
    def layout(track):
        return _cells(QRect(0, 0, 1000, 56), track, {"views": False})

    liked = layout(song(1, likeStatus="LIKE", album="A"))
    assert liked == layout(song(2, likeStatus="INDIFFERENT")) == layout(song(3, views="1 M"))
    assert "heart" in liked


def test_track_list_decides_the_views_column_for_the_whole_list(qapp):
    from ui.components.track_list import TrackList

    listing = TrackList()
    listing.set_tracks([song(1), song(2, likeStatus="LIKE")], Thumbs())
    assert listing.options["views"] is False
    listing.append_tracks([song(3, views="2 M")], Thumbs())
    rows = [_cells(QRect(0, 0, 1000, 56), t, listing.options) for t in listing.tracks]
    assert listing.options["views"] and rows[0] == rows[1] == rows[2] and "views" in rows[0]
    listing.set_tracks([song(4)], Thumbs(), views=False)
    listing.append_tracks([song(5, views="1 M")], Thumbs())
    assert listing.options["views"] is False


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
