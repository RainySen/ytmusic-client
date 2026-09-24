import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget,
)

from config import HOVER_PREFETCH_MS
from domain.models import artist_names, primary_artist, thumbnail_url
from ui.components.clickable import ClickableWidget
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.page_parts import pill_button
from ui.components.track_actions import TrackActionsButton

_TYPE_LABELS = {
    "song": "Canción", "album": "Álbum", "playlist": "Playlist", "video": "Video",
    "artist": "Artista", "profile": "Perfil", "podcast": "Podcast", "episode": "Episodio",
    "single": "Sencillo", "ep": "EP",
}
_MAX_SONGS = 10


def _result_title(item):
    return item.get("title") or item.get("artist") or item.get("name") or primary_artist(item, default="")


class _ArtistHero(QFrame):
    opened = Signal(dict)
    shuffle_clicked = Signal(dict)
    mix_clicked = Signal(dict)

    def __init__(self, data, thumbnails, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("artist_hero")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QFrame#artist_hero { background: #1e1e1e; border-radius: 12px; }"
                           "QFrame#artist_hero:hover { background: #262626; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(20)

        image = LazyThumbnail(96, circle=True, icon="fa5s.user", background="#333")
        image.set_source(thumbnail_url(data, 192), thumbnails)
        layout.addWidget(image)

        info = QVBoxLayout()
        info.setSpacing(4)
        info.setContentsMargins(0, 0, 0, 0)

        name = QLabel(_result_title(data) or "Artista")
        name.setStyleSheet("font-size: 22px; font-weight: 700; color: white; background: transparent;")
        info.addWidget(name)

        subscribers = data.get("subscribers", "")
        subtitle = QLabel(f"Artista  •  {subscribers} suscriptores" if subscribers else "Artista")
        subtitle.setStyleSheet("font-size: 12px; color: #aaa; background: transparent;")
        info.addWidget(subtitle)
        info.addSpacing(10)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.shuffle_button = pill_button("Aleatorio", "primary", "fa5s.random", height=36)
        self.shuffle_button.clicked.connect(lambda: self.shuffle_clicked.emit(data))
        self.mix_button = pill_button("Mix", "tonal", "fa5s.broadcast-tower", height=36)
        self.mix_button.clicked.connect(lambda: self.mix_clicked.emit(data))
        row.addWidget(self.shuffle_button)
        row.addWidget(self.mix_button)
        row.addStretch()
        info.addLayout(row)
        layout.addLayout(info, stretch=1)

        chevron = QLabel()
        chevron.setPixmap(qta.icon("fa5s.chevron-right", color="#aaa").pixmap(14, 14))
        chevron.setStyleSheet("background: transparent;")
        layout.addWidget(chevron, alignment=Qt.AlignTop)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.opened.emit(self._data)
        super().mouseReleaseEvent(event)


class _ResultRow(ClickableWidget):
    chosen = Signal(dict)
    add_next = Signal(dict)
    add_queue = Signal(dict)
    add_playlist = Signal(dict)
    hovered = Signal(dict)

    def __init__(self, item, thumbnails, parent=None):
        super().__init__(parent, dwell_ms=HOVER_PREFETCH_MS if item.get("videoId") else 0)
        self._item = item
        self.setMinimumHeight(60)
        kind = item.get("resultType", item.get("type", ""))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(14)

        is_artist = kind == "artist"
        thumb = LazyThumbnail(48, radius=4, circle=is_artist, icon="fa5s.user" if is_artist else "fa5s.music")
        thumb.set_source(thumbnail_url(item, 96), thumbnails)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(3)
        title = QLabel(_result_title(item))
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e8e8e8;")
        info.addWidget(title)

        parts = []
        if kind:
            parts.append(_TYPE_LABELS.get(kind, kind.title()))
        by = item.get("subscribers", "") if is_artist else (artist_names(item, limit=2) or item.get("author", ""))
        if by:
            parts.append(by)
        if item.get("duration"):
            parts.append(item["duration"])
        if parts:
            subtitle = QLabel("  •  ".join(parts))
            subtitle.setStyleSheet("font-size: 11px; color: #888;")
            info.addWidget(subtitle)
        layout.addLayout(info, stretch=1)

        self._actions = TrackActionsButton()
        self._actions.setVisible(bool(item.get("videoId")))
        self._actions.add_next.connect(lambda: self.add_next.emit(self._item))
        self._actions.add_queue.connect(lambda: self.add_queue.emit(self._item))
        self._actions.add_playlist.connect(lambda: self.add_playlist.emit(self._item))
        layout.addWidget(self._actions)

        self.activated.connect(lambda: self.chosen.emit(self._item))
        self.hover_changed.connect(self._actions.set_revealed)
        self.context_requested.connect(self._actions.show_menu)
        self.dwelled.connect(lambda: self.hovered.emit(self._item))


# resultados busqueda
class SearchPanel(QWidget):
    item_clicked = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    item_hovered = Signal(dict)
    artist_shuffle_requested = Signal(dict)
    artist_mix_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll = scroll

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(48, 24, 48, 24)
        self._layout.setSpacing(0)
        self._layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

    def _clear(self):
        while self._layout.count() > 1:
            widget = self._layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def show_message(self, text):
        self._clear()
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px; padding: 60px;")
        self._layout.insertWidget(0, label)

    def show_results(self, grouped, thumbnails):
        self._clear()
        top = grouped.get("top_result")
        songs = list(grouped.get("songs", []))
        more = list(grouped.get("more", []))

        hero = None
        if top and top.get("resultType") == "artist":
            hero = top
        elif top:
            (songs if top.get("resultType") == "song" else more).insert(0, top)

        widgets = []
        if hero:
            card = _ArtistHero(hero, thumbnails)
            card.opened.connect(self.item_clicked)
            card.shuffle_clicked.connect(self.artist_shuffle_requested)
            card.mix_clicked.connect(self.artist_mix_requested)
            widgets.append(card)
            widgets.append(self._spacer(20))
        if songs:
            widgets.append(self._header("Canciones"))
            widgets.extend(self._row(s, thumbnails) for s in songs[:_MAX_SONGS])
            widgets.append(self._spacer(24))
        if more:
            widgets.append(self._header("Más resultados"))
            widgets.extend(self._row(m, thumbnails) for m in more)
        if not widgets:
            self.show_message("Sin resultados.")
            return

        for position, widget in enumerate(widgets):
            self._layout.insertWidget(position, widget)
        self._scroll.verticalScrollBar().setValue(0)

    @staticmethod
    def _header(text):
        label = QLabel(text)
        label.setStyleSheet("font-size: 18px; font-weight: 700; color: white; padding: 12px 0 8px 0;")
        return label

    @staticmethod
    def _spacer(height):
        spacer = QWidget()
        spacer.setFixedHeight(height)
        return spacer

    def _row(self, item, thumbnails):
        row = _ResultRow(item, thumbnails)
        row.chosen.connect(self.item_clicked)
        row.add_next.connect(self.add_next_clicked)
        row.add_queue.connect(self.add_queue_clicked)
        row.add_playlist.connect(self.add_playlist_clicked)
        row.hovered.connect(self.item_hovered)
        return row
