from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel
import qtawesome as qta


class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QWidget()
        header.setObjectName("section_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)

        self.toggle_button = QToolButton()
        self.toggle_button.setIcon(qta.icon('fa5s.chevron-down', color='white'))
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.clicked.connect(self.toggle)
        self.toggle_button.setStyleSheet("border: none; background: transparent;")

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")

        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(header)
        layout.addWidget(self.content)

    def toggle(self):
        self.is_collapsed = not self.is_collapsed
        self.content.setVisible(not self.is_collapsed)
        icon = 'fa5s.chevron-right' if self.is_collapsed else 'fa5s.chevron-down'
        self.toggle_button.setIcon(qta.icon(icon, color='white'))

    def add_content(self, widget):
        self.content_layout.addWidget(widget)
