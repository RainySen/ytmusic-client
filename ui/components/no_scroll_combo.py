from __future__ import annotations

from PySide6.QtWidgets import QComboBox


# ignore wheel unless open, avoids accidental changes
class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()
