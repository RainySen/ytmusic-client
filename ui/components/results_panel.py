from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.search_info = QLabel("Resultados de Búsqueda")
        self.search_info.setObjectName("search_info")
        self.search_info.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.results_list = QListWidget()
        self.results_list.setObjectName("results_list")
        self.results_list.setSpacing(8)

        layout.addWidget(self.search_info)
        layout.addWidget(self.results_list)
