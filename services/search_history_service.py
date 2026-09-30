from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from infra.json_store import read_json, write_json_atomic

HISTORY_LIMIT = 15


class SearchHistoryService(QObject):
    changed = Signal(list)

    def __init__(self, path: str, limit: int = HISTORY_LIMIT, parent: QObject | None = None):
        super().__init__(parent)
        self._path = path
        self._limit = limit
        data = read_json(path, [])
        self._items = [q for q in data if isinstance(q, str) and q.strip()][:limit] if isinstance(data, list) else []

    @property
    def items(self) -> list[str]:
        return list(self._items)

    def add(self, query: str) -> None:
        query = " ".join(query.split())
        if not query:
            return
        rest = [q for q in self._items if q.lower() != query.lower()]
        self._update([query] + rest)

    def remove(self, query: str) -> None:
        self._update([q for q in self._items if q != query])

    def clear(self) -> None:
        self._update([])

    def _update(self, items: list[str]) -> None:
        items = items[:self._limit]
        if items == self._items:
            return
        self._items = items
        write_json_atomic(self._path, items)
        self.changed.emit(list(items))
