from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

CONNECT_TIMEOUT_MS = 400
WRITE_TIMEOUT_MS = 400
WAKE_MESSAGE = b"show"


# una sola instancia despertar la abierta
class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, key: str, parent: QObject | None = None):
        super().__init__(parent)
        self._key = key
        self._server: QLocalServer | None = None

    def claim(self) -> bool:
        if self._wake_existing():
            return False
        QLocalServer.removeServer(self._key)
        server = QLocalServer(self)
        server.setSocketOptions(QLocalServer.UserAccessOption)
        if not server.listen(self._key):
            return True
        server.newConnection.connect(self._on_connection)
        self._server = server
        return True

    def release(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None

    def _wake_existing(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._key)
        if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
            return False
        socket.write(WAKE_MESSAGE)
        socket.waitForBytesWritten(WRITE_TIMEOUT_MS)
        socket.disconnectFromServer()
        return True

    def _on_connection(self) -> None:
        while self._server is not None and self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            socket.disconnected.connect(socket.deleteLater)
            if socket.bytesAvailable():
                socket.readAll()
                self.activated.emit()
            else:
                socket.readyRead.connect(lambda s=socket: (s.readAll(), self.activated.emit()))
