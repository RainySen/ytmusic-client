import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from core.i18n import t
from domain.models import artist_list, thumbnail_url
from ui import imaging, theme
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.page_parts import MessagePage, back_button
from ui.components.section_feed import CardsSection
from ui.components.track_actions import ActionsButton, collection_actions
from ui.components.track_list import TrackList

COVER_SIZE = 300
INFO_WIDTH = 340
DESCRIPTION_CHARS = 220
LOAD_MORE_MARGIN = 200


def _play_qss() -> str:
    return f"""
        QPushButton {{ background: {theme.BUTTON_BG}; border: none; border-radius: {theme.radius(28)}px; }}
        QPushButton:hover {{ background: {theme.HOVER}; }}
        QPushButton:pressed {{ background: {theme.PRESSED}; }}
    """


def _round_qss() -> str:
    return f"""
        QPushButton {{ background: {theme.overlay(0.12)}; border: none; border-radius: {theme.radius(22)}px; }}
        QPushButton:hover {{ background: {theme.overlay(0.22)}; }}
    """


def _link_qss() -> str:
    return f"""
        QPushButton {{ background: transparent; border: none; color: {theme.TEXT}; font-size: 15px;
                       font-weight: 600; padding: 0; text-align: left; }}
        QPushButton:hover {{ text-decoration: underline; }}
    """


def _round_button(icon, size, style, tooltip, icon_color):
    button = QPushButton()
    button.setIcon(qta.icon(icon, color=icon_color))
    button.setFixedSize(size, size)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(style)
    button.setToolTip(tooltip)
    return button


class AlbumPanel(QWidget):
    back_requested = Signal()
    play_requested = Signal()
    shuffle_requested = Signal()
    track_chosen = Signal(int, dict)
    track_hovered = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    artist_clicked = Signal(str)
    item_clicked = Signal(dict)
    collection_action_requested = Signal(str, dict)
    load_more_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(self._scroll)
        self.tracks = None
        self._can_load_more = False
        self._loading_more = False
        self._scroll.verticalScrollBar().valueChanged.connect(self._maybe_load_more)

    def set_loading(self):
        self._scroll.setWidget(MessagePage(t("album.loading"), self.back_requested.emit))

    def release(self):
        self.tracks = None
        self._can_load_more = False
        self._loading_more = False
        self._scroll.setWidget(QWidget())

    def show_message(self, text):
        self._scroll.setWidget(MessagePage(text, self.back_requested.emit))

    def show_album(self, album, thumbnails):
        item = {"type": "album", "browseId": album["id"], "title": album["title"]}
        album_artists = set(artist_list(album))
        others = any(name not in album_artists for t in album["tracks"] for name in artist_list(t))
        self._show(album, thumbnails, item, self._artist_links(album.get("artists") or []),
                   dict(numbered=True, show_cover=False, show_artist=others, show_album=False))

    def show_playlist(self, playlist, thumbnails):
        item = {"type": "playlist", "playlistId": playlist["id"], "title": playlist["title"]}
        owner = []
        if playlist.get("author"):
            owner = self._artist_links([{"name": playlist["author"], "id": playlist.get("author_id", "")}])
        self._show(playlist, thumbnails, item, owner,
                   dict(numbered=False, show_cover=True, show_artist=True, show_album=True))

    def _maybe_load_more(self, value):
        bar = self._scroll.verticalScrollBar()
        if (self._can_load_more and not self._loading_more and self.tracks is not None
                and not self.tracks.building and value >= bar.maximum() - LOAD_MORE_MARGIN):
            self._loading_more = True
            self.tracks.show_loading_more()
            self.load_more_requested.emit()

    def update_tracks(self, new_tracks, has_more, thumbnails):
        self._loading_more = False
        self._can_load_more = has_more
        self.tracks.hide_loading_more()
        if new_tracks:
            self.tracks.append_tracks(new_tracks, thumbnails)

    def load_more_failed(self):
        self._loading_more = False
        self._can_load_more = False
        if self.tracks is not None:
            self.tracks.hide_loading_more()

    def _show(self, data, thumbnails, item, byline, row_options):
        self._loading_more = False
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(48, 24, 48, 32)
        column.setSpacing(28)
        button = back_button()
        button.clicked.connect(self.back_requested)
        column.addWidget(button, alignment=Qt.AlignLeft)

        body = QHBoxLayout()
        body.setSpacing(40)
        body.addWidget(self._info(data, thumbnails, item, byline), alignment=Qt.AlignTop)

        self.tracks = TrackList()
        self.tracks.track_chosen.connect(self.track_chosen)
        self.tracks.add_next_clicked.connect(self.add_next_clicked)
        self.tracks.add_queue_clicked.connect(self.add_queue_clicked)
        self.tracks.add_playlist_clicked.connect(self.add_playlist_clicked)
        self.tracks.track_hovered.connect(self.track_hovered)
        self.tracks.set_tracks(data["tracks"], thumbnails, **row_options)
        body.addWidget(self.tracks, stretch=1, alignment=Qt.AlignTop)
        column.addLayout(body)

        if data.get("more"):
            more = CardsSection(t("album.more"), data["more"], thumbnails, title_px=22)
            more.item_clicked.connect(self.item_clicked)
            more.collection_action_requested.connect(self.collection_action_requested)
            column.addWidget(more)
        column.addStretch()
        self._can_load_more = bool(data.get("has_more"))
        self._scroll.setWidget(page)

    def _artist_links(self, artists):
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignHCenter)
        for position, artist in enumerate(artists[:3]):
            link = QPushButton(artist.get("name", ""))
            link.setStyleSheet(_link_qss())
            if str(artist.get("id", "")).startswith("UC"):
                link.setCursor(Qt.PointingHandCursor)
                link.clicked.connect(lambda _=False, i=artist["id"]: self.artist_clicked.emit(i))
            if position:
                row.addWidget(self._muted(","))
            row.addWidget(link)
        return [row] if artists else []

    def _info(self, data, thumbnails, item, byline):
        info = QWidget()
        info.setFixedWidth(INFO_WIDTH)
        layout = QVBoxLayout(info)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        cover = LazyThumbnail(COVER_SIZE, radius=10, background=theme.SURFACE)
        cover.set_source(thumbnail_url(data, imaging.thumb_px(COVER_SIZE)), thumbnails)
        layout.addWidget(cover, alignment=Qt.AlignHCenter)
        layout.addSpacing(10)

        title = QLabel(data.get("title", ""))
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignHCenter)
        title.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {theme.TEXT};")
        layout.addWidget(title)
        for row in byline:
            layout.addLayout(row)

        kind = " • ".join(p for p in (data.get("kind"), data.get("year")) if p)
        layout.addWidget(self._muted(kind, center=True))
        count = data.get("track_count") or len(data["tracks"])
        extras = t("album.count.song", count=count) if count == 1 else t("album.count.songs", count=count)
        if data.get("duration"):
            extras += f" • {data['duration']}"
        layout.addWidget(self._muted(extras, center=True, wrap=True))
        description = (data.get("description") or "").strip()
        if description:
            if len(description) > DESCRIPTION_CHARS:
                description = description[:DESCRIPTION_CHARS].rsplit(" ", 1)[0] + "…"
            layout.addWidget(self._muted(description, center=True, wrap=True))
        layout.addSpacing(6)

        buttons = QHBoxLayout()
        buttons.setAlignment(Qt.AlignHCenter)
        buttons.setSpacing(14)
        self.shuffle_button = _round_button("fa5s.random", 44, _round_qss(), t("album.shuffle"), theme.TEXT)
        self.shuffle_button.clicked.connect(self.shuffle_requested)
        self.play_button = _round_button("fa5s.play", 56, _play_qss(), t("album.play"), theme.BG)
        self.play_button.clicked.connect(self.play_requested)
        self.menu_button = ActionsButton(collection_actions(), style=_round_qss(), size=44,
                                         icon_color=theme.TEXT)
        self.menu_button.set_revealed(True)
        self.menu_button.action_chosen.connect(lambda key: self.collection_action_requested.emit(key, item))
        for widget in (self.shuffle_button, self.play_button, self.menu_button):
            buttons.addWidget(widget)
        layout.addLayout(buttons)
        return info

    @staticmethod
    def _muted(text, center=False, wrap=False):
        label = QLabel(text)
        label.setWordWrap(wrap)
        if center:
            label.setAlignment(Qt.AlignHCenter)
        label.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_SECONDARY};")
        return label
