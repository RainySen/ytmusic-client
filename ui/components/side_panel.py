from html import escape

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from domain.models import Lyrics
from ui.components.drop_queue_container import DroppableQueueContainer
from ui.components.queue_widgets import ImprovedQueueItem
from ui.components.section_feed import CardsSection, CompactSection

PANEL_WIDTH = 420
TAB_QUEUE, TAB_LYRICS, TAB_SIMILAR = range(3)
_TAB_LABELS = ("A continuación", "Letra", "Similares")

_ICON_BUTTON = """
    QPushButton { border: none; border-radius: 14px; background: transparent; }
    QPushButton:hover { background: %s; }
"""
_TAB_QSS = """
    QPushButton { background: transparent; color: #9a9a9a; border: none; border-bottom: 2px solid transparent;
                  padding: 14px 4px; font-size: 12px; font-weight: 600; }
    QPushButton:hover { color: #dddddd; }
    QPushButton:checked { color: white; border-bottom: 2px solid white; }
"""
LYRICS_TEXT_WIDTH = PANEL_WIDTH - 32 - 24
_SUNG, _ACTIVE_DIM, _OTHER_LINE = "#ffffff", "#a8a8a8", "#6c6c6c"
_HINT_QSS = "color: #888; font-size: 13px; padding: 40px 12px;"


# panel lateral cola letra similares
class SidePanel(QWidget):
    queue_item_activated = Signal(int)
    queue_item_removed = Signal(int)
    queue_item_moved = Signal(int, int)
    clear_requested = Signal()
    save_requested = Signal()

    similar_tab_opened = Signal()
    similar_item_chosen = Signal(dict)
    similar_add_next = Signal(dict)
    similar_add_queue = Signal(dict)
    similar_add_playlist = Signal(dict)
    similar_collection_action = Signal(str, dict)
    similar_item_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("right_panel")
        self.setFixedWidth(PANEL_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_queue_tab())
        self._stack.addWidget(self._build_lyrics_tab())
        self._stack.addWidget(self._build_similar_tab())
        layout.addWidget(self._build_tab_row())
        layout.addWidget(self._stack, stretch=1)

    def _build_tab_row(self):
        row = QWidget()
        row.setObjectName("tab_row")
        row.setStyleSheet("#tab_row { border-bottom: 1px solid #333; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(16, 6, 16, 0)
        layout.setSpacing(0)
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        for index, label in enumerate(_TAB_LABELS):
            button = QPushButton(label.upper())
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(_TAB_QSS)
            button.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self._tab_group.addButton(button, index)
            layout.addWidget(button, stretch=1)
        self._tab_group.button(TAB_QUEUE).setChecked(True)
        self._tab_group.idClicked.connect(self._select_tab)
        return row

    def _select_tab(self, index):
        self._tab_group.button(index).setChecked(True)
        self._stack.setCurrentIndex(index)
        if index == TAB_SIMILAR:
            self.similar_tab_opened.emit()

    def current_tab(self):
        return self._stack.currentIndex()

    def is_similar_tab_active(self):
        return self.current_tab() == TAB_SIMILAR

    def _build_queue_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 12, 16, 8)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Cola de reproducción")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._queue_count = QLabel("(0)")
        self._queue_count.setStyleSheet("color: #999; font-size: 12px;")
        header.addWidget(title)
        header.addWidget(self._queue_count)
        header.addStretch()
        header.addWidget(self._icon_button("fa5s.save", "Guardar cola como playlist",
                                           "rgba(0,255,0,0.15)", self.save_requested.emit))
        header.addWidget(self._icon_button("fa5s.broom", "Limpiar cola",
                                           "rgba(255,0,0,0.2)", self.clear_requested.emit))
        layout.addLayout(header)

        self._queue_scroll = QScrollArea()
        self._queue_scroll.setWidgetResizable(True)
        self._queue_scroll.setFrameShape(QFrame.NoFrame)
        self._queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = DroppableQueueContainer()
        container.item_dropped.connect(self.queue_item_moved)
        self._queue_layout = QVBoxLayout(container)
        self._queue_layout.setContentsMargins(0, 0, 0, 0)
        self._queue_layout.setSpacing(4)
        self._queue_layout.addStretch()
        self._queue_scroll.setWidget(container)
        layout.addWidget(self._queue_scroll, stretch=10)
        return tab

    @staticmethod
    def _icon_button(icon, tooltip, hover, on_click):
        button = QPushButton()
        button.setIcon(qta.icon(icon, color="white"))
        button.setToolTip(tooltip)
        button.setFixedSize(28, 28)
        button.setStyleSheet(_ICON_BUTTON % hover)
        button.clicked.connect(on_click)
        return button

    def set_queue(self, songs, current_index, thumbnails):
        while self._queue_layout.count() > 1:
            widget = self._queue_layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        self._queue_count.setText(f"({len(songs)})")
        for index, song in enumerate(songs):
            item = ImprovedQueueItem(song, index, index == current_index, thumbnails)
            item.play_clicked.connect(self.queue_item_activated)
            item.remove_clicked.connect(self.queue_item_removed)
            self._queue_layout.insertWidget(index, item)

        if 0 <= current_index < len(songs):
            QTimer.singleShot(100, lambda: self._scroll_to(current_index))

    def _scroll_to(self, index):
        if 0 <= index < self._queue_layout.count() - 1:
            widget = self._queue_layout.itemAt(index).widget()
            if widget is not None:
                self._queue_scroll.ensureWidgetVisible(widget)

    def _build_lyrics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 12, 16, 8)
        self._lyrics = QListWidget()
        self._lyrics.setObjectName("lyrics_list")
        layout.addWidget(self._lyrics)
        self._lyrics_credit = QLabel()
        self._lyrics_credit.setAlignment(Qt.AlignCenter)
        self._lyrics_credit.setStyleSheet("color: #6c6c6c; font-size: 11px; padding-top: 4px;")
        self._lyrics_credit.hide()
        layout.addWidget(self._lyrics_credit)
        self._lyric_words = {}
        self._lyric_sung = {}
        self._lyric_active = -1
        return tab

    def set_lyrics(self, lyrics: Lyrics):
        if not lyrics.word_synced:
            self.set_lyrics_lines(lyrics.texts)
        else:
            self._reset_lyrics()
            font = QFont()
            font.setPixelSize(16)
            font.setWeight(QFont.DemiBold)
            for index, line in enumerate(lyrics.lines):
                item = QListWidgetItem()
                item.setFlags(Qt.ItemIsEnabled)
                self._lyrics.addItem(item)
                label = QLabel()
                label.setWordWrap(True)
                label.setTextFormat(Qt.RichText)
                label.setAlignment(Qt.AlignCenter)
                label.setFixedWidth(LYRICS_TEXT_WIDTH)
                label.setStyleSheet("background: transparent;")
                label.setFont(font)
                self._lyric_words[index] = (label, line.words)
                self._render_lyric(index, lit=0, active=False)
                item.setSizeHint(QSize(LYRICS_TEXT_WIDTH, label.heightForWidth(LYRICS_TEXT_WIDTH) + 16))
                self._lyrics.setItemWidget(item, label)
        self._lyrics_credit.setText(f"Letra: {lyrics.source}" if lyrics.source else "")
        self._lyrics_credit.setVisible(bool(lyrics.source))

    def _reset_lyrics(self):
        self._lyrics.clear()
        self._lyric_words = {}
        self._lyric_sung = {}
        self._lyric_active = -1

    def set_lyrics_lines(self, lines):
        self._reset_lyrics()
        self._lyrics_credit.hide()
        for line in lines:
            item = QListWidgetItem(line)
            item.setTextAlignment(Qt.AlignCenter)
            self._lyrics.addItem(item)

    def set_lyrics_message(self, message, focus=False):
        self.set_lyrics_lines([message])
        if focus:
            self._select_tab(TAB_LYRICS)

    def highlight_lyric(self, index):
        if 0 <= index < self._lyrics.count():
            self._lyrics.setCurrentRow(index)
            self._lyrics.scrollToItem(self._lyrics.item(index), QListWidget.PositionAtCenter)

    # letra palabras
    def set_lyric_progress(self, index, current_ms):
        entry = self._lyric_words.get(index)
        if entry is None:
            return
        if index != self._lyric_active:
            previous = self._lyric_active
            self._lyric_active = index
            if previous in self._lyric_words:
                self._render_lyric(previous, lit=0, active=False)
            self._lyric_sung.pop(index, None)
        lit = sum(1 for word in entry[1] if word.start_ms <= current_ms)
        if self._lyric_sung.get(index) != lit:
            self._lyric_sung[index] = lit
            self._render_lyric(index, lit=lit, active=True)

    def _render_lyric(self, index, lit, active):
        label, words = self._lyric_words[index]
        dim = _ACTIVE_DIM if active else _OTHER_LINE
        html = "".join(
            f'<span style="color:{_SUNG if position < lit else dim}">{escape(word.text)}</span>'
            for position, word in enumerate(words))
        label.setText(html.replace("  ", "&nbsp; "))

    def _build_similar_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._similar_layout = QVBoxLayout(content)
        self._similar_layout.setContentsMargins(16, 16, 16, 24)
        self._similar_layout.setSpacing(28)
        self._similar_layout.addStretch()
        scroll.setWidget(content)
        self._similar_scroll = scroll
        return scroll

    def _clear_similar(self):
        while self._similar_layout.count() > 1:
            widget = self._similar_layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def set_similar_message(self, text):
        self._clear_similar()
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet(_HINT_QSS)
        self._similar_layout.insertWidget(0, label)

    def set_similar_loading(self):
        self.set_similar_message("Cargando…")

    def clear_similar(self):
        self._clear_similar()

    def set_similar(self, related, thumbnails):
        self._clear_similar()
        sections = []
        if related.get("songs"):
            songs = CompactSection("Esto también te va a gustar", related["songs"], thumbnails,
                                   columns=1, rows=4, play_all=False, peek=36, title_px=16)
            songs.item_clicked.connect(self.similar_item_chosen)
            songs.add_next_clicked.connect(self.similar_add_next)
            songs.add_queue_clicked.connect(self.similar_add_queue)
            songs.add_playlist_clicked.connect(self.similar_add_playlist)
            songs.item_hovered.connect(self.similar_item_hovered)
            sections.append(songs)
        for key, title, size in (("playlists", "Playlists para ti", 150), ("artists", "Artistas similares", 130)):
            if related.get(key):
                cards = CardsSection(title, related[key], thumbnails, card_size=size, title_px=16)
                cards.item_clicked.connect(self.similar_item_chosen)
                cards.collection_action_requested.connect(self.similar_collection_action)
                sections.append(cards)
        if not sections:
            self.set_similar_message("No hay contenido similar para esta canción.")
            return
        for position, section in enumerate(sections):
            self._similar_layout.insertWidget(position, section)
            section.show()
        self._similar_scroll.verticalScrollBar().setValue(0)
