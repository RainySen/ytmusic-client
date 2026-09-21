from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest


class ThumbnailCache(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._cache: dict[str, QPixmap] = {}
        self._pending: dict[str, list] = {}

    def request(self, url: str, callback):
        if not url:
            return
        if url in self._cache:
            callback(self._cache[url])
            return
        if url in self._pending:
            self._pending[url].append(callback)
            return
        self._pending[url] = [callback]
        reply = self._manager.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda: self._on_finished(url, reply))

    def _on_finished(self, url: str, reply):
        pixmap = QPixmap()
        if reply.error() == reply.NetworkError.NoError:
            pixmap.loadFromData(reply.readAll())
        reply.deleteLater()
        if not pixmap.isNull():
            self._cache[url] = pixmap
            for cb in self._pending.pop(url, []):
                try:
                    cb(pixmap)
                except RuntimeError:
                    pass  # widget deleted before thumbnail arrived
        else:
            self._pending.pop(url, None)
