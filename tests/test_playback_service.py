import pytest

from domain.play_queue import PlayQueue
from services.playback_service import PlaybackService
from tests.fakes import FakeAudio, FakeCatalog, FakeNotifier, FakeStreams


def song(n):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}]}


class Rig:
    def __init__(self):
        self.queue = PlayQueue(radio_limit=6)
        self.audio = FakeAudio()
        self.streams = FakeStreams()
        self.catalog = FakeCatalog()
        self.notifier = FakeNotifier()
        self.service = PlaybackService(self.queue, self.streams, self.audio, self.catalog, self.notifier)
        self.started = []
        self.loading = []
        self.playing_states = []
        self.stopped = 0
        self.service.track_started.connect(self.started.append)
        self.service.track_loading.connect(self.loading.append)
        self.service.playing_changed.connect(self.playing_states.append)
        self.service.stopped.connect(lambda: setattr(self, "stopped", self.stopped + 1))

    def started_ids(self):
        return [s["videoId"] for s in self.started]


@pytest.fixture
def rig(qapp):
    return Rig()


def test_start_radio_plays_seed_before_recommendations_arrive(rig):
    rig.service.start_radio(song(0))
    assert rig.loading[0]["videoId"] == "v0"
    assert rig.streams.requests == ["v0"]
    assert rig.audio.played_urls == []
    rig.streams.resolve("v0")
    assert rig.audio.played_urls == ["url-v0"]
    assert rig.started_ids() == ["v0"]
    assert len(rig.queue) == 1


def test_radio_recommendations_fill_queue_and_prefetch(rig):
    rig.service.start_radio(song(0))
    rig.streams.resolve("v0")
    radio_call = next(i for i, c in enumerate(rig.catalog.calls) if c["key"] == "radio")
    rig.catalog.answer(radio_call, [song(i) for i in range(1, 9)])
    assert len(rig.queue) == 6
    assert rig.streams.prefetched[-3:] == ["v1", "v2", "v3"]


def test_stale_radio_result_is_ignored(rig):
    rig.service.start_radio(song(0))
    first = next(i for i, c in enumerate(rig.catalog.calls) if c["key"] == "radio")
    rig.service.start_radio(song(50))
    rig.catalog.answer(first, [song(1), song(2)])
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v50"]


def test_radio_does_not_trigger_duplicate_extension_request(rig):
    rig.service.start_radio(song(0))
    rig.streams.resolve("v0")
    assert [c["key"] for c in rig.catalog.calls] == ["radio"]


def test_finished_song_advances_to_next(rig):
    rig.queue.replace([song(0), song(1), song(2)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.audio.finished.emit()
    assert rig.streams.requests[-1] == "v1"
    rig.streams.resolve("v1")
    assert rig.started_ids() == ["v0", "v1"]


def test_stale_stream_resolution_is_ignored(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(song(0))
    rig.queue.jump_to(1)
    rig.service.play_track(song(1))
    rig.streams.resolve("v0")
    assert rig.audio.played_urls == []
    rig.streams.resolve("v1")
    assert rig.audio.played_urls == ["url-v1"]


def test_queue_end_requests_extension_then_plays_it(rig):
    rig.queue.replace([song(0)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    ext = next(i for i, c in enumerate(rig.catalog.calls) if c["key"] == "extend")
    assert rig.catalog.calls[ext]["video_id"] == "v0"
    rig.audio.finished.emit()
    assert rig.stopped == 1 and rig.playing_states[-1] is False
    rig.catalog.answer(ext, [song(1), song(2), song(3)])
    assert rig.streams.requests[-1] == "v1"
    assert len(rig.queue) == 3


def test_extension_skips_songs_already_queued(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    ext = next(i for i, c in enumerate(rig.catalog.calls) if c["key"] == "extend")
    rig.catalog.answer(ext, [song(1), song(5), song(6), song(7)])
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v0", "v1", "v5", "v6"]


def test_no_extension_while_plenty_queued_or_looping(rig):
    rig.queue.replace([song(i) for i in range(5)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    assert not any(c["key"] == "extend" for c in rig.catalog.calls)
    looping = Rig()
    looping.queue.replace([song(0)], 0)
    looping.queue.toggle_loop()
    looping.service.play_track(looping.queue.current)
    looping.streams.resolve("v0")
    assert looping.catalog.calls == []


def test_extension_failure_resets_state(rig):
    rig.queue.replace([song(0)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.catalog.fail(0)
    rig.service.next()
    assert len([c for c in rig.catalog.calls if c["key"] == "extend"]) == 2


def test_loop_song_replays_current(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.queue.toggle_loop()
    rig.queue.toggle_loop()
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.audio.finished.emit()
    assert rig.streams.requests[-1] == "v0" and rig.queue.current["videoId"] == "v0"


def test_stream_failure_notifies_and_skips(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.failed.emit("v0", "unavailable")
    assert rig.notifier.messages[0][0] == "error" and "T0" in rig.notifier.messages[0][1]
    assert rig.streams.requests[-1] == "v1"


def test_gives_up_after_consecutive_failures(rig):
    rig.queue.replace([song(i) for i in range(6)], 0)
    rig.service.play_track(rig.queue.current)
    for n in range(3):
        rig.streams.failed.emit(f"v{n}", "nope")
    assert rig.streams.requests == ["v0", "v1", "v2"]
    assert rig.notifier.messages[-1][0] == "warning"


def test_audio_error_retries_once_with_fresh_stream(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.audio.failed.emit()
    assert rig.streams.invalidated == ["v0"]
    assert rig.streams.requests == ["v0", "v0"]
    rig.streams.resolve("v0", url="fresh")
    assert rig.audio.played_urls == ["url-v0", "fresh"]


def test_audio_error_twice_skips_to_next_without_looping(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.audio.failed.emit()
    rig.streams.resolve("v0", url="fresh")
    rig.audio.failed.emit()
    assert rig.streams.requests[-1] == "v1"
    assert any(kind == "error" for kind, _ in rig.notifier.messages)


def test_toggle_pause_resume_and_restart(rig):
    rig.queue.replace([song(0)], 0)
    rig.service.toggle_pause()
    assert rig.streams.requests == ["v0"]
    rig.streams.resolve("v0")
    rig.service.toggle_pause()
    assert rig.audio.is_playing is False and rig.playing_states[-1] is False
    rig.service.toggle_pause()
    assert rig.audio.is_playing is True and rig.playing_states[-1] is True


def test_toggle_pause_ignored_while_loading(rig):
    rig.queue.replace([song(0)], 0)
    rig.service.play_track(rig.queue.current)
    rig.service.toggle_pause()
    assert rig.streams.requests == ["v0"]


def test_enqueue_next_and_last(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.enqueue_next(song(9))
    rig.service.enqueue_last(song(8))
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v0", "v9", "v1", "v8"]
    assert rig.streams.prefetched == ["v9", "v8"]
    assert rig.streams.requests == []


def test_enqueue_into_empty_queue_starts_playing(rig):
    rig.service.enqueue_last(song(3))
    assert rig.streams.requests == ["v3"]


def test_song_without_id_is_rejected(rig):
    rig.service.play_track({"title": "x"})
    assert rig.notifier.messages and rig.streams.requests == []


def test_play_collection_replaces_queue(rig):
    rig.service.play_collection([song(1), {"title": "no id"}, song(2)])
    assert [s["videoId"] for s in rig.queue.snapshot()] == ["v1", "v2"]
    assert rig.streams.requests == ["v1"]


def test_next_at_end_waits_for_extension(rig):
    rig.queue.replace([song(0)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    ext = next(i for i, c in enumerate(rig.catalog.calls) if c["key"] == "extend")
    rig.service.next()
    rig.catalog.answer(ext, [song(1)])
    assert rig.streams.requests[-1] == "v1"


def test_volume_and_seek_delegate(rig):
    rig.service.set_volume(40)
    rig.service.seek(0.5)
    assert rig.audio.volume == 40 and rig.audio.seeks == [0.5]


def test_radio_history_stays_bounded(rig):
    rig.queue.replace([song(i) for i in range(200)], 199)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v199")
    ext = next(i for i, c in enumerate(rig.catalog.calls) if c["key"] == "extend")
    rig.catalog.answer(ext, [song(1000), song(1001)])
    assert rig.queue.current["videoId"] == "v199"
    assert len(rig.queue) <= 50 + 1 + 2


def test_new_song_stops_the_previous_one_immediately(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    assert rig.audio.is_playing
    rig.queue.jump_to(1)
    rig.service.play_track(rig.queue.current)
    assert rig.audio.is_playing is False and rig.audio.has_media is False
    rig.streams.resolve("v1")
    assert rig.audio.played_urls == ["url-v0", "url-v1"]


def test_stopping_for_a_new_song_is_not_reported_as_audio_failure(rig):
    rig.queue.replace([song(0), song(1)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.queue.jump_to(1)
    rig.service.play_track(rig.queue.current)
    rig.audio.failed.emit()
    assert rig.streams.invalidated == [] and rig.notifier.messages == []


def test_shuffle_reorders_upcoming_and_prefetches(rig):
    rig.queue.replace([song(i) for i in range(10)], 0)
    rig.service.play_track(rig.queue.current)
    rig.streams.resolve("v0")
    rig.streams.prefetched.clear()
    rig.service.shuffle()
    assert rig.queue.current["videoId"] == "v0"
    assert len(rig.streams.prefetched) == 3


def sized_rig(size):
    r = Rig()
    r.queue = PlayQueue(radio_limit=6)
    r.service = PlaybackService(r.queue, r.streams, r.audio, r.catalog, r.notifier, radio_size=lambda: size)
    return r


def radio_calls(r):
    return [(i, c["limit"]) for i, c in enumerate(r.catalog.calls) if c["key"] == "radio"]


def answer_radio(r, count):
    index, _limit = radio_calls(r)[-1]
    r.catalog.answer(index, [song(i) for i in range(1, count + 1)])


def test_radio_size_200_loads_the_queue_in_growing_stages(qapp):
    r = sized_rig(200)
    r.service.start_radio(song(0))
    assert [limit for _, limit in radio_calls(r)] == [50] and r.queue.radio_limit == 200
    answer_radio(r, 49)
    assert [limit for _, limit in radio_calls(r)] == [50, 100] and len(r.queue) == 50
    answer_radio(r, 100)
    assert [limit for _, limit in radio_calls(r)] == [50, 100, 200] and len(r.queue) == 101
    answer_radio(r, 200)
    assert len(radio_calls(r)) == 3 and len(r.queue) == 200


def test_radio_size_25_asks_for_only_25_and_stops(qapp):
    r = sized_rig(25)
    r.service.start_radio(song(0))
    assert [limit for _, limit in radio_calls(r)] == [25]
    answer_radio(r, 25)
    assert len(radio_calls(r)) == 1 and len(r.queue) == 25


def test_radio_size_500_uses_doubling_stages_capped_at_the_target(qapp):
    r = sized_rig(500)
    r.service.start_radio(song(0))
    for count in (49, 148, 246, 403):
        answer_radio(r, count)
    assert [limit for _, limit in radio_calls(r)] == [50, 100, 200, 400, 500]


def test_unlimited_radio_starts_with_a_hundred_and_extends_in_bigger_batches(qapp):
    r = sized_rig(0)
    r.service.start_radio(song(0))
    answer_radio(r, 49)
    answer_radio(r, 100)
    assert [limit for _, limit in radio_calls(r)] == [50, 100] and r.queue.radio_limit is None
    assert r.service._extend_batch() == 10


def test_radio_stops_growing_when_youtube_runs_out_or_nothing_is_new(qapp):
    r = sized_rig(200)
    r.service.start_radio(song(0))
    answer_radio(r, 30)
    assert len(radio_calls(r)) == 1
    r2 = sized_rig(200)
    r2.service.start_radio(song(0))
    answer_radio(r2, 50)
    answer_radio(r2, 50)
    assert len(radio_calls(r2)) == 2


def test_radio_size_is_read_again_for_every_new_radio(qapp):
    size = [25]
    r = Rig()
    r.service = PlaybackService(r.queue, r.streams, r.audio, r.catalog, r.notifier, radio_size=lambda: size[0])
    r.service.start_radio(song(0))
    assert r.queue.radio_limit == 25
    size[0] = 100
    r.service.start_radio(song(50))
    assert r.queue.radio_limit == 100 and radio_calls(r)[-1][1] == 50


def test_small_radio_sizes_ask_for_exactly_that_many_and_never_stage(qapp):
    for size in (5, 10, 15):
        r = sized_rig(size)
        r.service.start_radio(song(0))
        assert [limit for _, limit in radio_calls(r)] == [size] and r.queue.radio_limit == size
        answer_radio(r, 49)
        assert len(radio_calls(r)) == 1 and len(r.queue) == size


def test_every_offered_radio_size_is_valid_and_ordered():
    from domain.settings import RADIO_SIZE_OPTIONS

    sizes = [s for s in RADIO_SIZE_OPTIONS if s]
    assert sizes == sorted(sizes) and sizes[0] == 5 and RADIO_SIZE_OPTIONS[-1] == 0
