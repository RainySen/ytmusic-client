import qtawesome as qta
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMenu, QPushButton

from core.i18n import t
from ui import theme
from ui.components.jump_slider import JumpSlider
from ui.components.link_label import LinkLabel
from ui.components.marquee_label import MarqueeLabel
from ui.components.track_actions import MENU_QSS, song_entries, song_hub

VOLUME_STEP_ICONS = ((1, "fa5s.volume-mute"), (34, "fa5s.volume-off"), (67, "fa5s.volume-down"), (101, "fa5s.volume-up"))
DEFAULT_UNMUTE = 50
INFO_WIDTH = 380


def _slim_slider_qss() -> str:
    return f"""
    QSlider::groove:horizontal {{ height: 3px; background: {theme.overlay(0.16)}; border-radius: {theme.radius(1)}px; }}
    QSlider::sub-page:horizontal {{ background: {theme.ACCENT}; border-radius: {theme.radius(1)}px; }}
    QSlider::handle:horizontal {{ width: 11px; height: 11px; margin: -4px 0; border-radius: {theme.radius(5)}px;
                                  background: {theme.ACCENT}; }}
    QSlider::handle:horizontal:hover {{ background: {theme.ACCENT}; }}
"""


class PlayerPanel(QWidget):
    expand_clicked = Signal()
    like_clicked = Signal()
    artist_clicked = Signal()
    album_clicked = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self._is_expanded = False
        self.setObjectName("player_widget")
        self.setFixedHeight(80)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self._before_mute = DEFAULT_UNMUTE
        self._playing = False
        self.song: dict | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addLayout(self._build_progress_row())

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 16, 0)
        row.setSpacing(0)
        outer.addLayout(row, stretch=1)

        info_area = QWidget()
        info_area.setFixedWidth(INFO_WIDTH)

        info_l = QHBoxLayout(info_area)
        info_l.setContentsMargins(16, 0, 16, 0)
        info_l.setSpacing(12)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(52, 52)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet(f"border-radius: {theme.radius(6)}px; background: {theme.SURFACE_RAISED};")

        text_col = QWidget()
        text_l = QVBoxLayout(text_col)
        text_l.setContentsMargins(0, 0, 0, 0)
        text_l.setSpacing(2)

        self.song_label = MarqueeLabel(t("player.now_playing.empty"))
        self.song_label.setObjectName("song_label")

        self.artist_label = LinkLabel("")
        self.album_label = LinkLabel("")
        self.artist_label.clicked.connect(self.artist_clicked)
        self.album_label.clicked.connect(self.album_clicked)
        self._separator = QLabel("·")
        self._separator.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_SECONDARY}; background: transparent;")
        meta = QHBoxLayout()
        meta.setContentsMargins(0, 0, 0, 0)
        meta.setSpacing(4)
        meta.addWidget(self.artist_label)
        meta.addWidget(self._separator)
        meta.addWidget(self.album_label)
        meta.addStretch(1)

        text_l.addWidget(self.song_label)
        text_l.addLayout(meta)
        self.set_meta("", "")

        info_l.addWidget(self.cover_label)
        info_l.addWidget(text_col, stretch=1)
        row.addWidget(info_area)

        center = QWidget()
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(0, 0, 0, 0)
        center_l.setSpacing(0)
        center_l.setAlignment(Qt.AlignVCenter)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(4)

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.icons["prev"])
        self.prev_button.setFixedSize(36, 36)
        self.prev_button.setCursor(Qt.PointingHandCursor)
        self.prev_button.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: {theme.radius(18)}px; }}
            QPushButton:hover {{ background: {theme.overlay(0.10)}; }}
        """)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icons["play"])
        self.play_button.setIconSize(QSize(18, 18))
        self.play_button.setFixedSize(40, 40)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setObjectName("play_button")
        self._play_glow = theme.glow_effect()
        self.play_button.setGraphicsEffect(self._play_glow)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icons["next"])
        self.next_button.setFixedSize(36, 36)
        self.next_button.setCursor(Qt.PointingHandCursor)
        self.next_button.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: {theme.radius(18)}px; }}
            QPushButton:hover {{ background: {theme.overlay(0.10)}; }}
        """)

        ctrl_row.addStretch()
        ctrl_row.addWidget(self.prev_button)
        ctrl_row.addWidget(self.play_button)
        ctrl_row.addWidget(self.next_button)
        ctrl_row.addStretch()

        center_l.addLayout(ctrl_row)
        row.addWidget(center, stretch=1)

        right = QWidget()
        right.setFixedWidth(360)
        right_l = QHBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.setSpacing(2)

        _aux_style = f"""
            QPushButton {{ background: transparent; border: none; border-radius: {theme.radius(17)}px; }}
            QPushButton:hover {{ background: {theme.overlay(0.10)}; }}
        """

        self.like_button = QPushButton()
        self.like_button.setFixedSize(34, 34)
        self.like_button.setCursor(Qt.PointingHandCursor)
        self.like_button.setStyleSheet(_aux_style)
        self.like_button.clicked.connect(self.like_clicked)
        self.set_liked(False)

        self.shuffle_button = QPushButton()
        self.shuffle_button.setIcon(qta.icon('fa5s.random', color=theme.TEXT_SECONDARY))
        self.shuffle_button.setToolTip(t("player.tooltip.shuffle"))
        self.shuffle_button.setFixedSize(34, 34)
        self.shuffle_button.setCursor(Qt.PointingHandCursor)
        self.shuffle_button.setStyleSheet(_aux_style)

        self.loop_button = QPushButton()
        self.loop_button.setIcon(self.icons["loop_off"])
        self.loop_button.setToolTip(t("player.tooltip.repeat"))
        self.loop_button.setFixedSize(34, 34)
        self.loop_button.setCursor(Qt.PointingHandCursor)
        self.loop_button.setStyleSheet(_aux_style)

        self.mute_button = QPushButton()
        self.mute_button.setIconSize(QSize(16, 16))
        self.mute_button.setFixedSize(34, 34)
        self.mute_button.setCursor(Qt.PointingHandCursor)
        self.mute_button.setStyleSheet(_aux_style)
        self.mute_button.clicked.connect(self.toggle_mute)

        self.volume_slider = JumpSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume)

        self.volume_label = QLabel()
        self.volume_label.setFixedWidth(34)
        self.volume_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.volume_label.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_SECONDARY};")
        self._on_volume(self.volume_slider.value())

        self._expand_btn = QPushButton()
        self._expand_btn.setIcon(qta.icon('fa5s.chevron-up', color=theme.TEXT_SECONDARY))
        self._expand_btn.setToolTip(t("player.tooltip.expand"))
        self._expand_btn.setFixedSize(34, 34)
        self._expand_btn.setCursor(Qt.PointingHandCursor)
        self._expand_btn.clicked.connect(self.expand_clicked.emit)
        self._expand_btn.setStyleSheet(_aux_style)

        right_l.addWidget(self.like_button)
        right_l.addWidget(self.shuffle_button)
        right_l.addWidget(self.loop_button)
        right_l.addSpacing(6)
        right_l.addWidget(self.mute_button)
        right_l.addWidget(self.volume_slider)
        right_l.addWidget(self.volume_label)
        right_l.addSpacing(4)
        right_l.addWidget(self._expand_btn)

        row.addWidget(right)

    def _build_progress_row(self) -> QHBoxLayout:
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(14, 0, 14, 0)
        prog_row.setSpacing(8)

        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(36)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_SECONDARY};")

        self.progress_slider = JumpSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setFixedHeight(14)
        self.progress_slider.setStyleSheet(_slim_slider_qss())

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setFixedWidth(36)
        self.total_time_label.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_SECONDARY};")

        prog_row.addWidget(self.time_label)
        prog_row.addWidget(self.progress_slider, stretch=1)
        prog_row.addWidget(self.total_time_label)
        return prog_row

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.expand_clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self._show_menu(self.build_menu(), event.globalPos())

    def _show_menu(self, menu: QMenu, position) -> None:
        menu.exec(position)

    def build_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(MENU_QSS)
        light = theme.TEXT
        menu.addAction(qta.icon("fa5s.pause" if self._playing else "fa5s.play", color=light),
                       t("player.menu.pause") if self._playing else t("player.menu.play")
                       ).triggered.connect(self.play_button.click)
        menu.addAction(qta.icon("fa5s.step-backward", color=light),
                       t("player.menu.previous")).triggered.connect(self.prev_button.click)
        menu.addAction(qta.icon("fa5s.step-forward", color=light),
                       t("player.menu.next")).triggered.connect(self.next_button.click)
        menu.addSeparator()
        menu.addAction(qta.icon("fa5s.random", color=light),
                       t("player.menu.shuffle")).triggered.connect(self.shuffle_button.click)
        menu.addAction(qta.icon("fa5s.sync-alt", color=light),
                       t("player.menu.change_repeat")).triggered.connect(self.loop_button.click)
        muted = self.volume_slider.value() == 0
        menu.addAction(qta.icon("fa5s.volume-up" if muted else "fa5s.volume-mute", color=light),
                       t("player.menu.unmute") if muted else t("player.menu.mute")).triggered.connect(self.toggle_mute)
        song = self.song
        extra = [entry for entry in song_entries(song) if entry[0] in ("artist", "pin")] if song else []
        if extra:
            menu.addSeparator()
            for key, label, icon in extra:
                menu.addAction(qta.icon(icon, color=light), label).triggered.connect(
                    lambda _=False, k=key: song_hub.relay(k, song))
        menu.addSeparator()
        menu.addAction(qta.icon("fa5s.chevron-down" if self._is_expanded else "fa5s.chevron-up", color=light),
                       t("player.menu.close_player") if self._is_expanded else t("player.menu.open_player")
                       ).triggered.connect(self.expand_clicked)
        return menu

    def toggle_mute(self) -> None:
        if self.volume_slider.value() > 0:
            self._before_mute = self.volume_slider.value()
            self.volume_slider.setValue(0)
        else:
            self.volume_slider.setValue(self._before_mute or DEFAULT_UNMUTE)

    def _on_volume(self, value: int) -> None:
        icon = next(name for limit, name in VOLUME_STEP_ICONS if value < limit)
        self.mute_button.setIcon(qta.icon(icon, color=theme.TEXT))
        self.mute_button.setToolTip(t("player.tooltip.unmute") if value == 0 else t("player.tooltip.mute"))
        self.volume_label.setText(f"{value}%")
        self.volume_slider.setToolTip(t("player.tooltip.volume", value=value))

    def set_playing(self, playing: bool) -> None:
        self._playing = playing

    def set_meta(self, artist: str, album: str) -> None:
        self.artist_label.setText(artist)
        self.album_label.setText(album)
        self.album_label.setVisible(bool(album))
        self._separator.setVisible(bool(album) and bool(artist))

    def set_liked(self, liked: bool, available: bool = True) -> None:
        self.like_button.setIcon(qta.icon("fa5s.heart", color=theme.ACCENT if liked else theme.TEXT_SECONDARY))
        self.like_button.setToolTip(t("player.tooltip.unlike") if liked else t("player.tooltip.like"))
        self.like_button.setEnabled(available)

    def set_expanded(self, expanded: bool):
        self._is_expanded = expanded
        icon = 'fa5s.chevron-down' if expanded else 'fa5s.chevron-up'
        self._expand_btn.setIcon(qta.icon(icon, color=theme.TEXT_SECONDARY))

    def set_cover_placeholder(self, pixmap):
        self.cover_label.setPixmap(pixmap)
