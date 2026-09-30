from collections import OrderedDict

import qtawesome as qta
from PySide6.QtCore import QAbstractListModel, QModelIndex, QPoint, QRect, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractItemView, QLabel, QListView, QMenu, QStyledItemDelegate, QVBoxLayout, QWidget

from core.config import HOVER_PREFETCH_MS
from domain.models import artist_names, thumbnail_url
from ui import imaging, theme
from ui.components.track_actions import MENU_QSS, song_entries, song_hub
from ui.imaging import round_pixmap, scale_cover

ROW_HEIGHT = 56
COVER = 44
COVER_CACHE = 120
MARGIN = 8
SPACING = 14
_TRACK = Qt.UserRole


class _TrackModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracks: list[dict] = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.tracks)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        track = self.tracks[index.row()]
        if role == _TRACK:
            return track
        if role == Qt.ToolTipRole:
            return " — ".join(p for p in (track.get("title", ""), artist_names(track), track.get("album", "")) if p)
        return None

    def reset(self, tracks):
        self.beginResetModel()
        self.tracks = list(tracks)
        self.endResetModel()

    def extend(self, tracks):
        if not tracks:
            return
        start = len(self.tracks)
        self.beginInsertRows(QModelIndex(), start, start + len(tracks) - 1)
        self.tracks.extend(tracks)
        self.endInsertRows()


# same geometry for painting and hit testing
def _cells(rect: QRect, track: dict, options: dict) -> dict:
    fixed = []
    if options.get("numbered"):
        fixed.append(("number", 28, 0))
    if options.get("show_cover", True):
        fixed.append(("cover", COVER, 0))
    fixed.append(("title", 0, 5))
    if options.get("show_artist", True):
        fixed.append(("artist", 0, 3))
    if track.get("views"):
        fixed.append(("views", 170, 0))
    if options.get("show_album", True):
        fixed.append(("album", 0, 3))
    fixed.append(("duration", 46, 0))
    if track.get("likeStatus") == "LIKE":
        fixed.append(("heart", 20, 0))
    fixed.append(("actions", 28, 0))
    width = rect.width() - 2 * MARGIN - SPACING * (len(fixed) - 1)
    stretch = sum(s for _k, _w, s in fixed)
    free = max(0, width - sum(w for _k, w, _s in fixed))
    cells, x = {}, rect.left() + MARGIN
    for key, size, weight in fixed:
        size = size or free * weight // stretch
        cells[key] = QRect(x, rect.top(), size, rect.height())
        x += size + SPACING
    return cells


class _TrackDelegate(QStyledItemDelegate):
    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner
        self._title_font = QFont(owner.font())
        self._title_font.setPixelSize(14)
        self._title_font.setWeight(QFont.DemiBold)
        self._muted_font = QFont(owner.font())
        self._muted_font.setPixelSize(13)
        self._number_font = QFont(owner.font())
        self._number_font.setPixelSize(14)
        self._placeholder = qta.icon("fa5s.music", color="#555").pixmap(22, 22)
        self._dots = qta.icon("fa5s.ellipsis-v", color="#ccc").pixmap(16, 16)
        self._heart = qta.icon("fa5s.heart", color="#ff3b5c").pixmap(13, 13)
        self._text = QColor(theme.TEXT)
        self._muted = QColor(theme.TEXT_SECONDARY)

    def sizeHint(self, option, index):
        return QSize(0, ROW_HEIGHT)

    def paint(self, painter, option, index):
        owner = self._owner
        track = index.data(_TRACK)
        row = index.row()
        rect = QRect(0, option.rect.top(), owner.view.viewport().width(), ROW_HEIGHT)
        hovered = owner.view.hovered_row == row
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        if hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 15))
            painter.drawRoundedRect(rect.adjusted(0, 0, 0, -1), 6, 6)
        cells = _cells(rect, track, owner.options)
        middle = Qt.AlignVCenter
        if "number" in cells:
            self._label(painter, cells["number"], str(row + 1), self._number_font, self._muted, Qt.AlignRight | middle)
        if "cover" in cells:
            self._cover(painter, cells["cover"], owner.cover_for(track))
        self._label(painter, cells["title"], track.get("title", ""), self._title_font, self._text, middle)
        for key, text, align in (("artist", artist_names(track), middle),
                                 ("views", track.get("views", ""), Qt.AlignRight | middle),
                                 ("album", track.get("album", ""), middle),
                                 ("duration", track.get("duration", ""), Qt.AlignRight | middle)):
            if key in cells:
                self._label(painter, cells[key], text, self._muted_font, self._muted, align)
        if "heart" in cells:
            self._centered(painter, cells["heart"], self._heart)
        if hovered:
            actions = cells["actions"]
            if owner.view.over_actions:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(255, 255, 255, 38))
                center = actions.center()
                painter.drawEllipse(center, 14, 14)
            self._centered(painter, actions, self._dots)
        painter.restore()

    @staticmethod
    def _label(painter, rect, text, font, color, align):
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(rect, align, painter.fontMetrics().elidedText(text or "", Qt.ElideRight, rect.width()))

    @staticmethod
    def _centered(painter, rect, pixmap):
        size = pixmap.deviceIndependentSize().toSize()
        painter.drawPixmap(rect.center().x() - size.width() // 2 + 1, rect.center().y() - size.height() // 2 + 1,
                           pixmap)

    def _cover(self, painter, cell, pixmap):
        box = QRect(cell.left(), cell.center().y() - COVER // 2 + 1, COVER, COVER)
        if pixmap is not None:
            painter.drawPixmap(box, pixmap)
            return
        path = QPainterPath()
        path.addRoundedRect(box, 4, 4)
        painter.fillPath(path, QColor("#1e1e1e"))
        self._centered(painter, box, self._placeholder)


class _TrackView(QListView):
    def __init__(self, owner):
        super().__init__(owner)
        self._owner = owner
        self.hovered_row = -1
        self.over_actions = False
        self._pressed_row = -1
        self._dwell = QTimer(self)
        self._dwell.setSingleShot(True)
        self._dwell.setInterval(HOVER_PREFETCH_MS)
        self._dwell.timeout.connect(owner._dwelled)
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setResizeMode(QListView.Adjust)
        self.setFrameShape(QListView.NoFrame)
        self.setStyleSheet("QListView { background: transparent; border: none; }")
        self.viewport().setAutoFillBackground(False)
        self.viewport().setCursor(Qt.PointingHandCursor)

    def _row_at(self, pos) -> int:
        return self.indexAt(pos).row()

    def _update_row(self, row):
        if row >= 0:
            self.viewport().update(QRect(0, row * ROW_HEIGHT, self.viewport().width(), ROW_HEIGHT))

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        row = self._row_at(pos)
        over = row >= 0 and self._owner.actions_rect(row).contains(pos)
        if row != self.hovered_row:
            self._update_row(self.hovered_row)
            self.hovered_row = row
            self._update_row(row)
            if row >= 0:
                self._dwell.start()
            else:
                self._dwell.stop()
        if over != self.over_actions:
            self.over_actions = over
            self._update_row(row)

    def leaveEvent(self, event):
        self._dwell.stop()
        self._update_row(self.hovered_row)
        self.hovered_row = -1
        self.over_actions = False
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dwell.stop()
            self._pressed_row = self._row_at(event.position().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event):
        pos = event.position().toPoint()
        pressed, self._pressed_row = self._pressed_row, -1
        row = self._row_at(pos)
        if event.button() != Qt.LeftButton or row < 0 or row != pressed:
            return
        actions = self._owner.actions_rect(row)
        if actions.contains(pos):
            self._owner.open_menu(row, self.viewport().mapToGlobal(actions.bottomRight()), align_right=True)
        else:
            self._owner.choose(row)

    def mouseDoubleClickEvent(self, event):
        event.accept()

    def contextMenuEvent(self, event):
        row = self._row_at(event.pos())
        if row >= 0:
            self._owner.open_menu(row, event.globalPos())

    # outer page scroll handles the wheel
    def wheelEvent(self, event):
        event.ignore()


# virtualized: only visible rows painted, covers loaded on paint
class TrackList(QWidget):
    track_chosen = Signal(int, dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    track_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.options: dict = {}
        self._thumbnails = None
        self._generation = 0
        self._covers: "OrderedDict[str, object]" = OrderedDict()
        self._requested: set[str] = set()
        self._model = _TrackModel(self)
        self.view = _TrackView(self)
        self.view.setModel(self._model)
        self.view.setItemDelegate(_TrackDelegate(self))
        self.view.setFixedHeight(0)
        layout.addWidget(self.view)
        self._loading = QLabel("Cargando más…")
        self._loading.setAlignment(Qt.AlignCenter)
        self._loading.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; padding: 12px;")
        self._loading.hide()
        layout.addWidget(self._loading)

    @property
    def row_count(self):
        return self._model.rowCount()

    @property
    def building(self):
        return False

    @property
    def tracks(self) -> list[dict]:
        return self._model.tracks

    def set_tracks(self, tracks, thumbnails, **row_options):
        self._generation += 1
        self._covers.clear()
        self._requested.clear()
        self._thumbnails = thumbnails
        self.options = dict(row_options)
        self._loading.hide()
        self._model.reset(tracks)
        self._fit()

    def append_tracks(self, tracks, thumbnails):
        self._thumbnails = thumbnails
        self._loading.hide()
        self._model.extend(tracks)
        self._fit()

    def show_loading_more(self):
        self._loading.show()

    def hide_loading_more(self):
        self._loading.hide()

    def _fit(self):
        self.view.setFixedHeight(self.row_count * ROW_HEIGHT)

    def actions_rect(self, row) -> QRect:
        rect = QRect(0, row * ROW_HEIGHT, self.view.viewport().width(), ROW_HEIGHT)
        return _cells(rect, self._model.tracks[row], self.options)["actions"]

    def choose(self, row):
        self.track_chosen.emit(row, self._model.tracks[row])

    def _dwelled(self):
        row = self.view.hovered_row
        if 0 <= row < self.row_count:
            self.track_hovered.emit(self._model.tracks[row])

    def open_menu(self, row, global_pos: QPoint, align_right: bool = False):
        track = self._model.tracks[row]
        menu = QMenu(self.window())
        menu.setStyleSheet(MENU_QSS)
        signals = {"next": self.add_next_clicked, "queue": self.add_queue_clicked,
                   "playlist": self.add_playlist_clicked}
        actions = {menu.addAction(qta.icon(icon, color="#e0e0e0"), label): key
                   for key, label, icon in song_entries(track)}
        if align_right:
            global_pos = QPoint(global_pos.x() - menu.sizeHint().width(), global_pos.y())
        try:
            chosen = self._show_menu(menu, global_pos)
        finally:
            menu.deleteLater()
        if chosen in actions and not song_hub.relay(actions[chosen], track):
            signals[actions[chosen]].emit(track)

    def _show_menu(self, menu, position):
        return menu.exec(position)

    def cover_for(self, track):
        url = thumbnail_url(track, imaging.thumb_px(COVER))
        if not url:
            return None
        cached = self._covers.get(url)
        if cached is not None:
            self._covers.move_to_end(url)
            return cached
        if self._thumbnails is not None and url not in self._requested:
            self._requested.add(url)
            generation = self._generation
            self._thumbnails.request(url, lambda pixmap, u=url: self._on_cover(generation, u, pixmap))
        return self._covers.get(url)

    def _on_cover(self, generation, url, pixmap):
        try:
            if generation != self._generation or pixmap is None or pixmap.isNull():
                return
            self._covers[url] = round_pixmap(scale_cover(pixmap, COVER, self.devicePixelRatioF()), 4)
            while len(self._covers) > COVER_CACHE:
                evicted, _ = self._covers.popitem(last=False)
                self._requested.discard(evicted)
            self.view.viewport().update()
        except RuntimeError:
            pass
