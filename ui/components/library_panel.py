import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QScrollArea, QFrame, QTabWidget
)

from ui.components.drop_queue_container import DroppableQueueContainer
from utils import get_thumbnail_url, scale_cover


class _SimilarRow(QWidget):
    clicked = Signal(dict)

    def __init__(self, song, parent=None):
        super().__init__(parent)
        self._song = song
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(10)

        self.thumb = QLabel()
        self.thumb.setFixedSize(40, 40)
        self.thumb.setStyleSheet("border-radius: 4px; background: #1e1e1e;")
        self.thumb.setAlignment(Qt.AlignCenter)

        text = QWidget()
        text_l = QVBoxLayout(text)
        text_l.setContentsMargins(0, 0, 0, 0)
        text_l.setSpacing(2)

        title_lbl = QLabel(song.get('title', ''))
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 500; color: #e6e6e6;")
        title_lbl.setMaximumWidth(220)

        artists = song.get('artists', [])
        artist_str = artists[0].get('name', '') if artists else ''
        artist_lbl = QLabel(artist_str)
        artist_lbl.setStyleSheet("font-size: 11px; color: #aaa;")

        text_l.addWidget(title_lbl)
        text_l.addWidget(artist_lbl)

        layout.addWidget(self.thumb)
        layout.addWidget(text, stretch=1)

    def set_thumbnail(self, px):
        try:
            self.thumb.setPixmap(scale_cover(px, 40))
        except RuntimeError:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._song)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 6px;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("")
        super().leaveEvent(event)


class LibraryPanel(QWidget):
    item_dropped = Signal(int, int)
    clear_requested = Signal()
    save_requested = Signal()
    similar_song_activated = Signal(dict)
    similar_filter_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("right_panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 8, 8)
        layout.setSpacing(8)

        self.right_tabs = QTabWidget()
        self.right_tabs.setObjectName("right_tabs")
        self.right_tabs.addTab(self._build_queue_tab(), qta.icon('fa5s.music', color='white'), "Cola")
        self.right_tabs.addTab(self._build_lyrics_tab(), qta.icon('fa5s.microphone-alt', color='white'), "Letra")
        self.right_tabs.addTab(self._build_similar_tab(), qta.icon('fa5s.compact-disc', color='white'), "Similares")

        layout.addWidget(self.right_tabs)

    def _build_queue_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        queue_header = QWidget()
        queue_header_layout = QHBoxLayout(queue_header)
        queue_header_layout.setContentsMargins(0, 0, 0, 0)

        queue_title = QLabel("Cola de Reproducción")
        queue_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.queue_count_label = QLabel("(0)")
        self.queue_count_label.setStyleSheet("color: #999; font-size: 12px;")

        clear_btn = QPushButton()
        clear_btn.setIcon(qta.icon('fa5s.broom', color='white'))
        clear_btn.setToolTip("Limpiar cola")
        clear_btn.setFixedSize(28, 28)
        clear_btn.clicked.connect(self.clear_requested.emit)
        clear_btn.setStyleSheet("""
            QPushButton { border: none; border-radius: 14px; background: transparent; }
            QPushButton:hover { background: rgba(255,0,0,0.2); }
        """)

        save_btn = QPushButton()
        save_btn.setIcon(qta.icon('fa5s.save', color='white'))
        save_btn.setToolTip("Guardar cola como playlist")
        save_btn.setFixedSize(28, 28)
        save_btn.clicked.connect(self.save_requested.emit)
        save_btn.setStyleSheet("""
            QPushButton { border: none; border-radius: 14px; background: transparent; }
            QPushButton:hover { background: rgba(0,255,0,0.15); }
        """)

        queue_header_layout.addWidget(queue_title)
        queue_header_layout.addWidget(self.queue_count_label)
        queue_header_layout.addStretch()
        queue_header_layout.addWidget(save_btn)
        queue_header_layout.addWidget(clear_btn)
        layout.addWidget(queue_header)

        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.NoFrame)
        self.queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.queue_container = DroppableQueueContainer()
        self.queue_container.item_dropped.connect(self.item_dropped)

        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(4)
        self.queue_layout.addStretch()

        self.queue_scroll.setWidget(self.queue_container)
        layout.addWidget(self.queue_scroll, stretch=10)

        return tab

    def _build_lyrics_tab(self):
        self.lyrics_tab = QWidget()
        layout = QVBoxLayout(self.lyrics_tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.lyrics_list_widget = QListWidget()
        self.lyrics_list_widget.setObjectName("lyrics_list")
        layout.addWidget(self.lyrics_list_widget)

        return self.lyrics_tab

    def _build_similar_tab(self):
        self.similar_tab = QWidget()
        layout = QVBoxLayout(self.similar_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Filter chips row
        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        chips_row.setContentsMargins(0, 0, 0, 0)
        self._similar_chips = {}
        for label in ("Canciones", "Mixes", "Playlists"):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #444;
                    border-radius: 12px;
                    padding: 3px 12px;
                    font-size: 11px;
                    background: transparent;
                    color: #aaa;
                }
                QPushButton:checked {
                    border-color: white;
                    color: white;
                    background: rgba(255,255,255,0.08);
                }
                QPushButton:hover { color: #ddd; }
            """)
            btn.clicked.connect(lambda _, l=label: self._on_similar_chip(l))
            chips_row.addWidget(btn)
            self._similar_chips[label] = btn
        chips_row.addStretch()
        self._similar_chips["Canciones"].setChecked(True)
        layout.addLayout(chips_row)

        self.similar_scroll = QScrollArea()
        self.similar_scroll.setWidgetResizable(True)
        self.similar_scroll.setFrameShape(QFrame.NoFrame)
        self.similar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.similar_container = QWidget()
        self.similar_layout = QVBoxLayout(self.similar_container)
        self.similar_layout.setContentsMargins(0, 0, 0, 0)
        self.similar_layout.setSpacing(2)
        self.similar_layout.addStretch()

        self.similar_scroll.setWidget(self.similar_container)
        layout.addWidget(self.similar_scroll)

        return self.similar_tab

    def _on_similar_chip(self, label):
        for lbl, btn in self._similar_chips.items():
            btn.setChecked(lbl == label)
        self.similar_filter_changed.emit(label)

    def show_similar_songs(self, songs, thumbnail_cache):
        while self.similar_layout.count() > 1:
            item = self.similar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for song in songs:
            row = _SimilarRow(song)
            row.clicked.connect(self.similar_song_activated.emit)
            self.similar_layout.insertWidget(self.similar_layout.count() - 1, row)
            url = get_thumbnail_url(song)
            if url:
                thumbnail_cache.request(url, row.set_thumbnail)
