import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from domain.models import thumbnail_url
from ui import theme
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.page_parts import MessagePage, back_button
from ui.components.section_feed import CardsSection
from ui.components.track_actions import COLLECTION_ACTIONS, ActionsButton
from ui.components.track_list import TrackList

COVER_SIZE = 300
INFO_WIDTH = 340
DESCRIPTION_CHARS = 220

_PLAY_QSS = """
    QPushButton { background: white; border: none; border-radius: 28px; }
    QPushButton:hover { background: #e6e6e6; }
    QPushButton:pressed { background: #cccccc; }
"""
_ROUND_QSS = """
    QPushButton { background: rgba(255,255,255,0.12); border: none; border-radius: 22px; }
    QPushButton:hover { background: rgba(255,255,255,0.22); }
"""
_LINK_QSS = f"""
    QPushButton {{ background: transparent; border: none; color: {theme.TEXT}; font-size: 15px;
                   font-weight: 600; padding: 0; text-align: left; }}
    QPushButton:hover {{ text-decoration: underline; }}
"""


def _round_button(icon, size, style, tooltip):
    button = QPushButton()
    button.setIcon(qta.icon(icon, color=theme.BG if style is _PLAY_QSS else "white"))
    button.setFixedSize(size, size)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(style)
    button.setToolTip(tooltip)
    return button


# pagina album playlist
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

    def set_loading(self):
        self._scroll.setWidget(MessagePage("Cargando…", self.back_requested.emit))

    def show_message(self, text):
        self._scroll.setWidget(MessagePage(text, self.back_requested.emit))

    def show_album(self, album, thumbnails):
        item = {"type": "album", "browseId": album["id"], "title": album["title"]}
        album_artists = {a.get("name") for a in album.get("artists") or []}
        others = any(a.get("name") not in album_artists for t in album["tracks"] for a in t.get("artists") or [])
        self._show(album, thumbnails, item, self._artist_links(album.get("artists") or []),
                   dict(numbered=True, show_cover=False, show_artist=others, show_album=False))

    def show_playlist(self, playlist, thumbnails):
        item = {"type": "playlist", "playlistId": playlist["id"], "title": playlist["title"]}
        owner = []
        if playlist.get("author"):
            owner = self._artist_links([{"name": playlist["author"], "id": playlist.get("author_id", "")}])
        self._show(playlist, thumbnails, item, owner,
                   dict(numbered=False, show_cover=True, show_artist=True, show_album=True))

    def _show(self, data, thumbnails, item, byline, row_options):
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
            more = CardsSection("Lanzamientos para ti", data["more"], thumbnails, title_px=22)
            more.item_clicked.connect(self.item_clicked)
            more.collection_action_requested.connect(self.collection_action_requested)
            column.addWidget(more)
        column.addStretch()
        self._scroll.setWidget(page)

    def _artist_links(self, artists):
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignHCenter)
        for position, artist in enumerate(artists[:3]):
            link = QPushButton(artist.get("name", ""))
            link.setStyleSheet(_LINK_QSS)
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

        cover = LazyThumbnail(COVER_SIZE, radius=10, background="#1e1e1e")
        cover.set_source(thumbnail_url(data, COVER_SIZE * 2), thumbnails)
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
        extras = f"{count} {'canción' if count == 1 else 'canciones'}"
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
        self.shuffle_button = _round_button("fa5s.random", 44, _ROUND_QSS, "Reproducir en orden aleatorio")
        self.shuffle_button.clicked.connect(self.shuffle_requested)
        self.play_button = _round_button("fa5s.play", 56, _PLAY_QSS, "Reproducir")
        self.play_button.clicked.connect(self.play_requested)
        self.menu_button = ActionsButton(COLLECTION_ACTIONS, style=_ROUND_QSS, size=44, icon_color="white")
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
