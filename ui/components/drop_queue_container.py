from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget


class DroppableQueueContainer(QWidget):
    item_dropped = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.drag_source_index = -1
        self.drop_indicator_pos = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            pos = event.position().toPoint()
            self.drop_indicator_pos = self._get_drop_position(pos)
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop_indicator_pos = -1
        self.update()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            try:
                source_index = int(event.mimeData().text())
                target_index = self._get_drop_position(event.position().toPoint())

                if source_index != target_index and target_index >= 0:
                    self.item_dropped.emit(source_index, target_index)

                event.acceptProposedAction()
            except ValueError:
                pass

        self.drop_indicator_pos = -1
        self.update()

    def _get_drop_position(self, pos):
        layout = self.layout()
        if not layout:
            return -1

        count = layout.count() - 1

        for i in range(count):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget_rect = widget.geometry()

                if widget_rect.contains(pos):
                    mid_point = widget_rect.top() + widget_rect.height() // 2
                    if pos.y() < mid_point:
                        return i
                    else:
                        return i + 1

        return count

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.drop_indicator_pos >= 0:
            from PySide6.QtGui import QPainter, QPen
            painter = QPainter(self)
            pen = QPen(Qt.red, 2)
            painter.setPen(pen)

            layout = self.layout()
            if layout:
                count = layout.count() - 1

                if self.drop_indicator_pos < count:
                    item = layout.itemAt(self.drop_indicator_pos)
                    if item and item.widget():
                        y = item.widget().geometry().top()
                        painter.drawLine(0, y, self.width(), y)
                elif count > 0:
                    item = layout.itemAt(count - 1)
                    if item and item.widget():
                        y = item.widget().geometry().bottom()
                        painter.drawLine(0, y, self.width(), y)
