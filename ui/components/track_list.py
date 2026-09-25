from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from core.config import HOVER_PREFETCH_MS
from domain.models import artist_names, thumbnail_url
from ui import theme
from ui.components.clickable import ClickableWidget
from ui.components.elided_label import ElidedLabel
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.track_actions import TrackActionsButton

FIRST_BATCH = 30
NEXT_BATCH = 15
MAX_ROWS = 300


class TrackRow(ClickableWidget):
    chosen = Signal(dict)
    add_next = Signal(dict)
    add_queue = Signal(dict)
    add_playlist = Signal(dict)
    hovered = Signal(dict)

    def __init__(self, track, thumbnails, *, number=None, show_cover=True, show_artist=True, show_album=True,
                 parent=None):
        super().__init__(parent, dwell_ms=HOVER_PREFETCH_MS)
        self.track = track
        self.setFixedHeight(56)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(14)

        if number is not None:
            label = QLabel(str(number))
            label.setFixedWidth(28)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setStyleSheet(f"font-size: 14px; color: {theme.TEXT_SECONDARY};")
            row.addWidget(label)
        if show_cover:
            thumb = LazyThumbnail(44, radius=4, background="#1e1e1e")
            thumb.set_source(thumbnail_url(track, 88), thumbnails)
            row.addWidget(thumb)

        row.addWidget(self._cell(track.get("title", ""), f"font-size: 14px; font-weight: 600; color: {theme.TEXT};"),
                      stretch=5)
        muted = f"font-size: 13px; color: {theme.TEXT_SECONDARY};"
        if show_artist:
            row.addWidget(self._cell(artist_names(track), muted), stretch=3)
        if track.get("views"):
            plays = self._cell(track["views"], muted, align=Qt.AlignRight)
            plays.setFixedWidth(170)
            row.addWidget(plays)
        if show_album:
            row.addWidget(self._cell(track.get("album", ""), muted), stretch=3)
        duration = QLabel(track.get("duration", ""))
        duration.setFixedWidth(46)
        duration.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        duration.setStyleSheet(muted)
        row.addWidget(duration)

        actions = TrackActionsButton()
        actions.add_next.connect(lambda: self.add_next.emit(self.track))
        actions.add_queue.connect(lambda: self.add_queue.emit(self.track))
        actions.add_playlist.connect(lambda: self.add_playlist.emit(self.track))
        row.addWidget(actions)

        self.activated.connect(lambda: self.chosen.emit(self.track))
        self.hover_changed.connect(actions.set_revealed)
        self.context_requested.connect(actions.show_menu)
        self.dwelled.connect(lambda: self.hovered.emit(self.track))

    @staticmethod
    def _cell(text, style, align=Qt.AlignLeft):
        label = ElidedLabel(text)
        label.setAlignment(align)
        label.setStyleSheet(style)
        label.setToolTip(text)
        return label


# lista canciones lotes
class TrackList(QWidget):
    track_chosen = Signal(int, dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    track_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._generation = 0
        self._pending = []
        self._options = {}
        self._thumbnails = None
        self._built = 0

    @property
    def row_count(self):
        return self._built

    def set_tracks(self, tracks, thumbnails, **row_options):
        self._clear()
        self._generation += 1
        self._thumbnails = thumbnails
        self._options = dict(row_options)
        self._pending = list(enumerate(tracks[:MAX_ROWS]))
        self._build_batch(FIRST_BATCH)
        if self._pending:
            QTimer.singleShot(0, lambda g=self._generation: self._continue(g))

    def _clear(self):
        self._pending = []
        self._built = 0
        while self._layout.count():
            widget = self._layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _continue(self, generation):
        if generation != self._generation or not self._pending:
            return
        self._build_batch(NEXT_BATCH)
        if self._pending:
            QTimer.singleShot(15, lambda: self._continue(generation))

    def _build_batch(self, count):
        options = dict(self._options)
        numbered = options.pop("numbered", False)
        batch, self._pending = self._pending[:count], self._pending[count:]
        for position, track in batch:
            row = TrackRow(track, self._thumbnails, number=position + 1 if numbered else None, **options)
            row.chosen.connect(lambda t, p=position: self.track_chosen.emit(p, t))
            row.add_next.connect(self.add_next_clicked)
            row.add_queue.connect(self.add_queue_clicked)
            row.add_playlist.connect(self.add_playlist_clicked)
            row.hovered.connect(self.track_hovered)
            self._layout.addWidget(row)
            row.show()
            self._built += 1
