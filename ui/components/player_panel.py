from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider


class PlayerPanel(QWidget):
    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.setObjectName("player_widget")
        self.setFixedHeight(170)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        info_row = QHBoxLayout()
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 6px; background: #1a1a1a;")

        self.song_label = QLabel("Sin reproducción")
        self.song_label.setObjectName("song_label")
        self.song_label.setSizePolicy(self.song_label.sizePolicy())

        info_row.addWidget(self.cover_label)
        info_row.addSpacing(12)
        info_row.addWidget(self.song_label)
        info_row.addStretch()

        progress_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(45)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setFixedWidth(45)

        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider, stretch=1)
        progress_layout.addWidget(self.total_time_label)

        ctrl_layout = QHBoxLayout()
        left_controls = QHBoxLayout()
        left_controls.addStretch()

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.icons["prev"])
        self.prev_button.setFixedSize(42, 42)
        self.prev_button.setCursor(Qt.PointingHandCursor)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icons["play"])
        self.play_button.setFixedSize(52, 52)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setObjectName("play_button")

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icons["next"])
        self.next_button.setFixedSize(42, 42)
        self.next_button.setCursor(Qt.PointingHandCursor)

        left_controls.addWidget(self.prev_button)
        left_controls.addWidget(self.play_button)
        left_controls.addWidget(self.next_button)
        left_controls.addStretch()

        right_controls = QHBoxLayout()

        self.lyrics_button = QPushButton()
        self.lyrics_button.setIcon(self.icons["lyrics"])
        self.lyrics_button.setToolTip("Ver letra")
        self.lyrics_button.setFixedSize(36, 36)
        self.lyrics_button.setCursor(Qt.PointingHandCursor)

        self.loop_button = QPushButton()
        self.loop_button.setIcon(self.icons["loop_off"])
        self.loop_button.setToolTip("Repetir")
        self.loop_button.setFixedSize(36, 36)
        self.loop_button.setCursor(Qt.PointingHandCursor)

        self.autoplay_button = QPushButton()
        self.autoplay_button.setIcon(self.icons["autoplay_off"])
        self.autoplay_button.setToolTip("Autoplay")
        self.autoplay_button.setFixedSize(36, 36)
        self.autoplay_button.setCursor(Qt.PointingHandCursor)

        vol_icon = QLabel()
        vol_icon.setPixmap(self.icons["volume"].pixmap(20, 20))

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(120)

        right_controls.addWidget(self.lyrics_button)
        right_controls.addWidget(self.loop_button)
        right_controls.addWidget(self.autoplay_button)
        right_controls.addSpacing(12)
        right_controls.addWidget(vol_icon)
        right_controls.addWidget(self.volume_slider)

        ctrl_layout.addLayout(left_controls, stretch=3)
        ctrl_layout.addLayout(right_controls, stretch=2)

        layout.addLayout(info_row)
        layout.addLayout(progress_layout)
        layout.addLayout(ctrl_layout)

    def set_cover_placeholder(self, pixmap):
        self.cover_label.setPixmap(pixmap)
