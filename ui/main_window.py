from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QSlider
)
from PySide6.QtCore import Qt

class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_toggle_play, on_volume_change):
        super().__init__()

        self.on_search = on_search
        self.on_select_song = on_select_song
        self.on_toggle_play = on_toggle_play
        self.on_volume_change = on_volume_change

        self.setWindowTitle("YTMusic Minimal Client")

        # Búsqueda
        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("Buscar canción...")

        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.search_clicked)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.song_selected)

        # --- Mini Reproductor ---
        self.song_label = QLabel("Sin reproducción")
        self.play_button = QPushButton("⏯️")
        self.play_button.clicked.connect(self.toggle_play_clicked)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.volume_changed)

        player_layout = QHBoxLayout()
        player_layout.addWidget(self.song_label)
        player_layout.addWidget(self.play_button)
        player_layout.addWidget(self.volume_slider)

        # Layout general
        layout = QVBoxLayout(self)
        layout.addWidget(self.search_box)
        layout.addWidget(self.search_button)
        layout.addWidget(self.results_list)
        layout.addLayout(player_layout)

    # Métodos UI
    def search_clicked(self):
        text = self.search_box.text()
        if text:
            self.on_search(text)

    def update_results(self, results):
        self.results_list.clear()
        for r in results:
            self.results_list.addItem(f"{r['title']} - {r['artists'][0]['name']}")

    def song_selected(self):
        index = self.results_list.currentRow()
        self.on_select_song(index)

    def update_song_info(self, text):
        self.song_label.setText(text)

    def toggle_play_clicked(self):
        self.on_toggle_play()

    def volume_changed(self, value):
        self.on_volume_change(value)
