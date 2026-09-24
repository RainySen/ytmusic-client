import time

from PySide6.QtCore import QObject, Signal

from domain.stream_cache import StreamInfo


class FakeAudio(QObject):
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    time_ms_changed = Signal(int)
    finished = Signal()
    failed = Signal()

    def __init__(self):
        super().__init__()
        self.played_urls = []
        self.is_playing = False
        self.has_media = False
        self.volume = None
        self.seeks = []

    def play_url(self, url):
        self.played_urls.append(url)
        self.is_playing = True
        self.has_media = True

    def pause(self):
        self.is_playing = False

    def resume(self):
        self.is_playing = True

    def stop(self):
        self.is_playing = False
        self.has_media = False

    def seek(self, fraction):
        self.seeks.append(fraction)

    def set_volume(self, volume):
        self.volume = volume


class FakeStreams(QObject):
    resolved = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.requests = []
        self.prefetched = []
        self.invalidated = []
        self.cache = {}

    def cached(self, video_id):
        return self.cache.get(video_id)

    def request(self, video_id):
        self.requests.append(video_id)
        if video_id in self.cache:
            self.resolved.emit(video_id, self.cache[video_id])

    def prefetch(self, video_ids):
        self.prefetched.extend(video_ids)

    def invalidate(self, video_id):
        self.invalidated.append(video_id)
        self.cache.pop(video_id, None)

    def resolve(self, video_id, url=None):
        info = StreamInfo(video_id, url or f"url-{video_id}", f"title-{video_id}", time.time() + 3600)
        self.resolved.emit(video_id, info)


class FakeCatalog:
    def __init__(self):
        self.calls = []

    def recommendations(self, video_id, limit, on_done, on_error=None, key=None):
        self.calls.append({"video_id": video_id, "limit": limit, "on_done": on_done,
                           "on_error": on_error, "key": key})

    def answer(self, index, tracks):
        self.calls[index]["on_done"](tracks)

    def fail(self, index, exc=None):
        self.calls[index]["on_error"](exc or RuntimeError("boom"))


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def info(self, text):
        self.messages.append(("info", text))

    def warning(self, text):
        self.messages.append(("warning", text))

    def error(self, text):
        self.messages.append(("error", text))
