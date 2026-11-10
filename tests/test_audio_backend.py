from infra.audio_backend import VlcAudioBackend


class FakePlayer:
    def __init__(self, time_ms=42_000):
        self.time_ms = time_ms
        self.calls = []

    def audio_set_mute(self, muted):
        self.calls.append(("mute", muted))

    def get_time(self):
        return self.time_ms

    def set_pause(self, paused):
        self.calls.append(("pause", paused))

    def set_time(self, ms):
        self.calls.append(("time", ms))

    def set_position(self, fraction):
        self.calls.append(("position", fraction))


def backend(qapp, player):
    audio = VlcAudioBackend()
    audio._player, audio._has_media, audio._playing = player, True, True
    return audio


def test_pause_mutes_first_and_resume_flushes_from_the_paused_spot(qapp):
    player = FakePlayer()
    audio = backend(qapp, player)
    audio.pause()
    assert player.calls == [("mute", True), ("pause", 1)]
    player.calls.clear()
    player.time_ms = 43_000  # vlc's clock may drift while the tail still plays
    audio.resume()
    assert player.calls == [("time", 42_000), ("pause", 0), ("mute", False)]
    assert audio.is_playing


def test_seeking_while_paused_is_not_undone_by_resume(qapp):
    player = FakePlayer()
    audio = backend(qapp, player)
    audio.pause()
    audio.seek(0.5)
    player.calls.clear()
    audio.resume()
    assert player.calls == [("pause", 0), ("mute", False)]
