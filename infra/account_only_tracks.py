from __future__ import annotations

import threading

from infra.json_store import read_json, write_json_atomic

DEFAULT_LIMIT = 500


# premium-only ids: skip the doomed anonymous attempt next run
class AccountOnlyTracks:
    def __init__(self, path: str | None = None, limit: int = DEFAULT_LIMIT):
        self._path = path
        self._limit = limit
        self._lock = threading.Lock()
        self._ids: list[str] | None = None

    def _load(self) -> list[str]:
        if self._ids is None:
            data = read_json(self._path, []) if self._path else []
            self._ids = [i for i in data if isinstance(i, str)] if isinstance(data, list) else []
        return self._ids

    def __contains__(self, video_id: str) -> bool:
        with self._lock:
            return video_id in self._load()

    def add(self, video_id: str) -> None:
        with self._lock:
            ids = self._load()
            if video_id in ids:
                return
            self._ids = [video_id, *ids][:self._limit]
            if self._path:
                write_json_atomic(self._path, self._ids)
