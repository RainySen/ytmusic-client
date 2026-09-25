from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget

from domain.models import thumbnail_url
from ui import theme
from ui.components.page_parts import MessagePage, back_button, heading, outline_button, pill_button
from ui.components.section_feed import SectionFeed
from ui.components.track_list import TrackList

BANNER_HEIGHT = 360
BANNER_REQUEST_PX = 1600
SIDE_MARGIN = 48


# banner artista
class _Banner(QWidget):
    def __init__(self, profile, thumbnails, on_back, on_shuffle, on_mix, parent=None):
        super().__init__(parent)
        self.setFixedHeight(BANNER_HEIGHT)
        self._thumbnails = thumbnails
        self._url = thumbnail_url({"thumbnails": profile.get("banner")}, BANNER_REQUEST_PX)
        self._pixmap = None
        self._scaled = None
        self._requested = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SIDE_MARGIN, 20, SIDE_MARGIN, 8)
        layout.setSpacing(6)
        back = back_button()
        back.clicked.connect(on_back)
        layout.addWidget(back, alignment=Qt.AlignLeft)
        layout.addStretch()

        name = QLabel(profile.get("name", ""))
        name.setWordWrap(True)
        name.setStyleSheet(f"font-size: 46px; font-weight: 800; color: {theme.TEXT}; background: transparent;")
        layout.addWidget(name)
        if profile.get("subscribers"):
            subs = QLabel(f"{profile['subscribers']} suscriptores")
            subs.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_SECONDARY}; background: transparent;")
            layout.addWidget(subs)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.shuffle_button = pill_button("Aleatorio", "primary", "fa5s.random")
        self.shuffle_button.setToolTip("Reproducir toda su discografía en orden aleatorio")
        self.shuffle_button.clicked.connect(on_shuffle)
        self.mix_button = pill_button("Mix", "tonal", "fa5s.broadcast-tower")
        self.mix_button.setToolTip("Una radio a partir de una de sus canciones")
        self.mix_button.clicked.connect(on_mix)
        buttons.addWidget(self.shuffle_button)
        buttons.addWidget(self.mix_button)
        buttons.addStretch()
        layout.addLayout(buttons)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._requested and self._url:
            self._requested = True
            self._thumbnails.request(self._url, self._on_image)

    def _on_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._rescale()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pixmap is None or self.width() < 2:
            return
        dpr = self.devicePixelRatioF()
        width, height = round(self.width() * dpr), round(self.height() * dpr)
        scaled = self._pixmap.scaled(width, height, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        scaled = scaled.copy((scaled.width() - width) // 2, (scaled.height() - height) // 4, width, height)
        scaled.setDevicePixelRatio(dpr)
        self._scaled = scaled

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.BG))
        if self._scaled is not None:
            painter.drawPixmap(0, 0, self._scaled)
        rect = QRectF(self.rect())
        fade = QLinearGradient(0, 0, 0, rect.height())
        fade.setColorAt(0.0, QColor(15, 15, 15, 110))
        fade.setColorAt(0.35, QColor(15, 15, 15, 0))
        fade.setColorAt(0.75, QColor(15, 15, 15, 150))
        fade.setColorAt(1.0, QColor(15, 15, 15, 255))
        painter.fillRect(rect, fade)
        painter.end()


# pagina artista
class ArtistPanel(QWidget):
    back_requested = Signal()
    shuffle_requested = Signal()
    mix_requested = Signal()
    show_all_requested = Signal()
    song_chosen = Signal(dict)
    song_hovered = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    collection_action_requested = Signal(str, dict)
    item_clicked = Signal(dict)
    item_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.feed = SectionFeed()
        for name in ("item_clicked", "add_next_clicked", "add_queue_clicked", "add_playlist_clicked", "collection_action_requested",
                     "item_hovered"):
            getattr(self.feed, name).connect(getattr(self, name))
        outer.addWidget(self.feed)
        self.songs = None

    def set_loading(self):
        self.feed.clear()
        self.feed.set_header(None)
        self.feed.set_loading()

    def show_message(self, text):
        self.feed.clear()
        self.feed.set_header(MessagePage(text, self.back_requested.emit))

    def show_profile(self, profile, thumbnails):
        header = QWidget()
        column = QVBoxLayout(header)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        banner = _Banner(profile, thumbnails, self.back_requested.emit, self.shuffle_requested.emit,
                         self.mix_requested.emit)
        self.shuffle_button, self.mix_button = banner.shuffle_button, banner.mix_button
        column.addWidget(banner)

        songs = profile.get("top_songs") or []
        if songs:
            block = QWidget()
            inner = QVBoxLayout(block)
            inner.setContentsMargins(SIDE_MARGIN, 12, SIDE_MARGIN, 0)
            inner.setSpacing(8)
            inner.addWidget(heading("Canciones más populares"))
            self.songs = self._song_list(songs, thumbnails, show_album=True)
            inner.addWidget(self.songs)
            if profile.get("songs_browse_id"):
                self.show_all_button = outline_button("Mostrar todo")
                self.show_all_button.clicked.connect(self.show_all_requested)
                inner.addWidget(self.show_all_button, alignment=Qt.AlignLeft)
            column.addWidget(block)

        self.feed.clear()
        self.feed.set_header(header)
        self.feed.set_sections(profile.get("sections") or [], thumbnails, empty_message="")
        self.feed.scroll_to_top()

    def show_all_songs(self, name, tracks, thumbnails):
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(SIDE_MARGIN, 24, SIDE_MARGIN, 24)
        column.setSpacing(12)
        button = back_button()
        button.clicked.connect(self.back_requested)
        column.addWidget(button, alignment=Qt.AlignLeft)
        column.addWidget(heading("Canciones más populares", 34))
        by = QLabel(name)
        by.setStyleSheet(f"font-size: 15px; color: {theme.TEXT_SECONDARY};")
        column.addWidget(by)
        self.songs = self._song_list(tracks, thumbnails, show_album=True)
        column.addWidget(self.songs)
        self.feed.clear()
        self.feed.set_header(page)
        self.feed.scroll_to_top()

    def _song_list(self, tracks, thumbnails, **options):
        songs = TrackList()
        songs.track_chosen.connect(lambda _position, track: self.song_chosen.emit(track))
        songs.add_next_clicked.connect(self.add_next_clicked)
        songs.add_queue_clicked.connect(self.add_queue_clicked)
        songs.add_playlist_clicked.connect(self.add_playlist_clicked)
        songs.track_hovered.connect(self.song_hovered)
        songs.set_tracks(tracks, thumbnails, show_artist=False, **options)
        return songs
