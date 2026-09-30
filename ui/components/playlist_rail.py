from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from domain.models import LOCAL_SOURCES, thumbnail_url
from ui import imaging, theme
from ui.components.clickable import ClickableWidget
from ui.components.elided_label import ElidedLabel
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.track_actions import ActionsButton

ROW_HEIGHT = 48
THUMB_PX = 30


def _entries_for(playlist: dict) -> tuple:
    entries = [
        ("next", "Reproducir a continuación", "fa5s.step-forward"),
        ("queue", "Agregar a la cola", "fa5s.list"),
        ("pin", "Quitar de fijadas" if playlist.get("pinned") else "Fijar playlist", "fa5s.thumbtack"),
    ]
    if playlist.get("source") in LOCAL_SOURCES:
        entries.append(("delete", "Eliminar playlist", "fa5s.trash"))
    return tuple(entries)


class PlaylistRailRow(ClickableWidget):
    chosen = Signal(dict)
    play_next_requested = Signal(dict)
    add_queue_requested = Signal(dict)
    pin_toggled = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, playlist: dict, thumbnails, parent=None):
        super().__init__(parent, radius=8)
        self.playlist = playlist
        self.setFixedHeight(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(10)

        thumb = LazyThumbnail(THUMB_PX, radius=4, icon="fa5s.list", background="#222")
        thumb.set_source(thumbnail_url(playlist, imaging.thumb_px(THUMB_PX)), thumbnails)
        layout.addWidget(thumb)

        title = ElidedLabel(playlist.get("title", ""))
        title.setStyleSheet(f"font-size: 13px; color: {theme.TEXT}; background: transparent;")
        layout.addWidget(title, 1)

        if playlist.get("pinned"):
            pin = QLabel()
            pin.setPixmap(qta.icon("fa5s.thumbtack", color=theme.TEXT_SECONDARY).pixmap(11, 11))
            pin.setStyleSheet("background: transparent;")
            layout.addWidget(pin)

        self.actions = ActionsButton(_entries_for(playlist), size=26)
        self.actions.action_chosen.connect(self._dispatch)
        layout.addWidget(self.actions)

        self.activated.connect(lambda: self.chosen.emit(self.playlist))
        self.context_requested.connect(self.actions.show_menu)
        self.hover_changed.connect(self.actions.set_revealed)

    def _dispatch(self, key: str) -> None:
        {
            "next": self.play_next_requested, "queue": self.add_queue_requested,
            "pin": self.pin_toggled, "delete": self.delete_requested,
        }[key].emit(self.playlist)


class PlaylistRail(QWidget):
    playlist_chosen = Signal(dict)
    play_next_requested = Signal(dict)
    add_queue_requested = Signal(dict)
    pin_toggled = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 8, 0, 8)
        outer.setSpacing(2)

        header = QLabel("TUS PLAYLISTS")
        header.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px; "
                             f"padding: 4px 10px; background: transparent;")
        outer.addWidget(header)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(1)
        outer.addLayout(self._rows_layout)
        self._message = QLabel("Aún no tienes playlists.")
        self._message.setWordWrap(True)
        self._message.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; padding: 4px 10px; "
                                    f"background: transparent;")
        self._message.hide()
        outer.addWidget(self._message)
        outer.addStretch(1)

    def set_loading(self) -> None:
        self._set_rows([])
        self._message.setText("Cargando…")
        self._message.show()

    def set_playlists(self, playlists: list[dict], thumbnails) -> None:
        self._set_rows(playlists, thumbnails)
        self._message.setVisible(not playlists)
        self._message.setText("Aún no tienes playlists.")

    def _set_rows(self, playlists, thumbnails=None) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for playlist in playlists:
            row = PlaylistRailRow(playlist, thumbnails)
            row.chosen.connect(self.playlist_chosen)
            row.play_next_requested.connect(self.play_next_requested)
            row.add_queue_requested.connect(self.add_queue_requested)
            row.pin_toggled.connect(self.pin_toggled)
            row.delete_requested.connect(self.delete_requested)
            self._rows_layout.addWidget(row)
