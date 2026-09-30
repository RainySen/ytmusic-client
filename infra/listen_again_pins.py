from __future__ import annotations

import threading

from infra.json_store import read_json, write_json_atomic

DEFAULT_LIMIT = 30


# local only: ytmusicapi has no pin api
class ListenAgainPins:
    def __init__(self, path: str, limit: int = DEFAULT_LIMIT):
        self._path = path
        self._limit = limit
        self._lock = threading.Lock()
        self._songs: list[dict] | None = None

    def _load(self) -> list[dict]:
        if self._songs is None:
            data = read_json(self._path, [])
            self._songs = [s for s in data if isinstance(s, dict) and s.get("videoId")] if isinstance(data, list) else []
        return self._songs

    def songs(self) -> list[dict]:
        with self._lock:
            return [dict(s) for s in self._load()]

    def is_pinned(self, video_id: str) -> bool:
        with self._lock:
            return any(s["videoId"] == video_id for s in self._load())

    def clear(self) -> None:
        with self._lock:
            self._songs = []
            write_json_atomic(self._path, self._songs)

    def toggle(self, song: dict) -> bool:
        video_id = song.get("videoId")
        if not video_id:
            return False
        with self._lock:
            songs = self._load()
            if any(s["videoId"] == video_id for s in songs):
                self._songs = [s for s in songs if s["videoId"] != video_id]
                pinned = False
            else:
                keep = {k: song[k] for k in ("videoId", "title", "artists", "album", "thumbnails", "duration")
                        if song.get(k)}
                self._songs = [{**keep, "type": "song"}] + songs[:self._limit - 1]
                pinned = True
            write_json_atomic(self._path, self._songs)
            return pinned
