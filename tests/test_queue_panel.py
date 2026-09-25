from PySide6.QtTest import QTest

from tests.test_ui import FakeThumbnails
from ui.components.side_panel import QUEUE_BATCH, SidePanel


def songs(count, start=0):
    return [{"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}]} for n in range(start, start + count)]


def items(panel):
    layout = panel._queue_layout
    return [layout.itemAt(i).widget() for i in range(layout.count() - 1)]


def shown_panel(qapp):
    panel = SidePanel()
    panel.resize(420, 600)
    panel.show()
    QTest.qWait(20)
    return panel


def test_hidden_panel_builds_nothing_until_it_is_shown(qapp):
    panel = SidePanel()
    panel.set_queue(songs(300), 5, FakeThumbnails())
    assert items(panel) == [] and panel._queue_count.text() == "(300)"
    panel.resize(420, 600)
    panel.show()
    QTest.qWait(20)
    assert len(items(panel)) >= QUEUE_BATCH
    assert items(panel)[5].is_current


def test_long_queue_is_built_in_batches_and_grows_on_scroll(qapp):
    panel = shown_panel(qapp)
    panel.set_queue(songs(500), 0, FakeThumbnails())
    QTest.qWait(150)
    first = len(items(panel))
    assert QUEUE_BATCH <= first < 100
    bar = panel._queue_scroll.verticalScrollBar()
    bar.setValue(bar.maximum())
    assert len(items(panel)) > first
    panel.close()


def test_changing_only_the_current_song_reuses_the_widgets(qapp):
    panel = shown_panel(qapp)
    queue = songs(120)
    panel.set_queue(queue, 0, FakeThumbnails())
    before = items(panel)
    assert before[0].is_current
    panel.set_queue(queue, 1, FakeThumbnails())
    after = items(panel)
    assert after == before and not after[0].is_current and after[1].is_current
    panel.close()


def test_appending_songs_keeps_the_built_widgets(qapp):
    panel = shown_panel(qapp)
    panel.set_queue(songs(10), 2, FakeThumbnails())
    before = items(panel)
    panel.set_queue(songs(16), 2, FakeThumbnails())
    after = items(panel)
    assert after[:10] == before and len(after) == 16 and panel._queue_count.text() == "(16)"
    panel.close()


def test_removing_or_moving_songs_rebuilds_the_list(qapp):
    panel = shown_panel(qapp)
    queue = songs(12)
    panel.set_queue(queue, 0, FakeThumbnails())
    before = items(panel)
    panel.set_queue(queue[:5] + queue[6:], 0, FakeThumbnails())
    QTest.qWait(20)
    after = items(panel)
    assert len(after) == 11 and all(a is not b for a, b in zip(after, before))
    assert [w.index for w in after] == list(range(11))
    panel.close()


def test_current_song_far_down_is_built_and_revealed(qapp):
    panel = shown_panel(qapp)
    panel.set_queue(songs(400), 250, FakeThumbnails())
    QTest.qWait(250)
    built = items(panel)
    assert len(built) > 250 and built[250].is_current
    panel.close()


def test_empty_and_shrinking_queues(qapp):
    panel = shown_panel(qapp)
    panel.set_queue(songs(3), 1, FakeThumbnails())
    panel.set_queue([], -1, FakeThumbnails())
    assert items(panel) == [] and panel._queue_count.text() == "(0)"
    panel.set_queue(songs(2), 5, FakeThumbnails())
    assert len(items(panel)) == 2 and not any(w.is_current for w in items(panel))
    panel.close()
