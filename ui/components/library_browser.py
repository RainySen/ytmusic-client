import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from ui import imaging
from domain.models import LOCAL_SOURCES, thumbnail_url
from ui.components.chip import Chip
from ui.components.clickable import ClickableWidget
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.track_list import TrackList

CHIP_LABELS = ["Playlists", "Canciones", "Me gusta", "Artistas"]
GRID_COLUMNS = 4
LOAD_MORE_MARGIN = 200

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
        thumb.set_source(thumbnail_url(playlist, imaging.thumb_px(152)), thumbnails)
        layout.addWidget(thumb)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)
        title = QLabel(playlist.get("title", ""))
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e0e0e0;")
        title.setWordWrap(True)
        title.setMaximumWidth(140 if playlist.get("pinned") else 152)
        title_row.addWidget(title, 1)
        if playlist.get("pinned"):
            pin = QLabel()
            pin.setPixmap(qta.icon("fa5s.thumbtack", color="#aaa").pixmap(11, 11))
            pin.setToolTip("Fijada")
            title_row.addWidget(pin, alignment=Qt.AlignTop)
        layout.addLayout(title_row)

        local = playlist.get("source", "ytmusic") in LOCAL_SOURCES
        count = playlist.get("track_count", 0)
        meta = QLabel(f"{'Local' if local else 'YouTube Music'}{f'  •  {count} pistas' if count else ''}")
        meta.setStyleSheet("font-size: 11px; color: #888;")
        meta.setWordWrap(True)
        meta.setMaximumWidth(152)
        layout.addWidget(meta)

        self.activated.connect(lambda: self.chosen.emit(self.playlist))


class ArtistRow(QWidget):
    def __init__(self, artist, thumbnails, parent=None):
        super().__init__(parent)
        self.setFixedHeight(68)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 16, 8)
        layout.setSpacing(16)

        thumb = LazyThumbnail(48, circle=True, icon="fa5s.user")
        thumb.set_source(thumbnail_url(artist, imaging.thumb_px(48)), thumbnails)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(3)
        name = QLabel(artist.get("name") or artist.get("title") or artist.get("artist", ""))
        name.setStyleSheet("font-size: 14px; font-weight: 500; color: #e0e0e0;")
        info.addWidget(name)
        detail = f"{artist['count']} canciones" if artist.get("count") else artist.get("subscribers", "")
        if detail:
            count = QLabel(detail)
            count.setStyleSheet("font-size: 12px; color: #888;")
            info.addWidget(count)
        layout.addLayout(info, stretch=1)


class LibraryBrowserPanel(QWidget):
    playlist_activated = Signal(dict)
    song_activated = Signal(dict)
    song_add_next = Signal(dict)
    song_add_queue = Signal(dict)
    song_add_playlist = Signal(dict)
    song_hovered = Signal(dict)
    chip_selected = Signal(str)
    load_more_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chips = {}
        self._can_load_more = False
        self._loading_more = False

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
        self._scroll.verticalScrollBar().valueChanged.connect(self._maybe_load_more)
        self.songs: TrackList | None = None

    def _clear(self):
        while self._layout.count() > 1:
            widget = self._layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self._loading_more = False
        self._can_load_more = False
        self.songs = None

    def release(self):
        self._clear()

    def _maybe_load_more(self, value):
        bar = self._scroll.verticalScrollBar()
        if (self._can_load_more and not self._loading_more and self.songs is not None
                and value >= bar.maximum() - LOAD_MORE_MARGIN):
            self._loading_more = True
            self.songs.show_loading_more()
            self.load_more_requested.emit()

    def _start_songs(self, songs, thumbnails):
        listing = TrackList()
        listing.track_chosen.connect(lambda _position, song: self.song_activated.emit(song))
        listing.add_next_clicked.connect(self.song_add_next)
        listing.add_queue_clicked.connect(self.song_add_queue)
        listing.add_playlist_clicked.connect(self.song_add_playlist)
        listing.track_hovered.connect(self.song_hovered)
        listing.set_tracks(songs, thumbnails)
        self.songs = listing
        self._layout.insertWidget(0, listing)

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
            self.show_message("Aún no tienes playlists. Guarda una desde una canción o desde la cola.")
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

    # append: songs is only the new page
    def show_songs(self, songs, thumbnails, has_more=False, append=False):
        self.set_active_chip("Canciones")
        if append:
            self._append_page(songs, thumbnails, has_more)
            return
        self._clear()
        if not songs:
            self.show_message("No hay canciones guardadas todavía.")
            return
        self._can_load_more = has_more
        self._start_songs(songs, thumbnails)

    def show_liked(self, songs, thumbnails, has_more=False, append=False):
        self.set_active_chip("Me gusta")
        if append:
            self._append_page(songs, thumbnails, has_more)
            return
        self._clear()
        if songs is None:
            self.show_message("Inicia sesión para ver las canciones a las que les diste Me gusta.")
            return
        if not songs:
            self.show_message("Todavía no le diste Me gusta a ninguna canción.")
            return
        self._can_load_more = has_more
        self._start_songs(songs, thumbnails)

    def _append_page(self, songs, thumbnails, has_more):
        self._can_load_more = has_more
        self._loading_more = False
        if self.songs is not None:
            self.songs.hide_loading_more()
            if songs:
                self.songs.append_tracks(songs, thumbnails)

    def show_artists(self, artists, thumbnails):
        self.set_active_chip("Artistas")
        self._clear()
        if not artists:
            self.show_message("No hay artistas todavía.")
            return
        self._layout.insertWidget(0, self._list_of([ArtistRow(a, thumbnails) for a in artists]))

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
