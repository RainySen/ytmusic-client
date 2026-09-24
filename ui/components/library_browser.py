from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from config import HOVER_PREFETCH_MS
from domain.models import LOCAL_SOURCES, artist_names, thumbnail_url
from ui.components.chip import Chip
from ui.components.clickable import ClickableWidget
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.track_actions import TrackActionsButton

CHIP_LABELS = ["Playlists", "Canciones", "Artistas"]
GRID_COLUMNS = 4

_SEPARATOR = "background: #1a1a1a; max-height: 1px;"


LibraryChip = Chip


class PlaylistCard(ClickableWidget):
    chosen = Signal(dict)

    def __init__(self, playlist, thumbnails, parent=None):
        super().__init__(parent, radius=8)
        self.playlist = playlist
        self.setFixedWidth(168)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 10)
        layout.setSpacing(6)

        thumb = LazyThumbnail(152, radius=6, icon="fa5s.list", background="#1e1e1e")
        thumb.set_source(thumbnail_url(playlist, 304), thumbnails)
        layout.addWidget(thumb)

        title = QLabel(playlist.get("title", ""))
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e0e0e0;")
        title.setWordWrap(True)
        title.setMaximumWidth(152)
        layout.addWidget(title)

        local = playlist.get("source", "ytmusic") in LOCAL_SOURCES
        count = playlist.get("track_count", 0)
        meta = QLabel(f"{'Local' if local else 'YouTube Music'}{f'  •  {count} pistas' if count else ''}")
        meta.setStyleSheet("font-size: 11px; color: #888;")
        meta.setWordWrap(True)
        meta.setMaximumWidth(152)
        layout.addWidget(meta)

        self.activated.connect(lambda: self.chosen.emit(self.playlist))


class SongRow(ClickableWidget):
    chosen = Signal(dict)
    add_next = Signal(dict)
    add_queue = Signal(dict)
    add_playlist = Signal(dict)
    hovered = Signal(dict)

    def __init__(self, song, thumbnails, parent=None):
        super().__init__(parent, dwell_ms=HOVER_PREFETCH_MS)
        self.song = song
        self.setFixedHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 16, 4)
        layout.setSpacing(12)

        thumb = LazyThumbnail(40, radius=4, background="#1e1e1e")
        thumb.set_source(thumbnail_url(song, 80), thumbnails)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(2)
        title = QLabel(song.get("title", ""))
        title.setStyleSheet("font-size: 13px; color: #e0e0e0;")
        artists = QLabel(artist_names(song))
        artists.setStyleSheet("font-size: 11px; color: #888;")
        info.addWidget(title)
        info.addWidget(artists)
        layout.addLayout(info, stretch=1)

        actions = TrackActionsButton()
        actions.add_next.connect(lambda: self.add_next.emit(self.song))
        actions.add_queue.connect(lambda: self.add_queue.emit(self.song))
        actions.add_playlist.connect(lambda: self.add_playlist.emit(self.song))
        layout.addWidget(actions)

        self.activated.connect(lambda: self.chosen.emit(self.song))
        self.hover_changed.connect(actions.set_revealed)
        self.context_requested.connect(actions.show_menu)
        self.dwelled.connect(lambda: self.hovered.emit(self.song))


class ArtistRow(QWidget):
    def __init__(self, artist, thumbnails, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 16, 8)
        layout.setSpacing(16)

        thumb = LazyThumbnail(48, circle=True, icon="fa5s.user")
        thumb.set_source(thumbnail_url(artist, 96), thumbnails)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(3)
        name = QLabel(artist.get("name", artist.get("artist", "")))
        name.setStyleSheet("font-size: 14px; font-weight: 500; color: #e0e0e0;")
        info.addWidget(name)
        if artist.get("count"):
            count = QLabel(f"{artist['count']} canciones")
            count.setStyleSheet("font-size: 12px; color: #888;")
            info.addWidget(count)
        layout.addLayout(info, stretch=1)


# biblioteca vista
class LibraryBrowserPanel(QWidget):
    playlist_activated = Signal(dict)
    song_activated = Signal(dict)
    song_add_next = Signal(dict)
    song_add_queue = Signal(dict)
    song_add_playlist = Signal(dict)
    song_hovered = Signal(dict)
    chip_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chips = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        header.setObjectName("lib_header")
        header.setFixedHeight(56)
        header.setStyleSheet("#lib_header { background: #0b0b0b; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        header_layout.setSpacing(8)
        for label in CHIP_LABELS:
            chip = LibraryChip(label)
            chip.setChecked(label == "Playlists")
            chip.clicked.connect(lambda _=False, l=label: self._on_chip_clicked(l))
            header_layout.addWidget(chip)
            self._chips[label] = chip
        header_layout.addStretch()
        outer.addWidget(header)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(_SEPARATOR)
        outer.addWidget(separator)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(16, 16, 16, 32)
        self._layout.setSpacing(0)
        self._layout.addStretch()
        self._scroll.setWidget(content)
        outer.addWidget(self._scroll, stretch=1)

    def _clear(self):
        while self._layout.count() > 1:
            widget = self._layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def set_active_chip(self, label):
        for name, chip in self._chips.items():
            chip.setChecked(name == label)

    def _on_chip_clicked(self, label):
        self.set_active_chip(label)
        self.chip_selected.emit(label)

    def show_message(self, text):
        self._clear()
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px; padding: 60px;")
        self._layout.insertWidget(0, label)

    def show_playlists(self, playlists, thumbnails):
        self.set_active_chip("Playlists")
        self._clear()
        if not playlists:
            self.show_message("Aún no tienes playlists. Importa una desde la barra lateral.")
            return
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(8)
        for position, playlist in enumerate(playlists):
            card = PlaylistCard(playlist, thumbnails)
            card.chosen.connect(self.playlist_activated)
            grid.addWidget(card, position // GRID_COLUMNS, position % GRID_COLUMNS)
        self._layout.insertWidget(0, grid_widget)

    def show_songs(self, songs, thumbnails):
        self.set_active_chip("Canciones")
        self._clear()
        if not songs:
            self.show_message("No hay canciones guardadas todavía.")
            return
        rows = [self._song_row(song, thumbnails) for song in songs]
        self._layout.insertWidget(0, self._list_of(rows))

    def show_artists(self, artists, thumbnails):
        self.set_active_chip("Artistas")
        self._clear()
        if not artists:
            self.show_message("No hay artistas todavía.")
            return
        self._layout.insertWidget(0, self._list_of([ArtistRow(a, thumbnails) for a in artists]))

    def _song_row(self, song, thumbnails):
        row = SongRow(song, thumbnails)
        row.chosen.connect(self.song_activated)
        row.add_next.connect(self.song_add_next)
        row.add_queue.connect(self.song_add_queue)
        row.add_playlist.connect(self.song_add_playlist)
        row.hovered.connect(self.song_hovered)
        return row

    @staticmethod
    def _list_of(rows):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for index, row in enumerate(rows):
            layout.addWidget(row)
            if index < len(rows) - 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setStyleSheet(_SEPARATOR)
                layout.addWidget(separator)
        return container
