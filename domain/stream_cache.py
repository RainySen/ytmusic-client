from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

DEFAULT_TTL_S = 3600


@dataclass(frozen=True)
class StreamInfo:
    video_id: str
    url: str
    title: str
    expires_at: float

    def is_valid(self, margin: float = 0.0, now: float | None = None) -> bool:
        return (now if now is not None else time.time()) + margin < self.expires_at

    def to_dict(self) -> dict:
        return {"url": self.url, "title": self.title, "expires_at": self.expires_at}

    @staticmethod
    def from_dict(video_id: str, data: dict) -> "StreamInfo":
        return StreamInfo(video_id, data["url"], data.get("title", ""), float(data["expires_at"]))


def expiry_from_url(url: str, default_ttl: float = DEFAULT_TTL_S, now: float | None = None) -> float:
    now = now if now is not None else time.time()
    try:
        values = parse_qs(urlparse(url).query).get("expire")
        if values:
            return float(values[0])
    except (ValueError, TypeError):
        pass
    return now + default_ttl


# cache streams expiracion
class StreamCache:
    def __init__(self, margin: float = 0.0, max_size: int = 256):
        self._items: "OrderedDict[str, StreamInfo]" = OrderedDict()
        self._margin = margin
        self._max_size = max_size

    def get(self, video_id: str) -> StreamInfo | None:
        info = self._items.get(video_id)
        if info is None:
            return None
        if not info.is_valid(self._margin):
            del self._items[video_id]
            return None
        self._items.move_to_end(video_id)
        return info

    def put(self, info: StreamInfo) -> None:
        self._items[info.video_id] = info
        self._items.move_to_end(info.video_id)
        while len(self._items) > self._max_size:
            self._items.popitem(last=False)

    def invalidate(self, video_id: str) -> None:
        self._items.pop(video_id, None)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def export(self) -> dict:
        return {vid: info.to_dict() for vid, info in self._items.items() if info.is_valid(self._margin)}

    def load(self, data: dict) -> int:
        loaded = 0
        for vid, raw in (data or {}).items():
            try:
                info = StreamInfo.from_dict(vid, raw)
            except (KeyError, TypeError, ValueError):
                continue
            if info.is_valid(self._margin):
                self._items[vid] = info
                loaded += 1
        return loaded
