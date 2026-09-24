from __future__ import annotations

import threading

from infra.json_store import read_json, write_json_atomic


# playlists recientes
class RecentPlaylists:
    def __init__(self, path: str, limit: int = 8):
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

    def touch(self, playlist_id: str) -> None:
        with self._lock:
            ids = [playlist_id] + [i for i in self._load() if i != playlist_id]
            self._ids = ids[:self._limit]
            write_json_atomic(self._path, self._ids)
