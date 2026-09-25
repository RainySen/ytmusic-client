from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ui.components.chip import Chip
from ui.components.section_feed import SectionFeed

MOOD_CHIPS = [
    "Todos", "Relajación", "Actívate", "Fiesta",
    "Entrenamiento", "Romance", "Concentración", "Tristeza",
]

MoodChip = Chip


class HomePanel(QWidget):
    item_clicked = Signal(dict)
    add_next_clicked = Signal(dict)
    add_queue_clicked = Signal(dict)
    add_playlist_clicked = Signal(dict)
    collection_action_requested = Signal(str, dict)
    play_all_requested = Signal(list)
    item_hovered = Signal(dict)
    mood_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chips = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_chips_row())

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background: #282828; max-height: 1px;")
        outer.addWidget(separator)

        self.feed = SectionFeed()
        for name in ("item_clicked", "add_next_clicked", "add_queue_clicked", "add_playlist_clicked", "collection_action_requested", "play_all_requested", "item_hovered"):
            getattr(self.feed, name).connect(getattr(self, name))
        outer.addWidget(self.feed, stretch=1)

    def _build_chips_row(self):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(48, 8, 48, 8)
        layout.setSpacing(8)
        for mood in MOOD_CHIPS:
            chip = MoodChip(mood)
            chip.setChecked(mood == "Todos")
            chip.clicked.connect(lambda _=False, m=mood: self._on_mood(m))
            layout.addWidget(chip)
            self._chips.append(chip)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(row)
        scroll.setFixedHeight(52)
        return scroll

    def _on_mood(self, mood):
        for chip in self._chips:
            chip.setChecked(chip.text() == mood)
        self.mood_selected.emit(mood)

    def set_loading(self):
        self.feed.set_loading()

    def show_message(self, text):
        self.feed.show_message(text)

    def set_sections(self, sections, thumbnails, reset_scroll=True):
        self.feed.set_sections(sections, thumbnails, reset_scroll)
