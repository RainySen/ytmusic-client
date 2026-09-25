from __future__ import annotations

import logging
from typing import Iterable, Protocol

from PySide6.QtCore import QObject, Signal

from domain.stream_cache import StreamCache, StreamInfo
from infra.concurrency import TaskHandle, TaskRunner

log = logging.getLogger(__name__)

MAX_QUEUED_PREFETCH = 6


class StreamResolver(Protocol):
    def resolve(self, video_id: str) -> StreamInfo: ...


# streams cache prefetch
class StreamService(QObject):
    resolved = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, resolver: StreamResolver, cache: StreamCache,
                 play_runner: TaskRunner, prefetch_runner: TaskRunner,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._resolver = resolver
        self._cache = cache
        self._play_runner = play_runner
        self._prefetch_runner = prefetch_runner
        self._inflight: dict[str, tuple[TaskHandle, bool]] = {}

    def cached(self, video_id: str) -> StreamInfo | None:
        return self._cache.get(video_id)

    def invalidate(self, video_id: str) -> None:
        self._cache.invalidate(video_id)

    def request(self, video_id: str) -> None:
        info = self._cache.get(video_id)
        if info is not None:
            self.resolved.emit(video_id, info)
            return
        flight = self._inflight.get(video_id)
        if flight is not None:
            handle, urgent = flight
            if urgent:
                return
            if not handle.cancel_if_queued():
                self._inflight[video_id] = (handle, True)
                return
            del self._inflight[video_id]
        self._submit(video_id, urgent=True)

    def prefetch(self, video_ids: Iterable[str]) -> None:
        for video_id in video_ids:
            if not video_id or self._cache.get(video_id) is not None or video_id in self._inflight:
                continue
            queued = sum(1 for _, urgent in self._inflight.values() if not urgent)
            if queued >= MAX_QUEUED_PREFETCH:
                return
            self._submit(video_id, urgent=False)

    def _submit(self, video_id: str, urgent: bool) -> None:
        runner = self._play_runner if urgent else self._prefetch_runner
        handle = runner.submit(
            lambda: self._resolver.resolve(video_id),
            lambda info: self._on_resolved(video_id, info),
            lambda exc: self._on_failed(video_id, exc),
        )
        self._inflight[video_id] = (handle, urgent)

    def _on_resolved(self, video_id: str, info: StreamInfo) -> None:
        self._inflight.pop(video_id, None)
        self._cache.put(info)
        self.resolved.emit(video_id, info)

    def _on_failed(self, video_id: str, exc: Exception) -> None:
        self._inflight.pop(video_id, None)
        log.warning("Could not resolve stream for %s: %s", video_id, exc)
        self.failed.emit(video_id, str(exc))

    def export_state(self) -> dict:
        return self._cache.export()

    def import_state(self, data: dict) -> int:
        return self._cache.load(data)

    def warm_up(self) -> None:
        warm = getattr(self._resolver, "warm_up", None)
        if warm:
            warm()
