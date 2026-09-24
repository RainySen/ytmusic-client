from __future__ import annotations

import time
from typing import Any, Callable

_MISSING = object()


# cache ttl
class TTLCache:
    def __init__(self, clock: Callable[[], float] = time.monotonic, max_items: int = 256):
        self._clock = clock
        self._max_items = max_items
        self._items: dict[Any, tuple[float, Any]] = {}

    def get(self, key: Any, default: Any = None) -> Any:
        entry = self._items.get(key, _MISSING)
        if entry is _MISSING:
            return default
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._items[key]
            return default
        return value

    def set(self, key: Any, value: Any, ttl: float) -> None:
        if len(self._items) >= self._max_items and key not in self._items:
            oldest = min(self._items, key=lambda k: self._items[k][0])
            del self._items[oldest]
        self._items[key] = (self._clock() + ttl, value)

    def clear(self) -> None:
        self._items.clear()
