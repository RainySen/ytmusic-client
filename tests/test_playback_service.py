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
