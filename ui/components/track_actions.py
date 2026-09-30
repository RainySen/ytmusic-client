import qtawesome as qta
from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QPushButton

SONG_ACTIONS = (
    ("next", "Reproducir a continuación", "fa5s.angle-double-right"),
    ("queue", "Agregar a la cola", "fa5s.list"),
    ("playlist", "Agregar a una playlist", "fa5s.plus"),
)
ARTIST_ACTION = ("artist", "Ir al artista", "fa5s.user")
PIN_ACTION = ("pin", "Fijar en volver a escuchar", "fa5s.thumbtack")
UNPIN_ACTION = ("pin", "Quitar de volver a escuchar", "fa5s.thumbtack")


# song actions routed through one hub instead of every widget
class SongMenuHub(QObject):
    artist_requested = Signal(dict)
    pin_toggled = Signal(dict)

    def __init__(self):
        super().__init__()
        self.is_pinned = lambda _song: False

    def relay(self, key: str, song: dict) -> bool:
        if key == "artist":
            self.artist_requested.emit(song)
        elif key == "pin":
            self.pin_toggled.emit(song)
        else:
            return False
        return True


song_hub = SongMenuHub()


def has_artist(song: dict | None) -> bool:
    return any(isinstance(a, dict) and a.get("id") for a in (song or {}).get("artists") or [])


def song_entries(song: dict | None) -> tuple:
    entries = list(SONG_ACTIONS)
    if has_artist(song):
        entries.append(ARTIST_ACTION)
    if song and song.get("videoId"):
        entries.append(UNPIN_ACTION if song_hub.is_pinned(song) else PIN_ACTION)
    return tuple(entries)
COLLECTION_ACTIONS = (
    ("shuffle", "Reproducir aleatoriamente", "fa5s.random"),
    ("mix", "Comenzar mix", "fa5s.broadcast-tower"),
    ("next", "Reproducir a continuación", "fa5s.angle-double-right"),
    ("queue", "Agregar a la cola", "fa5s.list"),
    ("playlist", "Guardar en una playlist", "fa5s.plus"),
    ("share", "Compartir", "fa5s.share"),
)

MENU_QSS = """
    QMenu { background: #282828; border: 1px solid #383838; border-radius: 8px; padding: 6px; }
    QMenu::item { padding: 9px 20px 9px 14px; border-radius: 4px; color: #e0e0e0; }
    QMenu::item:selected { background: rgba(255,255,255,0.10); }
"""
_BUTTON_QSS = """
    QPushButton { background: transparent; border: none; border-radius: 14px; }
    QPushButton:hover { background: rgba(255,255,255,0.15); }
    QPushButton:disabled { background: transparent; }
"""
_OVERLAY_QSS = """
    QPushButton { background: rgba(0,0,0,0.60); border: none; border-radius: 16px; }
    QPushButton:hover { background: rgba(0,0,0,0.85); }
"""


class ActionsButton(QPushButton):
    action_chosen = Signal(str)
    menu_opened = Signal()
    menu_closed = Signal()

    def __init__(self, entries, parent=None, *, style=_BUTTON_QSS, size=28, icon_color="#ccc"):
        super().__init__(parent)
        self._entries = tuple(entries)
        self._icon = qta.icon("fa5s.ellipsis-v", color=icon_color)
        self._revealed = False
        self._menu_open = False
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(style)
        self.clicked.connect(lambda: self.show_menu())
        self._apply(False)

    @property
    def menu_is_open(self) -> bool:
        return self._menu_open

    def set_revealed(self, revealed: bool) -> None:
        self._revealed = revealed
        if not self._menu_open:
            self._apply(revealed)

    def _apply(self, revealed: bool) -> None:
        self.setIcon(self._icon if revealed else QIcon())
        self.setEnabled(revealed)

    def show_menu(self, global_pos: QPoint | None = None) -> None:
        if self.isHidden() or self._menu_open:
            return
        menu = QMenu(self.window())
        menu.setStyleSheet(MENU_QSS)
        actions = {menu.addAction(qta.icon(icon, color="#e0e0e0"), label): key
                   for key, label, icon in self._current_entries()}
        if global_pos is None:
            global_pos = self.mapToGlobal(self.rect().bottomRight())
            global_pos.setX(global_pos.x() - menu.sizeHint().width())
        self._menu_open = True
        self.menu_opened.emit()
        try:
            chosen = menu.exec(global_pos)
        finally:
            self._menu_open = False
            self._apply(self._revealed)
            menu.deleteLater()
            self.menu_closed.emit()
        if chosen in actions:
            self.action_chosen.emit(actions[chosen])

    def _current_entries(self):
        return self._entries


class TrackActionsButton(ActionsButton):
    add_next = Signal()
    add_queue = Signal()
    add_playlist = Signal()

    def __init__(self, parent=None):
        super().__init__(SONG_ACTIONS, parent)
        self.song: dict | None = None
        self.action_chosen.connect(self._relay)

    def _current_entries(self):
        return song_entries(self.song)

    def _relay(self, key: str) -> None:
        if self.song is not None and song_hub.relay(key, self.song):
            return
        {"next": self.add_next, "queue": self.add_queue, "playlist": self.add_playlist}[key].emit()


class CollectionActionsButton(ActionsButton):
    def __init__(self, parent=None):
        super().__init__(COLLECTION_ACTIONS, parent, style=_OVERLAY_QSS, size=32, icon_color="white")
        self._revealed = True
        self._apply(True)

    def set_revealed(self, revealed: bool) -> None:
        self._revealed = True
