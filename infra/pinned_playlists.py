from __future__ import annotations

import threading

from infra.json_store import read_json, write_json_atomic

DEFAULT_LIMIT = 20


class PinnedPlaylists:
    def __init__(self, path: str, limit: int = DEFAULT_LIMIT):
        self._path = path
        self._limit = limit
        self._lock = threading.Lock()
        self._ids: list[str] | None = None

    def _load(self) -> list[str]:
        if self._ids is None:
            data = read_json(self._path, [])
            self._ids = [i for i in data if isinstance(i, str)] if isinstance(data, list) else []
        return self._ids

    def ids(self) -> list[str]:
        with self._lock:
            return list(self._load())

    def is_pinned(self, playlist_id: str) -> bool:
        with self._lock:
            return playlist_id in self._load()

    def toggle(self, playlist_id: str) -> bool:
        with self._lock:
            ids = self._load()
            if playlist_id in ids:
                self._ids = [i for i in ids if i != playlist_id]
                pinned = False
            else:
                self._ids = [playlist_id] + ids[:self._limit - 1]
                pinned = True
            write_json_atomic(self._path, self._ids)
            return pinned

    def discard(self, playlist_id: str) -> None:
        with self._lock:
            ids = self._load()
            if playlist_id in ids:
                self._ids = [i for i in ids if i != playlist_id]
                write_json_atomic(self._path, self._ids)
