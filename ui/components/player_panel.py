import qtawesome as qta
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider


class _ClickableArea(QWidget):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# barra player
class PlayerPanel(QWidget):
    expand_clicked = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self._is_expanded = False
        self.setObjectName("player_widget")
        self.setFixedHeight(80)
        self.setAttribute(Qt.WA_StyledBackground, True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 16, 0)
        outer.setSpacing(0)

        info_area = _ClickableArea()
        info_area.setCursor(Qt.PointingHandCursor)
        info_area.setFixedWidth(280)
        info_area.clicked.connect(self.expand_clicked.emit)

        info_l = QHBoxLayout(info_area)
        info_l.setContentsMargins(16, 0, 16, 0)
        info_l.setSpacing(12)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(52, 52)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("border-radius: 6px; background: #2a2a2a;")

        text_col = QWidget()
        text_l = QVBoxLayout(text_col)
        text_l.setContentsMargins(0, 0, 0, 0)
        text_l.setSpacing(2)

        self.song_label = QLabel("Sin reproducción")
        self.song_label.setObjectName("song_label")

        self.artist_label = QLabel("")
        self.artist_label.setStyleSheet("font-size: 11px; color: #aaa;")

        text_l.addWidget(self.song_label)
        text_l.addWidget(self.artist_label)

        info_l.addWidget(self.cover_label)
        info_l.addWidget(text_col, stretch=1)
        outer.addWidget(info_area)

        center = QWidget()
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(0, 6, 0, 6)
        center_l.setSpacing(4)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(4)

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.icons["prev"])
        self.prev_button.setFixedSize(36, 36)
        self.prev_button.setCursor(Qt.PointingHandCursor)
        self.prev_button.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 18px; }
            QPushButton:hover { background: rgba(255,255,255,0.10); }
        """)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icons["play"])
        self.play_button.setIconSize(QSize(18, 18))
        self.play_button.setFixedSize(40, 40)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setObjectName("play_button")

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icons["next"])
        self.next_button.setFixedSize(36, 36)
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 18px; }
            QPushButton:hover { background: rgba(255,255,255,0.10); }
        """)

        ctrl_row.addStretch()
        ctrl_row.addWidget(self.prev_button)
        ctrl_row.addWidget(self.play_button)
        ctrl_row.addWidget(self.next_button)
        ctrl_row.addStretch()

        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)

        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(40)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setStyleSheet("font-size: 11px; color: #aaa;")

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setFixedWidth(40)
        self.total_time_label.setStyleSheet("font-size: 11px; color: #aaa;")

        prog_row.addWidget(self.time_label)
        prog_row.addWidget(self.progress_slider, stretch=1)
        prog_row.addWidget(self.total_time_label)

        center_l.addLayout(ctrl_row)
        center_l.addLayout(prog_row)
        outer.addWidget(center, stretch=1)

        right = QWidget()
        right.setFixedWidth(300)
        right_l = QHBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(2)

        _aux_style = """
            QPushButton { background: transparent; border: none; border-radius: 17px; }
            QPushButton:hover { background: rgba(255,255,255,0.10); }
        """

        self.shuffle_button = QPushButton()
        self.shuffle_button.setIcon(qta.icon('fa5s.random', color='#aaa'))
        self.shuffle_button.setToolTip("Aleatorio")
        self.shuffle_button.setFixedSize(34, 34)
        self.shuffle_button.setCursor(Qt.PointingHandCursor)
        self.shuffle_button.setStyleSheet(_aux_style)

        self.loop_button = QPushButton()
        self.loop_button.setIcon(self.icons["loop_off"])
        self.loop_button.setToolTip("Repetir")
        self.loop_button.setFixedSize(34, 34)
        self.loop_button.setCursor(Qt.PointingHandCursor)
        self.loop_button.setStyleSheet(_aux_style)

        vol_icon = QLabel()
        vol_icon.setPixmap(self.icons["volume"].pixmap(16, 16))

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(90)

        self._expand_btn = QPushButton()
        self._expand_btn.setIcon(qta.icon('fa5s.chevron-up', color='#aaa'))
        self._expand_btn.setToolTip("Ampliar")
        self._expand_btn.setFixedSize(34, 34)
        self._expand_btn.setCursor(Qt.PointingHandCursor)
        self._expand_btn.clicked.connect(self.expand_clicked.emit)
        self._expand_btn.setStyleSheet(_aux_style)

        right_l.addWidget(self.shuffle_button)
        right_l.addWidget(self.loop_button)
        right_l.addSpacing(6)
        right_l.addWidget(vol_icon)
        right_l.addWidget(self.volume_slider)
        right_l.addSpacing(4)
        right_l.addWidget(self._expand_btn)

        outer.addWidget(right)

    def set_expanded(self, expanded: bool):
        self._is_expanded = expanded
        icon = 'fa5s.chevron-down' if expanded else 'fa5s.chevron-up'
        self._expand_btn.setIcon(qta.icon(icon, color='#aaa'))

    def set_cover_placeholder(self, pixmap):
        self.cover_label.setPixmap(pixmap)
