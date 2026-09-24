from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from domain.models import LOCAL_SOURCES, thumbnail_url
from ui import theme
from ui.components import dialogs
from ui.components.clickable import ClickableWidget
from ui.components.lazy_thumbnail import LazyThumbnail

DIALOG_SIZE = (480, 600)

_SECTION_QSS = "font-size: 15px; font-weight: 700; color: white;"


def _count_text(playlist: dict, singular: str, plural: str) -> str:
    raw = playlist.get("track_count")
    try:
        count = int(str(raw).split()[0].replace(",", "").replace(".", ""))
    except (ValueError, IndexError):
        return ""
    return f"{count} {singular if count == 1 else plural}" if count else ""


class _RecentTile(ClickableWidget):
    WIDTH = 96

    def __init__(self, playlist, thumbnails, parent=None):
        super().__init__(parent, radius=8)
        self.playlist = playlist
        self.setFixedWidth(self.WIDTH + 8)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 6)
        layout.setSpacing(4)
        thumb = LazyThumbnail(self.WIDTH, radius=4, icon="fa5s.list", background="#1e1e1e")
        thumb.set_source(thumbnail_url(playlist, 2 * self.WIDTH), thumbnails)
        layout.addWidget(thumb)
        for text, style in ((playlist.get("title", ""), "font-size: 12px; font-weight: 600; color: #e8e8e8;"),
                            (_count_text(playlist, "canción", "canciones"), "font-size: 11px; color: #999;")):
            label = QLabel()
            label.setStyleSheet(style)
            label.setText(label.fontMetrics().elidedText(text, Qt.ElideRight, self.WIDTH))
            label.setToolTip(text)
            layout.addWidget(label)


class _PlaylistRow(ClickableWidget):
    def __init__(self, playlist, thumbnails, parent=None):
        super().__init__(parent, radius=8)
        self.playlist = playlist
        self.setFixedHeight(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(14)
        thumb = LazyThumbnail(52, radius=4, icon="fa5s.list", background="#1e1e1e")
        thumb.set_source(thumbnail_url(playlist, 104), thumbnails)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(2)
        title = QLabel(playlist.get("title", ""))
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #f1f1f1;")
        title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        info.addWidget(title)
        local = playlist.get("source", "ytmusic") in LOCAL_SOURCES
        parts = [p for p in (_count_text(playlist, "pista", "pistas"), "Local" if local else "") if p]
        if parts:
            meta = QLabel("  •  ".join(parts))
            meta.setStyleSheet("font-size: 13px; color: #aaa;")
            info.addWidget(meta)
        layout.addLayout(info, stretch=1)


# modal guardar playlist
class SaveToPlaylistDialog(dialogs.Modal):
    def __init__(self, targets, thumbnails, parent=None):
        super().__init__(parent, "Guardar en una playlist", width=DIALOG_SIZE[0], height=DIALOG_SIZE[1])
        self.choice = None
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {theme.BORDER};")
        self.body.addWidget(line)
        self.body.addWidget(self._build_body(targets, thumbnails), stretch=1)
        self.footer.setContentsMargins(20, 10, 20, 18)
        self.new_button = self.add_button("Nueva playlist", "primary", self._ask_new, icon="fa5s.plus")

    def _build_body(self, targets, thumbnails):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(content)
        self.list_layout.setContentsMargins(20, 18, 20, 18)
        self.list_layout.setSpacing(6)

        recent, everything = targets.get("recent", []), targets.get("all", [])
        if recent:
            self.list_layout.addWidget(self._section("Recientes"))
            tiles = QHBoxLayout()
            tiles.setSpacing(4)
            for playlist in recent:
                tile = _RecentTile(playlist, thumbnails)
                tile.activated.connect(lambda p=playlist: self._choose(p))
                tiles.addWidget(tile)
            tiles.addStretch()
            self.list_layout.addLayout(tiles)
            self.list_layout.addSpacing(14)
        if everything:
            self.list_layout.addWidget(self._section("Todas las playlists"))
            for playlist in everything:
                row = _PlaylistRow(playlist, thumbnails)
                row.activated.connect(lambda p=playlist: self._choose(p))
                self.list_layout.addWidget(row)
        else:
            empty = QLabel("Aún no tienes playlists. Crea la primera con «Nueva playlist».")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 14px; padding: 40px 10px;")
            self.list_layout.addWidget(empty)
        self.list_layout.addStretch()
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _section(text):
        label = QLabel(text)
        label.setStyleSheet(_SECTION_QSS + " padding: 4px 0;")
        return label

    def _choose(self, playlist):
        self.choice = ("existing", playlist)
        self.accept()

    def _ask_new(self):
        title = dialogs.prompt_text(self, "Nueva playlist", "Ponle un nombre a tu playlist.",
                                    ok="Crear", placeholder="Título")
        if title:
            self.choice = ("new", title)
            self.accept()
