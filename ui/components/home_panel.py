import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QPushButton, QGridLayout
)

from utils import get_thumbnail_url, scale_cover

CARD_SIZE = 160
MOOD_CHIPS = ["Todos", "Relajación", "Actívate", "Fiesta", "Entrenamiento", "Romance", "Concentración", "Tristeza"]


class MoodChip(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self._update_style()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._update_style()

    def _update_style(self):
        if self.isChecked():
            self.setStyleSheet("""
                QPushButton {
                    background: #ffffff;
                    color: #0f0f0f;
                    border: 1px solid #ffffff;
                    border-radius: 16px;
                    padding: 5px 16px;
                    font-size: 13px;
                    font-weight: 600;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #e0e0e0;
                    border: 1px solid rgba(255,255,255,0.25);
                    border-radius: 16px;
                    padding: 5px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.08);
                    border-color: rgba(255,255,255,0.5);
                    color: white;
                }
            """)


class HomeCard(QWidget):
    clicked = Signal(dict)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(CARD_SIZE + 16)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(8)

        self.thumb = QLabel()
        self.thumb.setFixedSize(CARD_SIZE, CARD_SIZE)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border-radius: 6px; background: #1e1e1e;")
        self.thumb.setPixmap(qta.icon('fa5s.music', color='#444').pixmap(48, 48))
        layout.addWidget(self.thumb)

        title = QLabel(item.get('title', ''))
        title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        title.setWordWrap(True)
        title.setMaximumWidth(CARD_SIZE)
        layout.addWidget(title)

        artists = item.get('artists', [])
        if artists:
            artist_text = ' • '.join(a.get('name', '') for a in artists[:2])
            artist_lbl = QLabel(artist_text)
            artist_lbl.setStyleSheet("font-size: 11px; color: #aaa;")
            artist_lbl.setWordWrap(True)
            artist_lbl.setMaximumWidth(CARD_SIZE)
            layout.addWidget(artist_lbl)

        self._update_bg()

    def set_thumbnail(self, pixmap):
        self.thumb.setPixmap(scale_cover(pixmap, CARD_SIZE))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_bg()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_bg()
        super().leaveEvent(event)

    def _update_bg(self):
        bg = "rgba(255,255,255,0.06)" if self._hovered else "transparent"
        self.setStyleSheet(f"HomeCard {{ background: {bg}; border-radius: 8px; }}")


class CompactSongItem(QWidget):
    clicked = Signal(dict)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self._hovered = False
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        self.thumb = QLabel()
        self.thumb.setFixedSize(40, 40)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border-radius: 4px; background: #1e1e1e;")
        self.thumb.setPixmap(qta.icon('fa5s.music', color='#444').pixmap(24, 24))
        layout.addWidget(self.thumb)

        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        title_text = item.get('title', '')
        title_lbl = QLabel(title_text)
        title_lbl.setStyleSheet("font-size: 13px; color: #e0e0e0;")
        title_lbl.setMaximumWidth(180)

        artist_names = ' • '.join(a.get('name', '') for a in item.get('artists', []))
        subtitle_lbl = QLabel(artist_names)
        subtitle_lbl.setStyleSheet("font-size: 11px; color: #888;")
        subtitle_lbl.setMaximumWidth(180)

        info_layout.addWidget(title_lbl)
        info_layout.addWidget(subtitle_lbl)
        layout.addWidget(info, stretch=1)

        self._update_bg()

    def set_thumbnail(self, pixmap):
        self.thumb.setPixmap(scale_cover(pixmap, 40))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hovered = True
        self._update_bg()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_bg()
        super().leaveEvent(event)

    def _update_bg(self):
        bg = "rgba(255,255,255,0.06)" if self._hovered else "transparent"
        self.setStyleSheet(f"CompactSongItem {{ background: {bg}; border-radius: 6px; }}")


class HomePanel(QWidget):
    item_clicked = Signal(dict)
    mood_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mood_chips = []
        self._active_mood = "Todos"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        chips_area = self._build_chips_row()
        outer.addWidget(chips_area)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #1a1a1a; max-height: 1px;")
        outer.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._layout = QVBoxLayout(self._content)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(28)
        self._layout.addStretch()

        scroll.setWidget(self._content)
        outer.addWidget(scroll, stretch=1)

    def _build_chips_row(self):
        wrapper = QWidget()
        wrapper.setFixedHeight(48)
        wrapper.setStyleSheet("background: #0f0f0f;")

        h_scroll = QScrollArea(wrapper)
        h_scroll.setWidgetResizable(True)
        h_scroll.setFrameShape(QFrame.NoFrame)
        h_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        h_scroll.setStyleSheet("background: transparent;")
        h_scroll.setGeometry(0, 0, 99999, 48)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 6, 16, 6)
        row_layout.setSpacing(8)

        for mood in MOOD_CHIPS:
            chip = MoodChip(mood)
            if mood == "Todos":
                chip.setChecked(True)
            chip.clicked.connect(lambda checked, m=mood: self._on_mood_clicked(m))
            row_layout.addWidget(chip)
            self._mood_chips.append(chip)

        row_layout.addStretch()
        h_scroll.setWidget(row)

        outer = QWidget()
        outer.setFixedHeight(48)
        outer.setStyleSheet("background: #0f0f0f;")
        layout = QVBoxLayout(outer)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(h_scroll)
        return outer

    def _on_mood_clicked(self, mood):
        self._active_mood = mood
        for chip in self._mood_chips:
            chip.setChecked(chip.text() == mood)
        self.mood_selected.emit(mood)

    def show_sections(self, sections, thumbnail_cache):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for title, items in sections:
            if not items:
                continue
            self._layout.insertWidget(
                self._layout.count() - 1,
                self._build_section(title, items, thumbnail_cache)
            )

    def _build_section(self, title, items, thumbnail_cache):
        if items and items[0].get('type') == 'song':
            return self._build_compact_section(title, items, thumbnail_cache)
        return self._build_cards_section(title, items, thumbnail_cache)

    def _build_cards_section(self, title, items, thumbnail_cache):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 22px; font-weight: 700; color: #fff;")
        layout.addWidget(title_label)

        h_scroll = QScrollArea()
        h_scroll.setWidgetResizable(True)
        h_scroll.setFrameShape(QFrame.NoFrame)
        h_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        h_scroll.setFixedHeight(240)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 4)
        row_layout.setSpacing(0)

        for item in items:
            card = HomeCard(item)
            card.clicked.connect(self.item_clicked)
            row_layout.addWidget(card)
            url = get_thumbnail_url(item)
            if url:
                try:
                    thumbnail_cache.request(url, card.set_thumbnail)
                except RuntimeError:
                    pass

        row_layout.addStretch()
        h_scroll.setWidget(row)
        layout.addWidget(h_scroll)

        return section

    def _build_compact_section(self, title, items, thumbnail_cache):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 22px; font-weight: 700; color: #fff;")
        layout.addWidget(title_label)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        for i, item in enumerate(items[:12]):
            row_idx = i // 2
            col_idx = i % 2
            compact_item = CompactSongItem(item)
            compact_item.clicked.connect(self.item_clicked)
            grid.addWidget(compact_item, row_idx, col_idx)
            url = get_thumbnail_url(item)
            if url:
                try:
                    thumbnail_cache.request(url, compact_item.set_thumbnail)
                except RuntimeError:
                    pass

        layout.addWidget(grid_widget)
        return section
