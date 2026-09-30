from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ui import theme


def icon_button(icon: str, size: int = 36, tooltip: str = "", checkable: bool = False) -> QPushButton:
    button = QPushButton()
    button.setIcon(qta.icon(icon, color=theme.TEXT))
    button.setFixedSize(size, size)
    button.setCursor(Qt.PointingHandCursor)
    button.setCheckable(checkable)
    if tooltip:
        button.setToolTip(tooltip)
    button.setStyleSheet(f"""
        QPushButton {{ background: rgba(255,255,255,0.10); border: none; border-radius: {size // 2}px; }}
        QPushButton:hover {{ background: rgba(255,255,255,0.20); }}
        QPushButton:checked {{ background: rgba(62,166,255,0.22); }}
    """)
    return button
