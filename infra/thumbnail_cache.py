from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Callable

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkReply, QNetworkRequest

log = logging.getLogger(__name__)

PixmapCallback = Callable[[QPixmap], None]


class ThumbnailCache(QObject):
    def __init__(self, cache_dir: str | None = None, max_items: int = 400,
                 disk_bytes: int = 150 * 1024 * 1024, max_memory_mb: int = 20,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        if cache_dir:
            disk = QNetworkDiskCache(self)
            disk.setCacheDirectory(cache_dir)
            disk.setMaximumCacheSize(disk_bytes)
            self._manager.setCache(disk)
        self._memory: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._max_items = max_items
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._memory_bytes = 0
        self._pending: dict[str, list[PixmapCallback]] = {}

    def clear_memory(self) -> None:
        self._memory.clear()
        self._memory_bytes = 0

    def set_max_items(self, max_items: int) -> None:
        self._max_items = max_items
        self._trim()

    def disk_size(self) -> int:
        disk = self._manager.cache()
        return int(disk.cacheSize()) if disk is not None else 0

    def clear_disk(self) -> None:
        disk = self._manager.cache()
        if disk is not None:
            disk.clear()
        self.clear_memory()

    def request(self, url: str, callback: PixmapCallback) -> None:
        if not url:
            return
        cached = self._memory.get(url)
        if cached is not None:
            self._memory.move_to_end(url)
            self._invoke(callback, cached)
            return
        waiting = self._pending.get(url)
        if waiting is not None:
            waiting.append(callback)
            return
        self._pending[url] = [callback]
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(QNetworkRequest.CacheLoadControlAttribute, QNetworkRequest.PreferCache)
        request.setTransferTimeout(15000)
        reply = self._manager.get(request)
        reply.finished.connect(lambda: self._on_finished(url, reply))

    def _on_finished(self, url: str, reply: QNetworkReply) -> None:
        pixmap = QPixmap()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pixmap.loadFromData(reply.readAll())
        reply.deleteLater()
        callbacks = self._pending.pop(url, [])
        if pixmap.isNull():
            log.debug("Thumbnail failed: %s", url)
            return
        self._store(url, pixmap)
        for callback in callbacks:
            self._invoke(callback, pixmap)

    def _store(self, url: str, pixmap: QPixmap) -> None:
        previous = self._memory.pop(url, None)
        if previous is not None:
            self._memory_bytes -= self._weight(previous)
        self._memory[url] = pixmap
        self._memory_bytes += self._weight(pixmap)
        self._trim()

    # LRU: item count and byte budget
    def _trim(self) -> None:
        while self._memory and (len(self._memory) > self._max_items or
                                self._memory_bytes > self._max_memory_bytes):
            _url, old = self._memory.popitem(last=False)
            self._memory_bytes -= self._weight(old)

    @staticmethod
    def _weight(pixmap: QPixmap) -> int:
        return pixmap.width() * pixmap.height() * 4

    @staticmethod
    def _invoke(callback: PixmapCallback, pixmap: QPixmap) -> None:
        try:
            callback(pixmap)
        except RuntimeError:
            pass
