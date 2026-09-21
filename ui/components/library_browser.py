import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QFrame, QPushButton, QGridLayout
)

from utils import get_thumbnail_url, scale_cover

CHIP_LABELS = ["Playlists", "Canciones", "Artistas"]


class LibraryChip(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self._apply_style()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._apply_style()

    def _apply_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background: #212121;
                    color: white;
                    border: 1.5px solid white;
                    border-radius: 16px;
                    padding: 6px 18px;
                    font-size: 13px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #ccc;
                    border: 1px solid #3a3a3a;
                    border-radius: 16px;
                    padding: 6px 18px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    border-color: #777;
                    background: rgba(255,255,255,0.05);
                }
            """)


class PlaylistCard(QWidget):
    clicked = Signal(dict)

    def __init__(self, playlist, parent=None):
        super().__init__(parent)
        self.playlist = playlist
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(168)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 10)
        layout.setSpacing(6)

        self.thumb = QLabel()
        self.thumb.setFixedSize(152, 152)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border-radius: 6px; background: #1e1e1e;")
        self.thumb.setPixmap(qta.icon('fa5s.list', color='#555').pixmap(48, 48))
        layout.addWidget(self.thumb)

        title = QLabel(playlist.get('title', ''))
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e0e0e0;")
        title.setWordWrap(True)
        title.setMaximumWidth(152)
        layout.addWidget(title)

        source = playlist.get('source', 'ytmusic')
        source_text = 'Local' if source in ('local', 'imported', 'user_created') else 'YouTube Music'
        count = playlist.get('track_count', 0)
        meta = f"{source_text}{'  •  ' + str(count) + ' pistas' if count else ''}"
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet("font-size: 11px; color: #888;")
        meta_lbl.setWordWrap(True)
        meta_lbl.setMaximumWidth(152)
        layout.addWidget(meta_lbl)

        self._update_bg()

    def set_thumbnail(self, pixmap):
        self.thumb.setPixmap(scale_cover(pixmap, 152))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.playlist)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_bg()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_bg()
        super().leaveEvent(event)

    def _update_bg(self):
        bg = "rgba(255,255,255,0.06)" if self._hovered else "transparent"
        self.setStyleSheet(f"PlaylistCard {{ background: {bg}; border-radius: 8px; }}")


class SongRow(QWidget):
    clicked = Signal(dict)

    def __init__(self, song, parent=None):
        super().__init__(parent)
        self.song = song
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 16, 4)
        layout.setSpacing(12)

        self.thumb = QLabel()
        self.thumb.setFixedSize(40, 40)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border-radius: 4px; background: #1e1e1e;")
        self.thumb.setPixmap(qta.icon('fa5s.music', color='#444').pixmap(20, 20))
        layout.addWidget(self.thumb)

        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        title_lbl = QLabel(song.get('title', ''))
        title_lbl.setStyleSheet("font-size: 13px; color: #e0e0e0;")
        artist_names = ' • '.join(a.get('name', '') for a in song.get('artists', []))
        artist_lbl = QLabel(artist_names)
        artist_lbl.setStyleSheet("font-size: 11px; color: #888;")
        info_layout.addWidget(title_lbl)
        info_layout.addWidget(artist_lbl)
        layout.addWidget(info, stretch=1)

        self._update_bg()

    def set_thumbnail(self, pixmap):
        self.thumb.setPixmap(scale_cover(pixmap, 40))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.song)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_bg()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_bg()
        super().leaveEvent(event)

    def _update_bg(self):
        bg = "rgba(255,255,255,0.06)" if self._hovered else "transparent"
        self.setStyleSheet(f"SongRow {{ background: {bg}; border-radius: 6px; }}")


class ArtistRow(QWidget):
    def __init__(self, artist, parent=None):
        super().__init__(parent)
        self._hovered = False
        self.setFixedHeight(68)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 16, 8)
        layout.setSpacing(16)

        self.thumb = QLabel()
        self.thumb.setFixedSize(48, 48)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border-radius: 24px; background: #2a2a2a;")
        self.thumb.setPixmap(qta.icon('fa5s.user', color='#555').pixmap(24, 24))
        layout.addWidget(self.thumb)

        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        name = artist.get('name', artist.get('artist', ''))
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #e0e0e0;")
        info_layout.addWidget(name_lbl)

        count = artist.get('count', 0)
        if count:
            count_lbl = QLabel(f"{count} canciones")
            count_lbl.setStyleSheet("font-size: 12px; color: #888;")
            info_layout.addWidget(count_lbl)

        layout.addWidget(info, stretch=1)
        self._update_bg()

    def set_thumbnail(self, pixmap):
        self.thumb.setPixmap(scale_cover(pixmap, 48))
        self.thumb.setStyleSheet("border-radius: 24px;")

    def enterEvent(self, event):
        self._hovered = True
        self._update_bg()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_bg()
        super().leaveEvent(event)

    def _update_bg(self):
        bg = "rgba(255,255,255,0.04)" if self._hovered else "transparent"
        self.setStyleSheet(f"ArtistRow {{ background: {bg}; border-radius: 8px; }}")


class LibraryBrowserPanel(QWidget):
    playlist_activated = Signal(dict)
    song_activated = Signal(dict)
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
            chip.clicked.connect(lambda checked, l=label: self._on_chip_clicked(l))
            header_layout.addWidget(chip)
            self._chips[label] = chip

        header_layout.addStretch()
        outer.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #1a1a1a; max-height: 1px;")
        outer.addWidget(sep)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._clayout = QVBoxLayout(self._content)
        self._clayout.setContentsMargins(16, 16, 16, 32)
        self._clayout.setSpacing(0)
        self._clayout.addStretch()
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll, stretch=1)

    def _clear(self):
        while self._clayout.count() > 1:
            item = self._clayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _set_chip(self, label):
        """Update chip UI without emitting chip_selected (used by show_* methods)."""
        for l, chip in self._chips.items():
            chip.setChecked(l == label)

    def _on_chip_clicked(self, label):
        """Called when user clicks a chip — updates UI and emits signal."""
        self._set_chip(label)
        self.chip_selected.emit(label)

    def show_playlists(self, playlists, thumbnail_cache):
        self._set_chip("Playlists")
        self._clear()

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(8)

        cols = 4
        for i, pl in enumerate(playlists):
            card = PlaylistCard(pl)
            card.clicked.connect(self.playlist_activated)
            grid.addWidget(card, i // cols, i % cols)
            url = get_thumbnail_url(pl)
            if url:
                try:
                    thumbnail_cache.request(url, card.set_thumbnail)
                except RuntimeError:
                    pass

        self._clayout.insertWidget(0, grid_widget)

    def show_songs(self, songs, thumbnail_cache):
        self._set_chip("Canciones")
        self._clear()

        list_w = QWidget()
        list_l = QVBoxLayout(list_w)
        list_l.setContentsMargins(0, 0, 0, 0)
        list_l.setSpacing(0)

        sep_style = "background: #1a1a1a; max-height: 1px;"
        for i, song in enumerate(songs):
            row = SongRow(song)
            row.clicked.connect(self.song_activated)
            list_l.addWidget(row)
            if i < len(songs) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet(sep_style)
                list_l.addWidget(sep)
            url = get_thumbnail_url(song)
            if url:
                try:
                    thumbnail_cache.request(url, row.set_thumbnail)
                except RuntimeError:
                    pass

        self._clayout.insertWidget(0, list_w)

    def show_artists(self, artists, thumbnail_cache):
        self._set_chip("Artistas")
        self._clear()

        list_w = QWidget()
        list_l = QVBoxLayout(list_w)
        list_l.setContentsMargins(0, 0, 0, 0)
        list_l.setSpacing(0)

        sep_style = "background: #1a1a1a; max-height: 1px;"
        for i, artist in enumerate(artists):
            row = ArtistRow(artist)
            list_l.addWidget(row)
            if i < len(artists) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet(sep_style)
                list_l.addWidget(sep)
            url = get_thumbnail_url(artist)
            if url:
                try:
                    thumbnail_cache.request(url, row.set_thumbnail)
                except RuntimeError:
                    pass

        self._clayout.insertWidget(0, list_w)
