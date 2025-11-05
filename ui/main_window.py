import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QSlider, QSplitter, QMenu,
    QInputDialog, QMessageBox, QSystemTrayIcon, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QKeySequence
import qtawesome as qta


class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_add_to_queue, on_toggle_play,
                 on_volume_change, on_seek, on_next, on_previous, on_remove_from_queue,
                 on_queue_item_selected, on_login_requested, on_playlist_selected, on_import_playlist, app_icon,
                 on_save_imported_playlist, on_result_highlighted):
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
        self.on_login_requested = on_login_requested
        self.on_playlist_selected = on_playlist_selected
        self.on_import_playlist = on_import_playlist
        self.on_save_imported_playlist = on_save_imported_playlist
        self.on_result_highlighted = on_result_highlighted

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
        self.icon_login = qta.icon('mdi.account-circle', color='white')
        self.icon_import = qta.icon('fa5s.file-import', color='white')

        # Layout principal
        main_layout = QVBoxLayout(self)

        # Splitter horizontal (búsqueda | playlists + cola)
        splitter = QSplitter(Qt.Horizontal)

        # --- Panel izquierdo: Búsqueda ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        search_header_layout = QHBoxLayout()
        search_title = QLabel("<b>Búsqueda</b>")
        search_title.setStyleSheet("font-size: 14px;")
        search_header_layout.addWidget(search_title)
        search_header_layout.addStretch()

        self.login_button = QPushButton()
        self.login_button.setIcon(self.icon_login)
        self.login_button.setToolTip("Iniciar Sesión para ver tus playlists")
        self.login_button.setFixedSize(32, 32)
        self.login_button.clicked.connect(self.login_clicked)
        self.login_button.setStyleSheet("QPushButton { border: none; background-color: transparent; }")
        search_header_layout.addWidget(self.login_button)

        left_layout.addLayout(search_header_layout)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar canción, artista, álbum...")
        self.search_box.returnPressed.connect(self.search_clicked)

        self.search_button = QPushButton()
        self.search_button.setIcon(self.icon_search)
        self.search_button.setText(" Buscar")
        self.search_button.clicked.connect(self.search_clicked)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #03adb7;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00dfe5;
            }
        """)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.play_selected_song_now)
        self.results_list.currentItemChanged.connect(self.result_highlighted)
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #0a1415;
                color: white;
                border: 1px solid #1a2728;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #1a2728;
            }
            QListWidget::item:selected {
                background-color: #03adb7;
            }
        """)

        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_results_context_menu)

        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.search_button)
        left_layout.addWidget(self.results_list)

        # --- Panel derecho: Playlists + Cola (vertical split) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter vertical para Playlists y Cola
        vertical_splitter = QSplitter(Qt.Vertical)

        # --- Sección de Playlists (arriba) ---
        playlists_panel = QWidget()
        playlists_layout = QVBoxLayout(playlists_panel)

        playlists_title = QLabel("<b>Mis Playlists</b>")
        playlists_title.setStyleSheet("font-size: 14px;")

        self.playlists_list = QListWidget()
        self.playlists_list.itemDoubleClicked.connect(self.playlist_selected)
        self.playlists_list.setStyleSheet("""
            QListWidget {
                background-color: #0a1415;
                color: white;
                border: 1px solid #1a2728;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #1a2728;
            }
            QListWidget::item:selected {
                background-color: #03adb7;
            }
        """)

        playlists_layout.addWidget(playlists_title)
        playlists_layout.addWidget(self.playlists_list)

        # --- Sección de Cola (abajo) ---
        queue_panel = QWidget()
        queue_layout = QVBoxLayout(queue_panel)

        queue_title = QLabel("<b>Cola de reproducción</b>")
        queue_title.setStyleSheet("font-size: 14px;")

        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet("""
            QListWidget {
                background-color: #0a1415;
                color: white;
                border: 1px solid #1a2728;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #1a2728;
            }
        """)

        self.queue_list.itemDoubleClicked.connect(self.queue_item_selected)
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.show_queue_context_menu)

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

        self.clear_btn = QPushButton()
        self.clear_btn.setIcon(self.icon_clear)
        self.clear_btn.setText(" Limpiar todo")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e1732e;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e68c48;
            }
        """)

        queue_buttons.addWidget(self.import_btn)
        queue_buttons.addWidget(self.clear_btn)

        queue_layout.addWidget(queue_title)
        queue_layout.addWidget(self.queue_list)
        queue_layout.addLayout(queue_buttons)

        # Agregar paneles al splitter vertical
        vertical_splitter.addWidget(playlists_panel)
        vertical_splitter.addWidget(queue_panel)
        vertical_splitter.setStretchFactor(0, 1)
        vertical_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(vertical_splitter)

        # Agregar paneles al splitter horizontal
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, stretch=1)

        # --- Reproductor (parte inferior) ---
        player_widget = QWidget()
        player_widget.setStyleSheet("""
            QWidget {
                background-color: #0f1b1c;
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
                background: #1a2728;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #03adb7;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #03adb7;
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
                background-color: #1a2728;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #2a3738;
            }
        """)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icon_play)
        self.play_button.clicked.connect(self.toggle_play_clicked)
        self.play_button.setFixedSize(50, 50)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #03adb7;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #00dfe5;
                transform: scale(1.05);
            }
        """)

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icon_next)
        self.next_button.clicked.connect(self.next_clicked)
        self.next_button.setFixedSize(40, 40)
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #1a2728;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #2a3738;
            }
        """)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #1a2728;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #03adb7;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #03adb7;
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

        self.setup_quit_shortcut()

        self.init_tray_icon()

        # Estilo general de la ventana
        self.setStyleSheet("""
            QWidget {
                background-color: #060d0e;
                color: white;
                font-family: 'Segoe UI', Arial;
            }
            QLineEdit {
                background-color: #0f1b1c;
                color: white;
                border: 1px solid #1a2728;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #03adb7;
            }
            QLabel {
                color: white;
            }
        """)

    def setup_quit_shortcut(self):
        """Crea una acción invisible que cierra la app con Ctrl+Q."""
        quit_action = QAction("Salir", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.setToolTip("Cierra la aplicación completamente")
        # Conecta la acción directamente al 'quit' de la aplicación
        quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

    def login_clicked(self):
        # ... (el resto del archivo no cambia) ...
        instructions = """
            Para iniciar sesión, sigue estos pasos con atención:

            1. Abre YouTube Music en tu navegador (Chrome, Firefox, Opera).
            2. **IMPORTANTE: Asegúrate de haber iniciado sesión con tu cuenta.**
            3. Abre las herramientas de desarrollador (con F12).
            4. Ve a la pestaña "Red" (o "Network").
            5. **IMPORTANTE: Haz una recarga forzada de la página (Ctrl + Shift + R)** para evitar la caché.
            6. En el filtro, escribe `browse` para encontrar la petición correcta.
            7. Busca la petición a `music.youtube.com/youtubei...`, haz clic derecho sobre ella.
            8. Ve a "Copiar" -> "Copiar como cURL (bash)".
            9. Pega el texto completo en el campo de abajo.
        """

        text, ok = QInputDialog.getMultiLineText(self, 'Iniciar Sesión - Obtener Credenciales', instructions, text="")

        if ok and text:
            headers_list = []

            h_matches = re.findall(r"-H\s+'([^']*)'", text)
            if h_matches:
                headers_list.extend(h_matches)

            cookie_match = re.search(r"(--cookie|-b)\s+'([^']*)'", text)
            if cookie_match:
                cookie_data = cookie_match.group(2)
                headers_list.append(f"Cookie: {cookie_data}")

            headers_raw = "\n".join(headers_list)

            self.on_login_requested(headers_raw)

    def update_playlists(self, playlists):
        self.playlists_list.clear()
        if not playlists:
            self.playlists_list.addItem("Inicia sesión para ver tus playlists")
            return

        for p in playlists:
            self.playlists_list.addItem(f" {p['title']}")

    def playlist_selected(self):
        index = self.playlists_list.currentRow()
        self.on_playlist_selected(index)

    def show_auth_success(self):
        QMessageBox.information(self, "Éxito", "¡Inicio de sesión completado! Tus playlists se han cargado.")

    def show_auth_error(self):
        QMessageBox.warning(self, "Error",
                            "No se pudo completar el inicio de sesión. Por favor, verifica las cabeceras e inténtalo de nuevo.")

    def search_clicked(self):
        text = self.search_box.text()
        if text:
            self.on_search(text)

    def result_highlighted(self, current, previous):
        """
        Se llama cuando el usuario selecciona (con un clic) un ítem
        en la lista de resultados.
        """
        index = self.results_list.currentRow()
        if self.on_result_highlighted and index >= 0:
            self.on_result_highlighted(index)

    def update_results(self, results):
        self.results_list.clear()
        for r in results:
            artist = r['artists'][0]['name'] if r.get('artists') else 'Desconocido'
            self.results_list.addItem(f"♪ {r['title']} - {artist}")

    def play_selected_song_now(self):
        """
        Esta función se encarga de reproducir la canción seleccionada
        en la lista de resultados, ya sea por doble clic o por menú contextual.
        """
        index = self.results_list.currentRow()
        if index >= 0:
            self.on_select_song(index)

    def update_song_info(self, text):
        self.song_label.setText(f"♪ {text}")

    def toggle_play_clicked(self):
        self.on_toggle_play()

    def update_play_button_icon(self, is_playing):
        if is_playing:
            self.play_button.setIcon(self.icon_pause)
            if hasattr(self, 'play_pause_action'):
                self.play_pause_action.setText("⏸ Pausar")
        else:
            self.play_button.setIcon(self.icon_play)
            if hasattr(self, 'play_pause_action'):
                self.play_pause_action.setText("▶ Reproducir")

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

    def show_queue_context_menu(self, position):
        item = self.queue_list.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f1b1c;
                color: white;
                border: 1px solid #1a2728;
            }
            QMenu::item:selected {
                background-color: #ff4444;
            }
        """)

        delete_action = menu.addAction(self.icon_trash, " Eliminar de la cola")
        action = menu.exec(self.queue_list.mapToGlobal(position))

        if action == delete_action:
            self.remove_selected()

    def show_results_context_menu(self, position):
        item = self.results_list.itemAt(position)
        if item is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f1b1c;
                color: white;
                border: 1px solid #1a2728;
            }
            QMenu::item:selected {
                background-color: #03adb7;
            }
        """)

        play_now_action = menu.addAction(qta.icon('fa5s.play', color='white'), " Reproducir ahora")
        add_queue_action = menu.addAction(qta.icon('fa5s.plus', color='white'), " Agregar a la cola")

        action = menu.exec(self.results_list.mapToGlobal(position))

        if action == play_now_action:
            self.play_selected_song_now()
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

        quit_action = QAction("Salir (o Ctrl+Q)", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Aplicación minimizada",
            "El reproductor sigue activo en la bandeja del sistema.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def ask_to_save_playlist(self, title):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Guardar Playlist")
        msg_box.setText(f"¿Quieres guardar '{title}' en tu biblioteca 'Mis Playlists'?")
        msg_box.setInformativeText("Esto creará una nueva playlist en tu cuenta (requiere inicio de sesión).")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        msg_box.setIcon(QMessageBox.Question)

        if msg_box.exec() == QMessageBox.Yes:
            self.on_save_imported_playlist()

    def show_save_playlist_success(self, title):
        QMessageBox.information(self, "Éxito", f"La playlist '{title}' se ha guardado en tu biblioteca.")

    def show_save_playlist_error(self, title):
        QMessageBox.warning(self, "Error", f"No se pudo guardar la playlist '{title}'.")