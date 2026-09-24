import pytest

from domain.play_queue import LOOP_OFF, LOOP_QUEUE, LOOP_SONG, PlayQueue


def song(n):
    return {"videoId": f"v{n}", "title": f"T{n}"}


@pytest.fixture
def q(qapp):
    return PlayQueue(radio_limit=6)


def fill(q, n=4, index=0):
    q.replace([song(i) for i in range(n)], index)
    return q


def ids(q):
    return [s["videoId"] for s in q.snapshot()]


def test_empty_queue(q):
    assert q.current is None and q.current_index == -1
    assert q.next() is None and q.previous() is None


def test_append_to_empty_becomes_current(q):
    assert q.append(song(0)) is True
    assert q.current["videoId"] == "v0"
    assert q.append(song(1)) is False
    assert q.current_index == 0


def test_next_previous_and_bounds(q):
    fill(q, 3)
    assert q.next()["videoId"] == "v1"
    assert q.next()["videoId"] == "v2"
    assert q.next() is None
    assert q.current_index == 2
    assert q.previous()["videoId"] == "v1"
    fill(q, 3, 0)
    assert q.previous() is None


def test_loop_queue_wraps(q):
    fill(q, 2, 1)
    q.toggle_loop()
    assert q.loop_mode == LOOP_QUEUE
    assert q.next()["videoId"] == "v0"


def test_toggle_loop_cycles(q):
    assert [q.toggle_loop() for _ in range(3)] == [LOOP_QUEUE, LOOP_SONG, LOOP_OFF]


def test_insert_next(q):
    fill(q, 3, 0)
    assert q.insert_next(song(9)) is False
    assert ids(q) == ["v0", "v9", "v1", "v2"]
    empty = PlayQueue()
    assert empty.insert_next(song(1)) is True
    assert empty.current["videoId"] == "v1"


def test_play_now_inserts_after_current(q):
    fill(q, 3, 1)
    q.play_now(song(9))
    assert ids(q) == ["v0", "v1", "v9", "v2"]
    assert q.current["videoId"] == "v9"


def test_remove_before_current_shifts_index(q):
    fill(q, 4, 2)
    q.remove_at(0)
    assert q.current["videoId"] == "v2"
    assert q.current_index == 1


def test_remove_after_current_keeps_index(q):
    fill(q, 4, 1)
    q.remove_at(3)
    assert q.current["videoId"] == "v1"


def test_remove_current_detaches_and_next_does_not_skip(q):
    fill(q, 4, 1)
    q.remove_at(1)
    assert q.current is None and q.current_index == -1
    assert q.next()["videoId"] == "v2"


def test_remove_current_then_previous(q):
    fill(q, 4, 2)
    q.remove_at(2)
    assert q.previous()["videoId"] == "v1"


def test_remove_only_song(q):
    fill(q, 1)
    q.remove_at(0)
    assert len(q) == 0 and q.current_index == -1 and q.current is None


def test_remove_song_before_detached_slot(q):
    fill(q, 5, 2)
    q.remove_at(2)
    q.remove_at(1)
    assert q.next()["videoId"] == "v3"


def test_move_keeps_current_track(q):
    fill(q, 5, 1)
    q.move(1, 4)
    assert q.current["videoId"] == "v1"
    fill(q, 5, 2)
    q.move(0, 4)
    assert q.current["videoId"] == "v2"
    fill(q, 5, 2)
    q.move(4, 0)
    assert q.current["videoId"] == "v2"


def test_move_out_of_range_is_ignored(q):
    fill(q, 3)
    q.move(5, 0)
    q.move(0, 9)
    assert ids(q) == ["v0", "v1", "v2"]


def test_clear_except_current(q):
    fill(q, 4, 2)
    q.clear_except_current()
    assert ids(q) == ["v2"] and q.current_index == 0


def test_clear_with_no_current(q):
    q.clear_except_current()
    assert len(q) == 0


def test_extend_unique_skips_duplicates_and_respects_limit(q):
    fill(q, 2)
    added = q.extend_unique([song(1), song(5), song(6)], limit=3)
    assert added == 1 and ids(q) == ["v0", "v1", "v5"]


def test_radio_tail_ignored_for_stale_seed(q):
    q.start_radio(song(0))
    assert q.add_radio_tail("other", [song(1)]) == 0
    assert q.add_radio_tail("v0", [song(1), song(2)]) == 2
    assert q.radio_seed == "v0"


def test_radio_tail_capped_at_limit(qapp):
    q = PlayQueue(radio_limit=3)
    q.start_radio(song(0))
    q.add_radio_tail("v0", [song(i) for i in range(1, 10)])
    assert len(q) == 3


def test_restore_validates(q):
    q.restore([song(0), {"title": "no id"}, song(1)], 5)
    assert len(q) == 2 and q.current_index == -1
    q.restore([song(0), song(1)], 1)
    assert q.current["videoId"] == "v1"


def test_changed_signal_emitted(q):
    hits = []
    q.changed.connect(lambda: hits.append(1))
    q.append(song(0))
    q.next()
    assert len(hits) >= 1


def test_remaining_after_current(q):
    fill(q, 4, 1)
    assert q.remaining_after_current() == 2
    assert [s["videoId"] for s in q.upcoming(5)] == ["v2", "v3"]


def test_trim_played_keeps_recent_history_and_the_current_song(q):
    fill(q, 10, 7)
    removed = q.trim_played(keep=3)
    assert removed == 4
    assert ids(q) == ["v4", "v5", "v6", "v7", "v8", "v9"]
    assert q.current["videoId"] == "v7" and q.current_index == 3


def test_trim_played_noop_when_history_is_short(q):
    fill(q, 5, 2)
    assert q.trim_played(keep=10) == 0
    assert len(q) == 5


def test_shuffle_upcoming_only_touches_songs_after_current(q):
    import random

    fill(q, 12, 3)
    q.shuffle_upcoming(random.Random(1))
    result = ids(q)
    assert result[:4] == ["v0", "v1", "v2", "v3"]
    assert sorted(result[4:]) == sorted(f"v{i}" for i in range(4, 12))
    assert result[4:] != [f"v{i}" for i in range(4, 12)]
    assert q.current["videoId"] == "v3"


def test_shuffle_is_a_noop_with_fewer_than_two_upcoming(q):
    fill(q, 3, 1)
    hits = []
    q.changed.connect(lambda: hits.append(1))
    q.shuffle_upcoming()
    assert ids(q) == ["v0", "v1", "v2"] and hits == []
