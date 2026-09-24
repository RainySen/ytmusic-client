from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(0)

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(0)
        return hint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        text = self.fontMetrics().elidedText(self.text(), Qt.ElideRight, self.width())
        painter.setFont(self.font())
        painter.drawText(self.rect(), int(self.alignment()) | Qt.AlignVCenter, text)
        painter.end()
