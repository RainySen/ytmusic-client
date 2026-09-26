from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer

from domain.play_queue import PlayQueue
from infra.concurrency import TaskRunner
from infra.json_store import read_json, write_json_atomic
from services.stream_service import StreamService

log = logging.getLogger(__name__)

SAVE_DEBOUNCE_MS = 2000


# sesion cola guardar restaurar
class SessionService(QObject):
    def __init__(self, path: str, queue: PlayQueue, streams: StreamService, parent: QObject | None = None,
                 runner: TaskRunner | None = None):
        super().__init__(parent)
        self._runner = runner
        self._seq = 0
        self._path = path
        self._queue = queue
        self._streams = streams
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SAVE_DEBOUNCE_MS)
        self._timer.timeout.connect(self.save)
        self._autosave = False
        self._restored = False

    def restore(self, load: bool = True) -> None:
        self._restored = True
        if not load:
            return
        data = read_json(self._path)
        if not isinstance(data, dict):
            return
        songs = data.get("queue") or []
        self._queue.restore(songs, data.get("current_index", -1))
        streams = data.get("streams")
        if isinstance(streams, dict):
            loaded = self._streams.import_state(streams)
            log.info("Restored %d queued songs and %d stream URLs", len(self._queue), loaded)

    def enable_autosave(self) -> None:
        if not self._autosave:
            self._autosave = True
            self._queue.changed.connect(self._timer.start)

    # guardar en segundo plano las colas grandes
    def save(self, wait: bool = False) -> None:
        if not self._restored:
            return
        state = {
            "queue": self._queue.snapshot(),
            "current_index": self._queue.current_index,
            "streams": self._streams.export_state(),
        }
        self._seq += 1
        seq = self._seq
        if self._runner is None or wait:
            write_json_atomic(self._path, state)
            return
        self._runner.submit(lambda: self._write_if_latest(seq, state), key="session-save")

    def _write_if_latest(self, seq: int, state: dict) -> None:
        if seq == self._seq:
            write_json_atomic(self._path, state)
