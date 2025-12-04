import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QSlider, QSplitter, QMenu,
    QInputDialog, QMessageBox, QSystemTrayIcon, QApplication,
    QTabWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QKeySequence
import qtawesome as qta


class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_add_to_queue, on_toggle_play, on_add_next,
                 on_volume_change, on_seek, on_next, on_previous, on_remove_from_queue,
                 on_queue_item_selected, on_login_requested, on_playlist_selected, on_import_playlist, app_icon,
                 on_save_imported_playlist, on_result_highlighted, on_queue_item_moved, on_toggle_loop,
                 on_logout_requested, on_toggle_autoplay, on_show_lyrics_requested):
        super().__init__()

        self.on_search = on_search
        self.on_select_song = on_select_song
        self.on_add_to_queue = on_add_to_queue
        self.on_add_next = on_add_next
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
        self.on_queue_item_moved = on_queue_item_moved
        self.on_toggle_loop = on_toggle_loop
        self.on_logout_requested = on_logout_requested
        self.on_toggle_autoplay = on_toggle_autoplay
        self.on_show_lyrics_requested = on_show_lyrics_requested

        self.is_logged_in = False
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
        self.icon_login = qta.icon('fa5s.user-circle', color='white')
        self.icon_login_active = qta.icon('fa5s.user-circle', color='#03adb7')
        self.icon_import = qta.icon('fa5s.file-import', color='white')
        self.icon_loop_off = qta.icon('fa5s.sync-alt', color='gray')
        self.icon_loop_queue = qta.icon('fa5s.sync-alt', color='#03adb7')
        self.icon_loop_song = qta.icon('fa5s.redo', color='#03adb7')
        self.icon_autoplay_off = qta.icon('fa5s.magic', color='gray')
        self.icon_autoplay_on = qta.icon('fa5s.magic', color='#03adb7')
        self.icon_lyrics = qta.icon('fa5s.microphone-alt', color='white')

        # Layout principal
        main_layout = QVBoxLayout(self)
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
        self.login_button.setToolTip("Iniciar Sesión")
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
        self.search_button.setStyleSheet(
            "QPushButton { background-color: #03adb7; color: white; border: none; padding: 8px; border-radius: 4px; font-weight: bold; } QPushButton:hover { background-color: #00dfe5; }")

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.play_selected_song_now)
        self.results_list.currentItemChanged.connect(self.result_highlighted)
        self.results_list.setStyleSheet("""
            QListWidget { background-color: #0a1415; color: white; border-radius: 4px; } 
            QListWidget::item { padding: 8px; } 
            QListWidget::item:hover { background-color: #1a2728; outline: none; } 
            QListWidget::item:selected:active { background-color: #03adb7; outline: none; }
        """)
        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_results_context_menu)

        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.search_button)
        left_layout.addWidget(self.results_list)

        # --- Panel derecho con Pestañas ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.right_tabs = QTabWidget()
        right_layout.addWidget(self.right_tabs)

        # Tab 1: Playlist/Cola
        self.playlists_queue_tab = QWidget()
        pq_layout = QVBoxLayout(self.playlists_queue_tab)
        pq_layout.setContentsMargins(0, 0, 0, 0)
        vertical_splitter = QSplitter(Qt.Vertical)
        pq_layout.addWidget(vertical_splitter)

        playlists_panel = QWidget()
        p_layout = QVBoxLayout(playlists_panel)
        p_title = QLabel("<b>Mis Playlists</b>")
        p_title.setStyleSheet("font-size: 14px;")
        self.playlists_list = QListWidget()
        self.playlists_list.itemDoubleClicked.connect(self.playlist_selected)
        self.playlists_list.setStyleSheet("""
            QListWidget { background-color: #0a1415; color: white; border: 1px solid #1a2728; border-radius: 4px; } 
            QListWidget::item { padding: 8px; } 
            QListWidget::item:hover { background-color: #1a2728; outline: none; } 
            QListWidget::item:selected { background-color: #03adb7; outline: none; }
        """)
        p_layout.addWidget(p_title)
        p_layout.addWidget(self.playlists_list)

        queue_panel = QWidget()
        q_layout = QVBoxLayout(queue_panel)
        q_title = QLabel("<b>Cola de reproducción</b>")
        q_title.setStyleSheet("font-size: 14px;")
        self.queue_list = QListWidget()
        self.queue_list.setDragEnabled(True)
        self.queue_list.setAcceptDrops(True)
        self.queue_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.queue_list.model().rowsMoved.connect(self.queue_item_moved)
        self.queue_list.setStyleSheet("""
            QListWidget { background-color: #0a1415; color: white; border: 1px solid #1a2728; border-radius: 4px; selection-background-color: #1a2728; } 
            QListWidget::item { padding: 8px; } 
            QListWidget::item:hover { background-color: #1a2728; outline: none; } 
            QListWidget::item:selected:active { background-color: #1a2728; color: white; border-left: 3px solid #03adb7; padding-left: 5px; outline: none; } 
            QListWidget::item:selected:!active { background-color: #1a2728; color: white; border-left: 3px solid #03adb7; padding-left: 5px; outline: none; }
        """)
        self.queue_list.itemDoubleClicked.connect(self.queue_item_selected)
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.show_queue_context_menu)

        q_btns = QHBoxLayout()
        self.import_btn = QPushButton(" Importar URL")
        self.import_btn.setIcon(self.icon_import)
        self.import_btn.clicked.connect(self.import_playlist_clicked)
        self.import_btn.setStyleSheet(
            "QPushButton { background-color: #007bff; color: white; border: none; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background-color: #0099ff; }")
        self.clear_btn = QPushButton(" Limpiar todo")
        self.clear_btn.setIcon(self.icon_clear)
        self.clear_btn.clicked.connect(lambda: self.on_remove_from_queue(-1))
        self.clear_btn.setStyleSheet(
            "QPushButton { background-color: #e1732e; color: white; border: none; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background-color: #e68c48; }")
        q_btns.addWidget(self.import_btn)
        q_btns.addWidget(self.clear_btn)

        q_layout.addWidget(q_title)
        q_layout.addWidget(self.queue_list)
        q_layout.addLayout(q_btns)

        vertical_splitter.addWidget(playlists_panel)
        vertical_splitter.addWidget(queue_panel)
        vertical_splitter.setStretchFactor(0, 1)
        vertical_splitter.setStretchFactor(1, 1)

        # Tab 2: Letra (Karaoke)
        self.lyrics_tab = QWidget()
        lyrics_layout = QVBoxLayout(self.lyrics_tab)

        # Usamos QListWidget para controlar cada línea
        self.lyrics_list_widget = QListWidget()

        # === ESTILO KARAOKE ===
        self.lyrics_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #0a1415;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                color: #666666; /* Gris oscuro para líneas pasadas o futuras */
                font-size: 14px;
                text-align: center;
            }
            /* ESTILO PARA LA LÍNEA ACTIVA (Aunque no tenga el foco) */
            QListWidget::item:selected {
                background-color: transparent;
                color: #03adb7; /* CIAN brillante */
                font-weight: bold;
                font-size: 18px; /* Más grande */
                outline: none;
            }
            QListWidget::item:selected:!active {
                background-color: transparent;
                color: #03adb7; /* Mismo color cian aunque clicques fuera */
                outline: none;
            }
            QListWidget::item:hover {
                background-color: transparent; /* Evitar que el hover cambie el color de fondo */
            }
        """)
        self.lyrics_list_widget.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.lyrics_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        lyrics_layout.addWidget(self.lyrics_list_widget)

        self.right_tabs.addTab(self.playlists_queue_tab, "Playlists")
        self.right_tabs.addTab(self.lyrics_tab, "Letra")
        self.right_tabs.setStyleSheet("""
            QTabWidget::pane { border-top: 2px solid #1a2728; }
            QTabBar::tab { background: #0f1b1c; color: #b3b3b3; padding: 10px; font-weight: bold; border: 1px solid #1a2728; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0a1415; color: white; }
            QTabBar::tab:!selected:hover { background: #1a2728; }
        """)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=1)

        # Reproductor
        player_widget = QWidget()
        player_widget.setStyleSheet("QWidget { background-color: #0f1b1c; border-radius: 8px; padding: 6px 10px; }")
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(0, 0, 0, 0)
        player_layout.setSpacing(5)

        self.song_label = QLabel("Sin reproducción")
        self.song_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")

        progress_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setStyleSheet("color: #b3b3b3; font-size: 11px;")
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.progress_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #1a2728; height: 4px; border-radius: 2px; } QSlider::handle:horizontal { background: #03adb7; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; } QSlider::sub-page:horizontal { background: #03adb7; border-radius: 2px; }")
        self.total_time_label = QLabel("0:00")
        self.total_time_label.setStyleSheet("color: #b3b3b3; font-size: 11px;")
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time_label)

        ctrl_layout = QHBoxLayout()
        self.prev_button = QPushButton();
        self.prev_button.setIcon(self.icon_prev);
        self.prev_button.clicked.connect(self.previous_clicked);
        self.prev_button.setFixedSize(40, 40);
        self.prev_button.setStyleSheet(
            "QPushButton { background-color: #1a2728; border: none; border-radius: 20px; } QPushButton:hover { background-color: #2a3738; }")
        self.play_button = QPushButton();
        self.play_button.setIcon(self.icon_play);
        self.play_button.clicked.connect(self.toggle_play_clicked);
        self.play_button.setFixedSize(50, 50);
        self.play_button.setStyleSheet(
            "QPushButton { background-color: #03adb7; border: none; border-radius: 25px; } QPushButton:hover { background-color: #00dfe5; transform: scale(1.05); }")
        self.next_button = QPushButton();
        self.next_button.setIcon(self.icon_next);
        self.next_button.clicked.connect(self.next_clicked);
        self.next_button.setFixedSize(40, 40);
        self.next_button.setStyleSheet(
            "QPushButton { background-color: #1a2728; border: none; border-radius: 20px; } QPushButton:hover { background-color: #2a3738; }")

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100);
        self.volume_slider.setValue(50);
        self.volume_slider.setMaximumWidth(100);
        self.volume_slider.valueChanged.connect(self.volume_changed)
        self.volume_slider.setStyleSheet(
            "QSlider::groove:horizontal { background: #1a2728; height: 4px; border-radius: 2px; } QSlider::handle:horizontal { background: #03adb7; width: 10px; height: 10px; margin: -3px 0; border-radius: 5px; } QSlider::sub-page:horizontal { background: #03adb7; border-radius: 2px; }")
        vol_icon = QLabel();
        vol_icon.setPixmap(self.icon_volume.pixmap(20, 20))

        self.loop_button = QPushButton();
        self.loop_button.setIcon(self.icon_loop_off);
        self.loop_button.clicked.connect(self.on_toggle_loop);
        self.loop_button.setFixedSize(30, 30);
        self.loop_button.setStyleSheet(
            "QPushButton { border: none; background-color: transparent; border-radius: 15px; } QPushButton:hover { background-color: #2a3738; }")
        self.autoplay_button = QPushButton();
        self.autoplay_button.setIcon(self.icon_autoplay_off);
        self.autoplay_button.clicked.connect(self.on_toggle_autoplay);
        self.autoplay_button.setFixedSize(30, 30);
        self.autoplay_button.setStyleSheet(
            "QPushButton { border: none; background-color: transparent; border-radius: 15px; } QPushButton:hover { background-color: #2a3738; }")

        self.lyrics_button = QPushButton()
        self.lyrics_button.setIcon(self.icon_lyrics)
        self.lyrics_button.clicked.connect(self.on_show_lyrics_requested)
        self.lyrics_button.setFixedSize(30, 30)
        self.lyrics_button.setToolTip("Mostrar Letra")
        self.lyrics_button.setStyleSheet(
            "QPushButton { border: none; background-color: transparent; border-radius: 15px; } QPushButton:hover { background-color: #2a3738; }")

        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.prev_button)
        ctrl_layout.addWidget(self.play_button)
        ctrl_layout.addWidget(self.next_button)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.lyrics_button)
        ctrl_layout.addWidget(self.loop_button)
        ctrl_layout.addWidget(self.autoplay_button)
        ctrl_layout.addWidget(vol_icon)
        ctrl_layout.addWidget(self.volume_slider)

        player_layout.addWidget(self.song_label)
        player_layout.addLayout(progress_layout)
        player_layout.addLayout(ctrl_layout)
        main_layout.addWidget(player_widget)

        self.setup_quit_shortcut()
        self.init_tray_icon()

        # Estilos generales
        self.setStyleSheet(self.styleSheet() + """
            QScrollBar:vertical { border: none; background: #0a1415; width: 8px; margin: 0px; }
            QScrollBar::handle:vertical { background: #1a2728; min-height: 20px; border-radius: 4px; }
            QScrollBar::handle:vertical:hover { background: #03adb7; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal { border: none; background: #0a1415; height: 8px; margin: 0px; }
            QScrollBar::handle:horizontal { background: #1a2728; min-width: 20px; border-radius: 4px; }
            QScrollBar::handle:horizontal:hover { background: #03adb7; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { border: none; background: none; width: 0px; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
        """)

    def setup_quit_shortcut(self):
        quit_action = QAction("Salir", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

    # --- MÉTODOS PARA LA LISTA DE LETRA ---
    def set_lyrics_lines(self, lines):
        """Recibe una lista de strings y las pone en el QListWidget"""
        self.lyrics_list_widget.clear()
        for line in lines:
            item = QListWidgetItem(line)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_list_widget.addItem(item)

        # CAMBIO: Ya NO forzamos el cambio de pestaña aquí
        # self.right_tabs.setCurrentWidget(self.lyrics_tab)

        self.lyrics_button.setIcon(qta.icon('fa5s.microphone-alt', color='#03adb7'))

    def set_lyrics_message(self, message, switch_focus=False):
        """Para mensajes de error o 'Cargando...'"""
        self.lyrics_list_widget.clear()
        item = QListWidgetItem(message)
        item.setTextAlignment(Qt.AlignCenter)
        self.lyrics_list_widget.addItem(item)

        # CAMBIO: Solo cambiamos de pestaña si se pide explícitamente
        if switch_focus:
            self.right_tabs.setCurrentWidget(self.lyrics_tab)

        self.lyrics_button.setIcon(qta.icon('fa5s.microphone-alt', color='gray'))

    def highlight_lyric_index(self, index):
        """Ilumina la fila indicada y hace scroll hacia ella"""
        if index < 0 or index >= self.lyrics_list_widget.count():
            return

        # Seleccionar la fila
        self.lyrics_list_widget.setCurrentRow(index)

        # Hacer scroll suave para que la línea quede centrada verticalmente
        item = self.lyrics_list_widget.item(index)
        self.lyrics_list_widget.scrollToItem(item, QListWidget.PositionAtCenter)

    # -------------------------------------
    # ... (El resto de métodos no cambian: login_clicked, update_playlists, etc.) ...
    def login_clicked(self):
        if self.is_logged_in:
            reply = QMessageBox.question(self, "Cerrar Sesión", "¿Estás seguro de que deseas cerrar la sesión?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.on_logout_requested: self.on_logout_requested()
        else:
            instructions = """
                Para iniciar sesión, sigue estos pasos con atención:
                1. Abre YouTube Music en tu navegador.
                2. Asegúrate de haber iniciado sesión.
                3. Abre las herramientas de desarrollador (F12).
                4. Ve a la pestaña "Red".
                5. Recarga la página (Ctrl + Shift + R).
                6. Filtra por `browse`.
                7. Clic derecho en `music.youtube.com...` -> Copiar como cURL (bash).
                8. Pega abajo.
            """
            text, ok = QInputDialog.getMultiLineText(self, 'Iniciar Sesión', instructions, text="")
            if ok and text:
                headers_list = []
                unwrapped = re.sub(r'[\^\\]\s*\n', ' ', text).replace('\n', ' ')
                h_matches = re.findall(r"-H\s+(['\"])(.*?)\1", unwrapped)
                if h_matches: headers_list.extend([m[1] for m in h_matches])
                c_match = re.search(r"(--cookie|-b)\s+(['\"])(.*?)\2", unwrapped)
                if c_match: headers_list.append(f"Cookie: {c_match.group(3)}")
                if self.on_login_requested: self.on_login_requested("\n".join(headers_list))

    def update_playlists(self, playlists):
        self.playlists_list.clear()
        if not playlists: self.playlists_list.addItem("Inicia sesión para ver tus playlists"); return
        for p in playlists: self.playlists_list.addItem(f" {p['title']}")

    def playlist_selected(self):
        self.on_playlist_selected(self.playlists_list.currentRow())

    def show_auth_success(self):
        QMessageBox.information(self, "Éxito", "¡Inicio de sesión completado!")

    def show_auth_error(self):
        QMessageBox.warning(self, "Error", "No se pudo completar el inicio de sesión.")

    def update_auth_status(self, is_authenticated):
        self.is_logged_in = is_authenticated
        if is_authenticated:
            self.login_button.setIcon(self.icon_login_active)
            self.login_button.setToolTip("Sesión iniciada. Click para salir.")
        else:
            self.login_button.setIcon(self.icon_login)
            self.login_button.setToolTip("Iniciar Sesión")

    def search_clicked(self):
        if self.search_box.text(): self.on_search(self.search_box.text())

    def result_highlighted(self, current, previous):
        if self.on_result_highlighted and self.results_list.currentRow() >= 0:
            self.on_result_highlighted(self.results_list.currentRow())

    def update_results(self, results):
        self.results_list.clear()
        for r in results:
            artist = r['artists'][0]['name'] if r.get('artists') else 'Desconocido'
            self.results_list.addItem(f"♪ {r['title']} - {artist}")

    def play_selected_song_now(self):
        if self.results_list.currentRow() >= 0: self.on_select_song(self.results_list.currentRow())

    def update_song_info(self, text):
        self.song_label.setText(f"♪ {text}")

    def toggle_play_clicked(self):
        self.on_toggle_play()

    def update_play_button_icon(self, is_playing):
        if is_playing:
            self.play_button.setIcon(self.icon_pause)
            if hasattr(self, 'play_pause_action'): self.play_pause_action.setText("⏸ Pausar")
        else:
            self.play_button.setIcon(self.icon_play)
            if hasattr(self, 'play_pause_action'): self.play_pause_action.setText("▶ Reproducir")

    def update_loop_button_icon(self, mode):
        if mode == 1:
            self.loop_button.setIcon(self.icon_loop_queue); self.loop_button.setToolTip("Repetir Cola")
        elif mode == 2:
            self.loop_button.setIcon(self.icon_loop_song); self.loop_button.setToolTip("Repetir Canción")
        else:
            self.loop_button.setIcon(self.icon_loop_off); self.loop_button.setToolTip("Repetir (Apagado)")

    def volume_changed(self, val):
        self.on_volume_change(val)

    def seek_position(self, val):
        self.on_seek(val / 1000.0)

    def update_progress(self, pos):
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(int(pos * 1000))
        self.progress_slider.blockSignals(False)

    def update_time(self, cur, tot):
        self.time_label.setText(self._format_time(cur))
        self.total_time_label.setText(self._format_time(tot))

    def _format_time(self, s):
        return f"{s // 60}:{s % 60:02d}"

    def next_clicked(self):
        self.on_next()

    def previous_clicked(self):
        self.on_previous()

    def update_queue(self, queue, current_index):
        self.queue_list.clear()
        for i, s in enumerate(queue):
            prefix = "▶ " if i == current_index else "   "
            artist = s['artists'][0]['name'] if s.get('artists') else 'Desconocido'
            self.queue_list.addItem(f"{prefix}{s['title']} - {artist}")

    def import_playlist_clicked(self):
        url, ok = QInputDialog.getText(self, "Importar Playlist", "Pega la URL:")
        if ok and url: self.on_import_playlist(url)

    def remove_selected(self):
        if self.queue_list.currentRow() >= 0: self.on_remove_from_queue(self.queue_list.currentRow())

    def queue_item_selected(self):
        self.on_queue_item_selected(self.queue_list.currentRow())

    def show_queue_context_menu(self, pos):
        if not self.queue_list.itemAt(pos): return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #0f1b1c; color: white; border: 1px solid #1a2728; } QMenu::item:selected { background-color: #ff4444; }")
        delete_action = menu.addAction(self.icon_trash, " Eliminar")
        if menu.exec(self.queue_list.mapToGlobal(pos)) == delete_action: self.remove_selected()

    def queue_item_moved(self, source_parent_index, source_row, source_end_row, dest_parent_index, dest_row):
        if self.on_queue_item_moved: self.on_queue_item_moved(source_row, dest_row)

    def show_results_context_menu(self, pos):
        if not self.results_list.itemAt(pos): return
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #0f1b1c; color: white; border: 1px solid #1a2728; } QMenu::item:selected { background-color: #03adb7; }")
        play = menu.addAction(qta.icon('fa5s.play', color='white'), " Reproducir ahora")
        add_next = menu.addAction(qta.icon('fa5s.level-down-alt', color='white', options=[{'rotation': -90}]),
                                  " Agregar Siguiente")
        add_queue = menu.addAction(qta.icon('fa5s.plus', color='white'), " Agregar a la cola")
        action = menu.exec(self.results_list.mapToGlobal(pos))
        if action == play:
            self.play_selected_song_now()
        elif action == add_next:
            self.on_add_next(self.results_list.currentRow())
        elif action == add_queue:
            self.on_add_to_queue(self.results_list.currentRow())

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("YTMusic Minimal Client")
        menu = QMenu(self)
        menu.addAction("Mostrar").triggered.connect(self.showNormal)
        menu.addSeparator()
        self.play_pause_action = menu.addAction(" Reproducir")
        self.play_pause_action.triggered.connect(self.on_toggle_play)
        menu.addAction(self.icon_prev, " Anterior").triggered.connect(self.on_previous)
        menu.addAction(self.icon_next, " Siguiente").triggered.connect(self.on_next)
        menu.addSeparator()
        menu.addAction("Salir").triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger: self.showNormal()

    def closeEvent(self, e):
        e.ignore();
        self.hide()
        self.tray_icon.showMessage("Minimizado", "Reproduciendo en 2do plano.", QSystemTrayIcon.MessageIcon.Information,
                                   2000)

    def ask_to_save_playlist(self, title, auth):
        msg = QMessageBox(self)
        msg.setWindowTitle("Guardar Playlist")
        msg.setIcon(QMessageBox.Question)
        if auth:
            msg.setText(f"¿Dónde guardar '{title}'?")
            local = msg.addButton("💾 Local", QMessageBox.ActionRole)
            cloud = msg.addButton("☁️ YTMusic", QMessageBox.ActionRole)
            msg.addButton("Cancelar", QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() == local:
                self.on_save_imported_playlist(False)
            elif msg.clickedButton() == cloud:
                self.on_save_imported_playlist(True)
        else:
            msg.setText(f"¿Guardar '{title}' localmente?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            if msg.exec() == QMessageBox.Yes: self.on_save_imported_playlist(False)

    def show_save_playlist_success(self, t, l):
        QMessageBox.information(self, "Éxito", f"Guardada {t} ({l})")

    def show_save_playlist_error(self, t):
        QMessageBox.warning(self, "Error", f"Falló al guardar {t}")

    def update_autoplay_button_icon(self, enabled):
        self.autoplay_button.setIcon(self.icon_autoplay_on if enabled else self.icon_autoplay_off)