from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QToolButton, QWidget

from ui.components.playlist_rail import PlaylistRail

COLLAPSED_WIDTH = 90
EXPANDED_WIDTH = 240
COLLAPSED_BTN = QSize(74, 62)
EXPANDED_BTN = QSize(216, 44)
ICON_PX = 22
INLINE_ICON_GAP = 12


# QToolButton has no icon-text spacing: pad the icon
def _spaced_icon(icon: QIcon, size: int, gap: int) -> QIcon:
    pixmap = QPixmap(size + gap, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.drawPixmap(0, 0, icon.pixmap(size, size))
    painter.end()
    return QIcon(pixmap)

_ACTIVE_STACKED = """
    QToolButton {
        background: rgba(255,255,255,0.12);
        color: white;
        border: none;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 700;
        padding-top: 6px;
    }
"""
_INACTIVE_STACKED = """
    QToolButton {
        background: transparent;
        color: #aaa;
        border: none;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 500;
        padding-top: 6px;
    }
    QToolButton:hover {
        background: rgba(255,255,255,0.08);
        color: #e0e0e0;
    }
"""
_ACTIVE_INLINE = """
    QToolButton {
        background: rgba(255,255,255,0.12);
        color: white;
        border: none;
        border-radius: 10px;
        font-size: 15px;
        font-weight: 700;
        padding-left: 14px;
        text-align: left;
    }
"""
_INACTIVE_INLINE = """
    QToolButton {
        background: transparent;
        color: #aaa;
        border: none;
        border-radius: 10px;
        font-size: 15px;
        font-weight: 500;
        padding-left: 14px;
        text-align: left;
    }
    QToolButton:hover {
        background: rgba(255,255,255,0.08);
        color: #e0e0e0;
    }
"""


class Sidebar(QWidget):
    home_requested    = Signal()
    explore_requested = Signal()
    library_requested = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self.setObjectName("sidebar")
        self.setFixedWidth(COLLAPSED_WIDTH)
        self._expanded = False
        self._active = "Inicio"

        self._nav_layout = layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 20, 8, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self.nav_buttons = {}
        self._nav_icons = {}
        for label, icon_key, signal in [
            ("Inicio",    "home",    self.home_requested),
            ("Explorar",  "explore", self.explore_requested),
            ("Biblioteca","library", self.library_requested),
        ]:
            btn = QToolButton()
            btn.setText(label)
            btn.setIcon(icons[icon_key])
            btn.setIconSize(QSize(ICON_PX, ICON_PX))
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setFixedSize(COLLAPSED_BTN)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn, alignment=Qt.AlignHCenter)
            self.nav_buttons[label] = btn
            self._nav_icons[label] = icons[icon_key]

        self.rail = PlaylistRail()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        scroll.setWidget(self.rail)
        scroll.hide()
        self._rail_scroll = scroll
        layout.addWidget(scroll, stretch=1)

        self.set_active("Inicio")

    def set_active(self, name: str):
        self._active = name
        active_qss = _ACTIVE_INLINE if self._expanded else _ACTIVE_STACKED
        inactive_qss = _INACTIVE_INLINE if self._expanded else _INACTIVE_STACKED
        for btn_name, btn in self.nav_buttons.items():
            btn.setStyleSheet(active_qss if btn_name == name else inactive_qss)

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.setFixedWidth(EXPANDED_WIDTH if expanded else COLLAPSED_WIDTH)
        self._rail_scroll.setVisible(expanded)
        style = Qt.ToolButtonTextBesideIcon if expanded else Qt.ToolButtonTextUnderIcon
        size = EXPANDED_BTN if expanded else COLLAPSED_BTN
        alignment = Qt.AlignLeft | Qt.AlignVCenter if expanded else Qt.AlignHCenter
        for name, btn in self.nav_buttons.items():
            btn.setToolButtonStyle(style)
            btn.setFixedSize(size)
            btn.setIcon(_spaced_icon(self._nav_icons[name], ICON_PX, INLINE_ICON_GAP) if expanded
                       else self._nav_icons[name])
            self._nav_layout.setAlignment(btn, alignment)
        self.set_active(self._active)

    def set_playlists(self, playlists, thumbnails) -> None:
        self.rail.set_playlists(playlists, thumbnails)

    def release_rail(self) -> None:
        if not self._expanded:
            self.rail.set_playlists([], None)
