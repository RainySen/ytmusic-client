from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QSlider, QSplitter, QMenu,
    QInputDialog, QSystemTrayIcon, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction
import qtawesome as qta


class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_add_to_queue, on_toggle_play,
                 on_volume_change, on_seek, on_next, on_previous, on_remove_from_queue,
                 on_queue_item_selected, on_import_playlist, app_icon):
        super().__init__()

        self.on_search = on_search
        self.on_select_song = on_select_song
        self.on_add_to_queue = on_add_to_queue
        self.on_toggle_play = on_toggle_play
        self.on_volume_change = on_volume_change
        self.on_seek = on_seek
        self.on_next = on_next
        self.on_previous = on_previous
        self.on_remove_from_queue = on_remove_from_queue
        self.on_queue_item_selected = on_queue_item_selected
        self.on_import_playlist = on_import_playlist

        self.app_icon = app_icon
        self.setWindowIcon(self.app_icon)

        self.setWindowTitle("YTMusic Minimal Client")

        # Definir iconos
        self.icon_play = qta.icon('fa5s.play', color='white')
        self.icon_pause = qta.icon('fa5s.pause', color='white')
        self.icon_next = qta.icon('fa5s.step-forward', color='white')
        self.icon_prev = qta.icon('fa5s.step-backward', color='white')
        self.icon_search = qta.icon('fa5s.search', color='white')
        self.icon_volume = qta.icon('fa5s.volume-up', color='white')
        self.icon_trash = qta.icon('fa5s.trash', color='white')
        self.icon_clear = qta.icon('fa5s.broom', color='white')
        self.icon_clear = qta.icon('fa5s.broom', color='white')
        self.icon_import = qta.icon('fa5s.file-import', color='white')

        # Layout principal
        main_layout = QVBoxLayout(self)

        # Splitter horizontal (búsqueda | cola)
        splitter = QSplitter(Qt.Horizontal)

        # --- Panel izquierdo: Búsqueda ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        search_title = QLabel("<b>Búsqueda</b>")
        search_title.setStyleSheet("font-size: 14px;")
        left_layout.addWidget(search_title)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar canción, artista, álbum...")
        self.search_box.returnPressed.connect(self.search_clicked)

        self.search_button = QPushButton()
        self.search_button.setIcon(self.icon_search)
        self.search_button.setText(" Buscar")
        self.search_button.clicked.connect(self.search_clicked)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
        """)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.song_selected)
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #181818;
                color: white;
                border: 1px solid #282828;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #282828;
            }
            QListWidget::item:selected {
                background-color: #1DB954;
            }
        """)

        # Habilitar menú contextual
        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_results_context_menu)

        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.search_button)
        left_layout.addWidget(self.results_list)

        # --- Panel derecho: Cola ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        queue_title = QLabel("<b>Cola de reproducción</b>")
        queue_title.setStyleSheet("font-size: 14px;")
        right_layout.addWidget(queue_title)

        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet("""
            QListWidget {
                background-color: #181818;
                color: white;
                border: 1px solid #282828;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #282828;
            }
        """)

        # Habilitar doble click en la cola
        self.queue_list.itemDoubleClicked.connect(self.queue_item_selected)

        queue_buttons = QHBoxLayout()
        self.import_btn = QPushButton()
        self.import_btn.setIcon(self.icon_import)
        self.import_btn.setText(" Importar URL")
        self.import_btn.clicked.connect(self.import_playlist_clicked)
        self.import_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #0099ff;
                    }
                """)

        self.remove_btn = QPushButton()
        self.remove_btn.setIcon(self.icon_trash)
        self.remove_btn.setText(" Eliminar")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
        """)

        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(self.icon_clear)
        self.clear_btn.setText(" Limpiar todo")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff8800;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ffaa00;
            }
        """)

        queue_buttons.addWidget(self.import_btn)
        queue_buttons.addWidget(self.remove_btn)
        queue_buttons.addWidget(self.clear_btn)

        right_layout.addWidget(self.queue_list)
        right_layout.addLayout(queue_buttons)

        # Agregar paneles al splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, stretch=1)

        # --- Reproductor (parte inferior) ---
        player_widget = QWidget()
        player_widget.setStyleSheet("""
            QWidget {
                background-color: #282828;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        player_layout = QVBoxLayout(player_widget)

        self.song_label = QLabel("Sin reproducción")
        self.song_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")

        # Barra de progreso
        progress_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet("color: #b3b3b3; font-size: 11px;")

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #404040;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 2px;
            }
        """)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #b3b3b3; font-size: 11px;")

        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time_label)

        # Controles
        controls_layout = QHBoxLayout()

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.icon_prev)
        self.prev_button.clicked.connect(self.previous_clicked)
        self.prev_button.setFixedSize(40, 40)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #535353;
            }
        """)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icon_play)
        self.play_button.clicked.connect(self.toggle_play_clicked)
        self.play_button.setFixedSize(50, 50)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #1ed760;
                transform: scale(1.05);
            }
        """)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icon_next)
        self.next_button.clicked.connect(self.next_clicked)
        self.next_button.setFixedSize(40, 40)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #535353;
            }
        """)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #404040;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: white;
                border-radius: 2px;
            }
        """)

        volume_icon = QLabel()
        volume_icon.setPixmap(self.icon_volume.pixmap(20, 20))

        controls_layout.addStretch()
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.next_button)
        controls_layout.addStretch()
        controls_layout.addWidget(volume_icon)
        controls_layout.addWidget(self.volume_slider)

        player_layout.addWidget(self.song_label)
        player_layout.addLayout(progress_layout)
        player_layout.addLayout(controls_layout)

        main_layout.addWidget(player_widget)

        self.init_tray_icon()

        # Estilo general de la ventana
        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
                font-family: 'Segoe UI', Arial;
            }
            QLineEdit {
                background-color: #282828;
                color: white;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #1DB954;
            }
            QLabel {
                color: white;
            }
        """)

    # Métodos UI
    def search_clicked(self):
        text = self.search_box.text()
        if text:
            self.on_search(text)

    def update_results(self, results):
        self.results_list.clear()
        for r in results:
            artist = r['artists'][0]['name'] if r.get('artists') else 'Desconocido'
            self.results_list.addItem(f" {r['title']} - {artist}")

    def song_selected(self):
        index = self.results_list.currentRow()
        self.on_select_song(index)

    def update_song_info(self, text):
        self.song_label.setText(f" {text}")

    def toggle_play_clicked(self):
        self.on_toggle_play()

    def update_play_button_icon(self, is_playing):
        if is_playing:
            self.play_button.setIcon(self.icon_pause)
            if hasattr(self, 'play_pause_action'):
                self.play_pause_action.setText(" Pausar")
        else:
            self.play_button.setIcon(self.icon_play)
            if hasattr(self, 'play_pause_action'):
                self.play_pause_action.setText(" Reproducir")

    def volume_changed(self, value):
        self.on_volume_change(value)

    def seek_position(self, value):
        position = value / 1000.0
        self.on_seek(position)

    def update_progress(self, position):
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(int(position * 1000))
        self.progress_slider.blockSignals(False)

    def update_time(self, current, total):
        self.time_label.setText(self._format_time(current))
        self.total_time_label.setText(self._format_time(total))

    def _format_time(self, seconds):
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    def next_clicked(self):
        self.on_next()

    def previous_clicked(self):
        self.on_previous()

    def update_queue(self, queue, current_index):
        self.queue_list.clear()
        for i, song in enumerate(queue):
            prefix = "▶ " if i == current_index else "   "
            artist = song['artists'][0]['name'] if song.get('artists') else 'Desconocido'
            self.queue_list.addItem(f"{prefix}{song['title']} - {artist}")

    def import_playlist_clicked(self):
        url, ok = QInputDialog.getText(self,
                                       "Importar Playlist",
                                       "Pega la URL de la playlist de YouTube/YTMusic:")

        if ok and url:
            self.on_import_playlist(url)

    def remove_selected(self):
        index = self.queue_list.currentRow()
        if index >= 0:
            self.on_remove_from_queue(index)

    def queue_item_selected(self):
        index = self.queue_list.currentRow()
        if index >= 0:
            self.on_queue_item_selected(index)

    def show_results_context_menu(self, position):
        item = self.results_list.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #282828;
                color: white;
                border: 1px solid #404040;
            }
            QMenu::item:selected {
                background-color: #1DB954;
            }
        """)

        play_now_action = menu.addAction(qta.icon('fa5s.play', color='white'), " Reproducir ahora")
        add_queue_action = menu.addAction(qta.icon('fa5s.plus', color='white'), " Agregar a la cola")

        action = menu.exec(self.results_list.mapToGlobal(position))

        if action == play_now_action:
            self.song_selected()
        elif action == add_queue_action:
            index = self.results_list.currentRow()
            self.on_add_to_queue(index)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("YTMusic Minimal Client")

        tray_menu = QMenu(self)

        show_action = QAction("Mostrar Aplicación", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        self.play_pause_action = QAction(" Reproducir", self)
        self.play_pause_action.triggered.connect(self.on_toggle_play)
        tray_menu.addAction(self.play_pause_action)

        prev_action = QAction(self.icon_prev, " Anterior", self)
        prev_action.triggered.connect(self.on_previous)
        tray_menu.addAction(prev_action)

        next_action = QAction(self.icon_next, " Siguiente", self)
        next_action.triggered.connect(self.on_next)
        tray_menu.addAction(next_action)

        tray_menu.addSeparator()

        quit_action = QAction("Salir", self)
        quit_action.triggered.connect(QApplication.instance().quit)  # Cierra la app de verdad
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        # Mostrar la ventana con un clic izquierdo normal
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()

    def closeEvent(self, event):
        # Sobreescribir el evento de cierre (clic en la 'X')
        # 1. Ignorar el evento (evita que la app se cierre)
        event.ignore()
        # 2. Ocultar la ventana
        self.hide()
        # 3. Mostrar una notificación (opcional pero recomendado)
        self.tray_icon.showMessage(
            "Aplicación minimizada",
            "El reproductor sigue activo en la bandeja del sistema.",
            QSystemTrayIcon.MessageIcon.Information,
            2000  # milisegundos
        )