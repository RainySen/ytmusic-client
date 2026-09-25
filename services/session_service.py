from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer

from domain.play_queue import PlayQueue
from infra.json_store import read_json, write_json_atomic
from services.stream_service import StreamService

log = logging.getLogger(__name__)

SAVE_DEBOUNCE_MS = 2000


# sesion cola guardar restaurar
class SessionService(QObject):
    def __init__(self, path: str, queue: PlayQueue, streams: StreamService, parent: QObject | None = None):
        super().__init__(parent)
        self._path = path
        self._queue = queue
        self._streams = streams
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SAVE_DEBOUNCE_MS)
        self._timer.timeout.connect(self.save)
        self._autosave = False
        self._restored = False

    def restore(self) -> None:
        self._restored = True
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

    def save(self) -> None:
        if not self._restored:
            return
        state = {
            "queue": self._queue.snapshot(),
            "current_index": self._queue.current_index,
            "streams": self._streams.export_state(),
        }
        write_json_atomic(self._path, state)
