from PySide6.QtCore import QObject, Signal


# navegacion senales
class Navigator(QObject):
    artist_requested = Signal(str)
    album_requested = Signal(str)
    playlist_requested = Signal(str)
