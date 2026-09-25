from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot

log = logging.getLogger(__name__)

Callback = Callable[[Any], None]


class TaskHandle:
    __slots__ = ("key", "cancelled", "_runner", "_job", "_children")

    def __init__(self, runner: "TaskRunner", key: str | None):
        self.key = key
        self.cancelled = False
        self._runner = runner
        self._job: _Job | None = None
        self._children: list[TaskHandle] = []

    def cancel(self) -> bool:
        return self._runner._cancel(self)

    def cancel_if_queued(self) -> bool:
        return self._runner._cancel_if_queued(self)


# hilo principal callbacks
class _Dispatcher(QObject):
    finished = Signal(object)


class _Job(QRunnable):
    def __init__(self, fn: Callable[[], Any], handle: TaskHandle, dispatcher: _Dispatcher):
        super().__init__()
        self.setAutoDelete(False)
        self._fn = fn
        self._handle = handle
        self._dispatcher = dispatcher

    def run(self) -> None:
        try:
            outcome = (True, self._fn())
        except Exception as exc:
            outcome = (False, exc)
        try:
            self._dispatcher.finished.emit((self._handle, outcome))
        except RuntimeError:
            pass


# hilos pool callbacks
class TaskRunner(QObject):
    def __init__(self, name: str = "tasks", max_threads: int = 4, parent: QObject | None = None):
        super().__init__(parent)
        self.setObjectName(name)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_threads)
        self._dispatcher = _Dispatcher()
        self._dispatcher.finished.connect(self._deliver, Qt.QueuedConnection)
        self._latest: dict[str, TaskHandle] = {}
        self._live: dict[int, tuple[TaskHandle, Callback | None, Callback | None]] = {}

    # hilos tareas key
    def submit(
        self,
        fn: Callable[[], Any],
        on_success: Callback | None = None,
        on_error: Callback | None = None,
        *,
        key: str | None = None,
        priority: int = 0,
    ) -> TaskHandle:
        handle = TaskHandle(self, key)
        if key is not None:
            previous = self._latest.get(key)
            if previous is not None:
                previous.cancel()
            self._latest[key] = handle
        job = _Job(fn, handle, self._dispatcher)
        handle._job = job
        self._live[id(handle)] = (handle, on_success, on_error)
        self._pool.start(job, priority)
        return handle

    # hilos paralelo
    def gather(
        self,
        fns: list[Callable[[], Any]],
        on_done: Callback,
        *,
        key: str | None = None,
        priority: int = 0,
    ) -> TaskHandle:
        parent = TaskHandle(self, key)
        if key is not None:
            previous = self._latest.get(key)
            if previous is not None:
                previous.cancel()
            self._latest[key] = parent
        results: list[Any] = [None] * len(fns)
        remaining = [len(fns)]

        if not fns:
            on_done([])
            return parent

        def make_callbacks(slot: int):
            def finish(value: Any) -> None:
                results[slot] = value
                remaining[0] -= 1
                if remaining[0] == 0 and not parent.cancelled:
                    if key is not None and self._latest.get(key) is parent:
                        del self._latest[key]
                    self._call(on_done, results)
            return finish

        for slot, fn in enumerate(fns):
            cb = make_callbacks(slot)
            child = self.submit(fn, cb, cb, priority=priority)
            parent._children.append(child)
        return parent

    def _cancel(self, handle: TaskHandle) -> bool:
        handle.cancelled = True
        for child in handle._children:
            child.cancel()
        if handle.key is not None and self._latest.get(handle.key) is handle:
            del self._latest[handle.key]
        job = handle._job
        if job is not None and self._pool.tryTake(job):
            self._live.pop(id(handle), None)
            return True
        return False

    def _cancel_if_queued(self, handle: TaskHandle) -> bool:
        job = handle._job
        if job is not None and self._pool.tryTake(job):
            handle.cancelled = True
            self._live.pop(id(handle), None)
            if handle.key is not None and self._latest.get(handle.key) is handle:
                del self._latest[handle.key]
            return True
        return False

    def cancel_key(self, key: str) -> None:
        handle = self._latest.get(key)
        if handle is not None:
            handle.cancel()

    @Slot(object)
    def _deliver(self, envelope: tuple[TaskHandle, tuple[bool, Any]]) -> None:
        handle, (ok, payload) = envelope
        entry = self._live.pop(id(handle), None)
        if entry is None or handle.cancelled:
            return
        _, on_success, on_error = entry
        if handle.key is not None and self._latest.get(handle.key) is handle:
            del self._latest[handle.key]
        if ok:
            if on_success:
                self._call(on_success, payload)
        else:
            if on_error:
                self._call(on_error, payload)
            else:
                log.warning("Task %s failed: %r", handle.key or "", payload, exc_info=payload)

    @staticmethod
    def _call(callback: Callback, value: Any) -> None:
        try:
            callback(value)
        except RuntimeError as exc:
            log.debug("Dropped callback for a destroyed object: %s", exc)
        except Exception:
            log.exception("Unhandled error in task callback")

    def active_count(self) -> int:
        return self._pool.activeThreadCount()

    def shutdown(self, wait_ms: int = 300) -> bool:
        self._pool.clear()
        return self._pool.waitForDone(wait_ms)
