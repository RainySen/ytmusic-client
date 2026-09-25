from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ui import theme


# chips filtros
class Chip(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet(theme.chip_qss(False))

    def setChecked(self, checked):
        super().setChecked(checked)
        self.setStyleSheet(theme.chip_qss(checked))
