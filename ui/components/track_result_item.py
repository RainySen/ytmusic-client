import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from utils import scale_cover


class TrackResultItem(QWidget):
    def __init__(self, song, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self.thumb = QLabel()
        self.thumb.setFixedSize(56, 56)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border-radius: 4px; background: #1e1e1e;")
        self.thumb.setPixmap(qta.icon('fa5s.music', color='#444').pixmap(28, 28))
        layout.addWidget(self.thumb)

        meta = QVBoxLayout()
        meta.setSpacing(4)
        meta.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(song.get('title', 'Desconocido'))
        title_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #fff;")
        title_label.setWordWrap(False)

        artists = song.get('artists', [])
        artist_text = ", ".join(a.get('name', '') for a in artists) or "Desconocido"
        artist_label = QLabel(artist_text)
        artist_label.setStyleSheet("color: #aaa; font-size: 12px;")
        artist_label.setWordWrap(False)

        meta.addWidget(title_label)
        meta.addWidget(artist_label)
        layout.addLayout(meta, stretch=1)

    def set_thumbnail(self, pixmap):
        self.thumb.setPixmap(scale_cover(pixmap, 56))
