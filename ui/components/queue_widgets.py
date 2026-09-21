from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, QLabel, QPushButton
import qtawesome as qta


class ImprovedQueueItem(QWidget):
    play_clicked = Signal(int)
    remove_clicked = Signal(int)

    def __init__(self, song, index, is_current=False):
        super().__init__()
        self.index = index
        self.song = song
        self.is_current = is_current
        self.drag_start_position = None

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.play_indicator = QLabel()
        if is_current:
            self.play_indicator.setPixmap(qta.icon('fa5s.volume-up', color='#FF0000').pixmap(14, 14))
        else:
            self.play_indicator.setPixmap(qta.icon('fa5s.grip-vertical', color='#666').pixmap(14, 14))
        self.play_indicator.setFixedWidth(20)
        self.play_indicator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.play_indicator.setCursor(Qt.OpenHandCursor)

        thumb = QLabel()
        thumb.setFixedSize(40, 40)
        thumb.setPixmap(qta.icon('fa5s.music', color='#666').pixmap(40, 40))
        thumb.setScaledContents(True)
        thumb.setStyleSheet("border-radius: 4px; background: #1a1a1a;")
        thumb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(song.get('title', 'Desconocido'))
        self.title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.title_label.setWordWrap(False)
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title_label.setTextFormat(Qt.PlainText)
        self.title_label.setTextInteractionFlags(Qt.NoTextInteraction)

        self.full_title = song.get('title', 'Desconocido')

        artist_text = ", ".join([a.get('name', '') for a in song.get('artists', [])]) if song.get('artists') else "Desconocido"
        self.artist_label = QLabel(artist_text)
        self.artist_label.setStyleSheet("color: #999; font-size: 11px;")
        self.artist_label.setWordWrap(False)
        self.artist_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.artist_label.setTextInteractionFlags(Qt.NoTextInteraction)

        self.full_artist = artist_text

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)

        buttons_container = QWidget()
        buttons_container.setFixedWidth(64)
        buttons_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(4)

        btn_play = QPushButton()
        btn_play.setIcon(qta.icon('fa5s.play', color='white'))
        btn_play.setFixedSize(28, 28)
        btn_play.clicked.connect(lambda: self.play_clicked.emit(self.index))
        btn_play.setCursor(Qt.PointingHandCursor)
        btn_play.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 14px;
                background: transparent;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)

        btn_remove = QPushButton()
        btn_remove.setIcon(qta.icon('fa5s.times', color='#999'))
        btn_remove.setFixedSize(28, 28)
        btn_remove.clicked.connect(lambda: self.remove_clicked.emit(self.index))
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 14px;
                background: transparent;
            }
            QPushButton:hover {
                background: rgba(255,0,0,0.2);
            }
        """)

        buttons_layout.addWidget(btn_play)
        buttons_layout.addWidget(btn_remove)

        layout.addWidget(self.play_indicator)
        layout.addWidget(thumb)
        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(buttons_container)

        self.setFixedHeight(56)

        bg_color = "rgba(255,0,0,0.08)" if is_current else "transparent"
        border_color = "rgba(255,0,0,0.3)" if is_current else "transparent"
        self.setStyleSheet(f"""
            ImprovedQueueItem {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            ImprovedQueueItem:hover {{
                background: rgba(255,255,255,0.03);
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.play_indicator.geometry().contains(event.pos()):
                self.drag_start_position = event.pos()
                self.play_indicator.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self.drag_start_position is None:
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.index))
        drag.setMimeData(mime_data)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec(Qt.MoveAction)

        self.play_indicator.setCursor(Qt.OpenHandCursor)
        self.drag_start_position = None

    def mouseReleaseEvent(self, event):
        self.play_indicator.setCursor(Qt.OpenHandCursor)
        self.drag_start_position = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        available_width = self.width() - 156

        if available_width > 50:
            font_metrics = self.title_label.fontMetrics()
            self.title_label.setText(font_metrics.elidedText(self.full_title, Qt.ElideRight, available_width))
            self.artist_label.setText(font_metrics.elidedText(self.full_artist, Qt.ElideRight, available_width))
