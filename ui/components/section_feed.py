import qtawesome as qta
from PySide6.QtCore import Property, QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from config import HOVER_PREFETCH_MS
from domain.models import artist_names, thumbnail_url
from ui.components.clickable import ClickableWidget
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.track_actions import CollectionActionsButton, TrackActionsButton

CARD_SIZE = 210
LOOKAHEAD_PX = 600
MOOD_COLUMNS = 4

_ARROW_STYLE = """
    QPushButton { background: rgba(255,255,255,0.10); border: none; border-radius: 16px; }
    QPushButton:hover   { background: rgba(255,255,255,0.20); }
    QPushButton:pressed { background: rgba(255,255,255,0.28); }
    QPushButton:disabled { background: rgba(255,255,255,0.04); }
"""
_PLAY_ALL_STYLE = """
    QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.25);
                  border-radius: 16px; padding: 5px 14px; color: #e0e0e0; font-size: 12px; }
    QPushButton:hover { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.5); color: white; }
"""


def _arrow_button(icon_name: str) -> QPushButton:
    button = QPushButton()
    button.setIcon(qta.icon(icon_name, color="white"))
    button.setFixedSize(32, 32)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(_ARROW_STYLE)
    return button


def _clear_layout(layout) -> None:
    while layout.count():
        taken = layout.takeAt(0)
        widget = taken.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def is_collection_card(item: dict) -> bool:
    return (item.get("type") in ("playlist", "album") and not str(item.get("browseId", "")).startswith("UC")
            and not item.get("videoId"))


class _CardOverlay(QWidget):
    play_clicked = Signal()
    action_chosen = Signal(str)

    def __init__(self, cover, size):
        super().__init__(cover)
        self.setGeometry(0, 0, size, size)
        self.play_button = QPushButton(self)
        self.play_button.setIcon(qta.icon("fa5s.play", color="#0f0f0f"))
        self.play_button.setFixedSize(48, 48)
        self.play_button.move(size - 48 - 10, size - 48 - 10)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setToolTip("Reproducir")
        self.play_button.setStyleSheet("QPushButton { background: white; border: none; border-radius: 24px; }"
                                       "QPushButton:hover { background: #e6e6e6; }")
        self.play_button.clicked.connect(self.play_clicked)
        self.menu_button = CollectionActionsButton(self)
        self.menu_button.move(size - 32 - 8, 8)
        self.menu_button.action_chosen.connect(self.action_chosen)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 70))
        painter.end()


# tarjeta overlay hover
class HomeCard(ClickableWidget):
    chosen = Signal(dict)
    action_requested = Signal(str, dict)

    def __init__(self, item, thumbnails, parent=None, size=CARD_SIZE):
        super().__init__(parent, radius=10)
        self.item = item
        self.setFixedWidth(size + 12)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 8)
        layout.setSpacing(6)

        kind = item.get("type", "")
        self.thumb = LazyThumbnail(size, radius=0 if kind == "playlist" else 6, circle=kind == "artist",
                                   icon="fa5s.user" if kind == "artist" else "fa5s.music")
        self.thumb.set_source(thumbnail_url(item, size * 2), thumbnails)
        layout.addWidget(self.thumb)

        title = QLabel()
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #fff;")
        title.setMaximumWidth(size)
        title.setText(title.fontMetrics().elidedText(item.get("title", ""), Qt.ElideRight, size))
        layout.addWidget(title)

        subtitle = (item.get("subtitle") or artist_names(item, limit=2) or item.get("subscribers", "")
                    or {"playlist": "Playlist", "album": "Álbum", "artist": "Artista"}.get(kind, ""))
        if subtitle:
            sub = QLabel(sub_text := subtitle)
            sub.setStyleSheet("font-size: 11px; color: #aaa;")
            sub.setText(sub.fontMetrics().elidedText(sub_text, Qt.ElideRight, size))
            sub.setMaximumWidth(size)
            layout.addWidget(sub)

        self.activated.connect(lambda: self.chosen.emit(self.item))

        self._overlay = None
        if is_collection_card(item):
            self._overlay = _CardOverlay(self.thumb, size)
            self._overlay.play_clicked.connect(lambda: self.action_requested.emit("play", self.item))
            self._overlay.action_chosen.connect(lambda key: self.action_requested.emit(key, self.item))
            self._overlay.menu_button.menu_closed.connect(self._sync_overlay)
            self.hover_changed.connect(self._sync_overlay)
            self.context_requested.connect(self._overlay.menu_button.show_menu)

    def _sync_overlay(self, *_):
        if self._overlay is not None:
            self._overlay.setVisible(self.hovered or self._overlay.menu_button.menu_is_open)


class CompactSongItem(ClickableWidget):
    chosen = Signal(dict)
    add_next = Signal(dict)
    add_queue = Signal(dict)
    add_playlist = Signal(dict)
    hovered = Signal(dict)

    def __init__(self, item, thumbnails, parent=None):
        super().__init__(parent, dwell_ms=HOVER_PREFETCH_MS)
        self.item = item
        self.setMinimumWidth(200)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        thumb = LazyThumbnail(44, radius=4)
        thumb.set_source(thumbnail_url(item, 88), thumbnails)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(3)
        title = QLabel(item.get("title", ""))
        title.setStyleSheet("font-size: 13px; font-weight: 600; color: #e0e0e0;")
        sub = QLabel(artist_names(item))
        sub.setStyleSheet("font-size: 11px; color: #888;")
        info.addWidget(title)
        info.addWidget(sub)
        layout.addLayout(info, stretch=1)

        self._actions = TrackActionsButton()
        self._actions.add_next.connect(lambda: self.add_next.emit(self.item))
        self._actions.add_queue.connect(lambda: self.add_queue.emit(self.item))
        self._actions.add_playlist.connect(lambda: self.add_playlist.emit(self.item))
        layout.addWidget(self._actions)

        self.activated.connect(lambda: self.chosen.emit(self.item))
        self.hover_changed.connect(self._actions.set_revealed)
        self.context_requested.connect(self._actions.show_menu)
        self.dwelled.connect(lambda: self.hovered.emit(self.item))


class _SectionHeader(QHBoxLayout):
    def __init__(self, title, on_prev, on_next, extra=None, title_px=20):
        super().__init__()
        label = QLabel(title)
        label.setStyleSheet(f"font-size: {title_px}px; font-weight: 700; color: white;")
        label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.addWidget(label, stretch=1)
        if extra is not None:
            self.addWidget(extra)
            self.addSpacing(8)
        self.prev = _arrow_button("fa5s.chevron-left")
        self.next = _arrow_button("fa5s.chevron-right")
        self.prev.clicked.connect(on_prev)
        self.next.clicked.connect(on_next)
        self.addWidget(self.prev)
        self.addWidget(self.next)


class _Viewport(QWidget):
    SLIDE_MS = 380

    def __init__(self, parent=None):
        super().__init__(parent)
        self.track = QWidget(self)
        self._offset = 0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(self.SLIDE_MS)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def _get_offset(self):
        return self._offset

    def _set_offset(self, value):
        self._offset = int(value)
        self.track.move(-self._offset, 0)

    offset = Property(int, _get_offset, _set_offset)

    def slide_to(self, x, animate=True):
        self._animation.stop()
        if animate and self.isVisible() and x != self._offset:
            self._animation.setStartValue(self._offset)
            self._animation.setEndValue(int(x))
            self._animation.start()
        else:
            self._set_offset(x)


# carrusel tarjetas
class CardsSection(QWidget):
    item_clicked = Signal(dict)
    collection_action_requested = Signal(str, dict)
    SPACING = 4
    SLOT = CARD_SIZE + 12 + SPACING
    INITIAL_CARDS = 6

    def __init__(self, title, items, thumbnails, parent=None, *, card_size=CARD_SIZE, title_px=20):
        super().__init__(parent)
        self._card_size = card_size
        self.SLOT = card_size + 12 + self.SPACING
        self._items = items
        self._thumbnails = thumbnails
        self._built = 0
        self._target = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        self._header = _SectionHeader(title, self._go_prev, self._go_next, title_px=title_px)
        root.addLayout(self._header)

        self._view = _Viewport()
        self._row = QHBoxLayout(self._view.track)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(self.SPACING)
        self._row.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        root.addWidget(self._view)
        self._ensure_built(self.INITIAL_CARDS * self.SLOT)
        self._update_arrows()

    def _content_width(self):
        return max(0, len(self._items) * self.SLOT - self.SPACING)

    def _max_offset(self):
        return max(0, self._content_width() - self._view.width())

    def _page_step(self):
        return max(1, self._view.width() // self.SLOT) * self.SLOT

    def _ensure_built(self, limit_px):
        grew = False
        while self._built < len(self._items) and self._built * self.SLOT < limit_px:
            card = HomeCard(self._items[self._built], self._thumbnails, size=self._card_size)
            card.chosen.connect(self.item_clicked)
            card.action_requested.connect(self.collection_action_requested)
            self._row.addWidget(card)
            card.show()
            self._built += 1
            grew = True
        if grew:
            height = max(self._row.itemAt(i).widget().sizeHint().height() for i in range(self._row.count()))
            self._view.setFixedHeight(height)
            self._view.track.resize(max(0, self._built * self.SLOT - self.SPACING), height)

    def _update_arrows(self):
        self._header.prev.setEnabled(self._target > 0)
        self._header.next.setEnabled(self._target < self._max_offset())

    def _slide(self, target):
        self._target = max(0, min(self._max_offset(), target))
        self._ensure_built(self._target + self._view.width() + self.SLOT)
        self._view.slide_to(self._target)
        self._update_arrows()

    def _go_prev(self):
        self._slide(self._target - self._page_step())

    def _go_next(self):
        self._slide(self._target + self._page_step())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._target = min(self._target, self._max_offset())
        self._ensure_built(self._target + self._view.width() + self.SLOT)
        self._view.slide_to(self._target, animate=False)
        self._update_arrows()


# grilla canciones
class CompactSection(QWidget):
    item_clicked = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    play_all_requested = Signal(list)
    item_hovered = Signal(dict)

    GAP = 12

    def __init__(self, title, items, thumbnails, parent=None, *, columns=3, rows=4,
                 play_all=True, peek=0, title_px=20):
        super().__init__(parent)
        self._items = items
        self._thumbnails = thumbnails
        self._columns = columns
        self._page_size = columns * rows
        self._peek = peek
        self._pages = []
        self._page = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        extra = None
        if play_all:
            extra = QPushButton("Reproducir todo")
            extra.setCursor(Qt.PointingHandCursor)
            extra.setStyleSheet(_PLAY_ALL_STYLE)
            extra.clicked.connect(lambda: self.play_all_requested.emit(list(self._items)))
        self._header = _SectionHeader(title, self._go_prev, self._go_next, extra=extra, title_px=title_px)
        root.addLayout(self._header)

        self._view = _Viewport()
        root.addWidget(self._view)
        self._build_page(0)
        self._view.setFixedHeight(self._pages[0].sizeHint().height())
        self._relayout(animate=False)

    @property
    def page_count(self):
        return max(1, -(-len(self._items) // self._page_size))

    def _build_page(self, index):
        while len(self._pages) <= index:
            n = len(self._pages)
            page = QWidget(self._view.track)
            columns = QHBoxLayout(page)
            columns.setContentsMargins(0, 0, 0, 0)
            columns.setSpacing(4)
            column_layouts = []
            for _ in range(self._columns):
                column = QVBoxLayout()
                column.setContentsMargins(0, 0, 0, 0)
                column.setSpacing(2)
                columns.addLayout(column, stretch=1)
                column_layouts.append(column)
            start = n * self._page_size
            for position, item in enumerate(self._items[start:start + self._page_size]):
                row = CompactSongItem(item, self._thumbnails)
                row.chosen.connect(self.item_clicked)
                row.add_next.connect(self.add_next_clicked)
                row.add_queue.connect(self.add_queue_clicked)
                row.add_playlist.connect(self.add_playlist_clicked)
                row.hovered.connect(self.item_hovered)
                column_layouts[position % self._columns].addWidget(row)
            for column in column_layouts:
                column.addStretch()
            page.show()
            self._pages.append(page)

    def _relayout(self, animate):
        page_width = max(1, self._view.width() - self._peek)
        stride = page_width + (self.GAP if self._peek else 0)
        height = self._view.height()
        for index, page in enumerate(self._pages):
            page.setGeometry(index * stride, 0, page_width, height)
        self._view.track.resize(len(self._pages) * stride, height)
        self._view.slide_to(self._page * stride, animate)
        self._header.prev.setEnabled(self._page > 0)
        self._header.next.setEnabled(self._page < self.page_count - 1)

    def _go_to(self, page):
        self._page = max(0, min(self.page_count - 1, page))
        self._build_page(self._page)
        self._relayout(animate=True)

    def _go_prev(self):
        self._go_to(self._page - 1)

    def _go_next(self):
        self._go_to(self._page + 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout(animate=False)


class MoodTile(ClickableWidget):
    chosen = Signal(dict)

    def __init__(self, item, parent=None):
        super().__init__(parent, radius=6, hover_alpha=25)
        self.item = item
        self.setFixedHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        label = QLabel(item.get("title", ""))
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f0f0f0;")
        layout.addWidget(label)
        self.setStyleSheet("MoodTile { background: #2a2a2a; border-left: 4px solid #ff4e45; border-radius: 6px; }")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.activated.connect(lambda: self.chosen.emit(self.item))


class MoodGridSection(QWidget):
    item_clicked = Signal(dict)

    def __init__(self, title, items, thumbnails, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        label = QLabel(title)
        label.setStyleSheet("font-size: 20px; font-weight: 700; color: white;")
        root.addWidget(label)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        for position, item in enumerate(items):
            tile = MoodTile(item)
            tile.chosen.connect(self.item_clicked)
            grid.addWidget(tile, position // MOOD_COLUMNS, position % MOOD_COLUMNS)
        for column in range(MOOD_COLUMNS):
            grid.setColumnStretch(column, 1)
        root.addLayout(grid)


# secciones lazy scroll
class SectionFeed(QWidget):
    item_clicked = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    collection_action_requested = Signal(str, dict)
    play_all_requested = Signal(list)
    item_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending = []
        self._built = []
        self._thumbnails = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.verticalScrollBar().valueChanged.connect(self._fill)

        self._content = QWidget()
        content = QVBoxLayout(self._content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        self._header_slot = QVBoxLayout()
        self._header_slot.setContentsMargins(0, 0, 0, 0)
        content.addLayout(self._header_slot)
        sections = QWidget()
        self._layout = QVBoxLayout(sections)
        self._layout.setContentsMargins(48, 24, 48, 24)
        self._layout.setSpacing(32)
        self._layout.addStretch()
        content.addWidget(sections, stretch=1)
        self._scroll.setWidget(self._content)
        outer.addWidget(self._scroll)

        self._message = QLabel()
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setStyleSheet("color: #888; font-size: 14px; padding: 60px;")
        self._message.hide()

    def set_loading(self):
        self.show_message("Cargando…")

    def show_message(self, text):
        self._clear()
        self._message.setText(text)
        self._layout.insertWidget(0, self._message)
        self._message.show()

    def _clear(self):
        self._pending = []
        self._built = []
        self._message.hide()
        self._layout.removeWidget(self._message)
        while self._layout.count() > 1:
            widget = self._layout.takeAt(0).widget()
            if widget is not None and widget is not self._message:
                widget.setParent(None)
                widget.deleteLater()

    def clear(self):
        self._clear()

    def set_sections(self, sections, thumbnails, reset_scroll=True, empty_message="No hay contenido para mostrar."):
        self._thumbnails = thumbnails
        scroll_value = self._scroll.verticalScrollBar().value()
        self._clear()
        self._pending = [(title, items) for title, items in sections if items]
        if not self._pending:
            if empty_message:
                self.show_message(empty_message)
            return
        self._fill()
        if not reset_scroll:
            QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(scroll_value))

    def set_header(self, widget):
        while self._header_slot.count():
            old = self._header_slot.takeAt(0).widget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
        if widget is not None:
            self._header_slot.addWidget(widget)
            widget.show()

    def scroll_to_top(self):
        self._scroll.verticalScrollBar().setValue(0)

    def reveal(self, index):
        while len(self._built) <= index and self._pending:
            self._build_next()
        if index < len(self._built):
            target = self._built[index]
            QTimer.singleShot(0, lambda: self._scroll.verticalScrollBar().setValue(
                max(0, target.mapTo(self._content, QPoint(0, 0)).y() - 8)))

    def _fill(self, *_):
        while self._pending and self._needs_more_content():
            self._build_next()

    def _build_next(self):
        title, items = self._pending.pop(0)
        section = self._build_section(title, items)
        self._built.append(section)
        self._layout.insertWidget(self._layout.count() - 1, section)
        section.show()
        self._layout.activate()

    def _needs_more_content(self):
        bar = self._scroll.verticalScrollBar()
        viewport_height = max(self._scroll.viewport().height(), 400)
        content_height = self._content.sizeHint().height()
        return content_height - (bar.value() + viewport_height) < LOOKAHEAD_PX

    def _build_section(self, title, items):
        kind = items[0].get("type")
        if kind == "mood":
            section = MoodGridSection(title, items, self._thumbnails)
        elif kind == "song":
            section = CompactSection(title, items, self._thumbnails)
            section.add_next_clicked.connect(self.add_next_clicked)
            section.add_queue_clicked.connect(self.add_queue_clicked)
            section.add_playlist_clicked.connect(self.add_playlist_clicked)
            section.play_all_requested.connect(self.play_all_requested)
            section.item_hovered.connect(self.item_hovered)
        else:
            section = CardsSection(title, items, self._thumbnails)
            section.collection_action_requested.connect(self.collection_action_requested)
        section.item_clicked.connect(self.item_clicked)
        return section

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._fill)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._fill)
