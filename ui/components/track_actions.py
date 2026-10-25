import qtawesome as qta
from PySide6.QtCore import QObject, QPoint, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QPushButton

from core.i18n import t

# (key, label key, icon); the label is resolved on use: the language is set after imports
_SONG_SPECS = (
    ("next", "menus.song.next", "fa5s.angle-double-right"),
    ("queue", "menus.song.queue", "fa5s.list"),
    ("playlist", "menus.song.playlist", "fa5s.plus"),
)
_ARTIST_SPEC = ("artist", "menus.song.artist", "fa5s.user")
_PIN_SPEC = ("pin", "menus.song.pin", "fa5s.thumbtack")
_UNPIN_SPEC = ("pin", "menus.song.unpin", "fa5s.thumbtack")
_COLLECTION_SPECS = (
    ("shuffle", "menus.collection.shuffle", "fa5s.random"),
    ("mix", "menus.collection.mix", "fa5s.broadcast-tower"),
    ("next", "menus.collection.next", "fa5s.angle-double-right"),
    ("queue", "menus.collection.queue", "fa5s.list"),
    ("playlist", "menus.collection.playlist", "fa5s.plus"),
    ("share", "menus.collection.share", "fa5s.share"),
)


def _labeled(specs) -> tuple:
    return tuple((key, t(label), icon) for key, label, icon in specs)


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
    entries = list(_SONG_SPECS)
    if has_artist(song):
        entries.append(_ARTIST_SPEC)
    if song and song.get("videoId"):
        entries.append(_UNPIN_SPEC if song_hub.is_pinned(song) else _PIN_SPEC)
    return _labeled(entries)


def song_actions() -> tuple:
    return _labeled(_SONG_SPECS)


def collection_actions() -> tuple:
    return _labeled(_COLLECTION_SPECS)

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

    def __init__(self, parent=None, *, overlay: bool = False):
        style = dict(style=_OVERLAY_QSS, size=32, icon_color="white") if overlay else {}
        super().__init__(song_actions(), parent, **style)
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
        super().__init__(collection_actions(), parent, style=_OVERLAY_QSS, size=32, icon_color="white")
        self._revealed = True
        self._apply(True)

    def set_revealed(self, revealed: bool) -> None:
        self._revealed = True
