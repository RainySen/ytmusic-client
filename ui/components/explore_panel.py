import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from core.i18n import t
from ui import theme
from ui.components.section_feed import SectionFeed

# label keys: translated when the panel is built, after the language is set
_JUMP_BUTTONS = (
    ("explore.jump.new_releases", "fa5s.compact-disc"),
    ("explore.jump.charts", "fa5s.chart-line"),
    ("explore.jump.moods_genres", "fa5s.smile"),
)


def _button_qss() -> str:
    return f"""
    QPushButton {{ background: {theme.SURFACE}; color: {theme.TEXT}; border: none; border-radius: {theme.radius(8)}px;
                  padding: 0 18px; font-size: 17px; font-weight: 700; text-align: left; }}
    QPushButton:hover {{ background: {theme.SURFACE_RAISED}; }}
"""


def _back_qss() -> str:
    return f"""
    QPushButton {{ background: transparent; color: {theme.TEXT_SECONDARY}; border: none; font-size: 13px;
                   padding: 6px 4px; }}
    QPushButton:hover {{ color: {theme.TEXT}; }}
"""


class ExplorePanel(QWidget):
    item_clicked = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    collection_action_requested = Signal(str, dict)
    play_all_requested = Signal(list)
    item_hovered = Signal(dict)
    jump_requested = Signal(int)
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(48, 20, 48, 0)
        top_layout.setSpacing(6)

        self._jump_row = QWidget()
        row = QHBoxLayout(self._jump_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        for index, (label, icon) in enumerate(_JUMP_BUTTONS):
            button = QPushButton("  " + t(label))
            button.setIcon(qta.icon(icon, color=theme.TEXT_SECONDARY))
            button.setFixedHeight(64)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(_button_qss())
            button.clicked.connect(lambda _=False, i=index: self.jump_requested.emit(i))
            row.addWidget(button, stretch=1)
        top_layout.addWidget(self._jump_row)

        self._back = QPushButton("←  " + t("explore.back"))
        self._back.setCursor(Qt.PointingHandCursor)
        self._back.setStyleSheet(_back_qss())
        self._back.clicked.connect(self.back_requested)
        self._back.hide()
        top_layout.addWidget(self._back, alignment=Qt.AlignLeft)
        outer.addWidget(top)

        self.feed = SectionFeed()
        for name in ("item_clicked", "add_next_clicked", "add_queue_clicked", "add_playlist_clicked", "collection_action_requested", "play_all_requested", "item_hovered"):
            getattr(self.feed, name).connect(getattr(self, name))
        outer.addWidget(self.feed, stretch=1)

    def set_detail_mode(self, detail: bool) -> None:
        self._jump_row.setVisible(not detail)
        self._back.setVisible(detail)

    def reveal(self, index: int) -> None:
        self.feed.reveal(index)

    def set_loading(self):
        self.feed.set_loading()

    def show_message(self, text):
        self.feed.show_message(text)

    def set_sections(self, sections, thumbnails, reset_scroll=True):
        self.feed.set_sections(sections, thumbnails, reset_scroll)
