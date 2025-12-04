import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QSlider, QSplitter, QMenu,
    QInputDialog, QMessageBox, QSystemTrayIcon, QApplication,
    QTabWidget, QListWidgetItem, QFrame, QSizePolicy, QScrollArea, QToolButton
)
from PySide6.QtCore import Qt, QSize, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QIcon, QAction, QKeySequence, QPixmap
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

class ImprovedQueueItem(QWidget):
    play_clicked = Signal(int)
    remove_clicked = Signal(int)

    def __init__(self, song, index, is_current=False):
        super().__init__()
        self.index = index
        self.song = song

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self.play_indicator = QLabel()
        if is_current:
            self.play_indicator.setPixmap(qta.icon('fa5s.volume-up', color='#FF0000').pixmap(14, 14))
        else:
            self.play_indicator.setPixmap(qta.icon('fa5s.grip-vertical', color='#666').pixmap(14, 14))
        self.play_indicator.setFixedWidth(20)

        thumb = QLabel()
        thumb.setFixedSize(48, 48)
        thumb.setPixmap(qta.icon('fa5s.music', color='#666').pixmap(48, 48))
        thumb.setScaledContents(True)
        thumb.setStyleSheet("border-radius: 4px; background: #1a1a1a;")

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title = QLabel(song.get('title', 'Desconocido'))
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        title.setWordWrap(False)

        artist_text = ", ".join([a.get('name', '') for a in song.get('artists', [])]) if song.get(
            'artists') else "Desconocido"
        artist = QLabel(artist_text)
        artist.setStyleSheet("color: #999; font-size: 11px;")
        artist.setWordWrap(False)

        info_layout.addWidget(title)
        info_layout.addWidget(artist)
        info_layout.addStretch()

        btn_play = QPushButton()
        btn_play.setIcon(qta.icon('fa5s.play', color='white'))
        btn_play.setFixedSize(28, 28)
        btn_play.clicked.connect(lambda: self.play_clicked.emit(self.index))
        btn_play.setCursor(Qt.PointingHandCursor)
        btn_play.setStyleSheet("""
            QPushButton { 
                border: none; 
                border-radius: 14px; 
                background: transparent; 
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); }
        """)

        btn_remove = QPushButton()
        btn_remove.setIcon(qta.icon('fa5s.times', color='#999'))
        btn_remove.setFixedSize(28, 28)
        btn_remove.clicked.connect(lambda: self.remove_clicked.emit(self.index))
        btn_remove.setCursor(Qt.PointingHandCursor)
        btn_remove.setStyleSheet("""
            QPushButton { 
                border: none; 
                border-radius: 14px; 
                background: transparent; 
            }
            QPushButton:hover { 
                background: rgba(255,0,0,0.2);
            }
        """)

        layout.addWidget(self.play_indicator)
        layout.addWidget(thumb)
        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(btn_play)
        layout.addWidget(btn_remove)

        bg_color = "rgba(255,0,0,0.08)" if is_current else "transparent"
        border_color = "rgba(255,0,0,0.3)" if is_current else "transparent"
        self.setStyleSheet(f"""
            ImprovedQueueItem {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            ImprovedQueueItem:hover {{
                background: rgba(255,255,255,0.03);
            }}
        """)

class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_add_to_queue, on_toggle_play, on_add_next,
                 on_volume_change, on_seek, on_next, on_previous, on_remove_from_queue,
                 on_queue_item_selected, on_login_requested, on_playlist_selected, on_import_playlist, app_icon,
                 on_save_imported_playlist, on_result_highlighted, on_queue_item_moved, on_toggle_loop,
                 on_logout_requested, on_toggle_autoplay, on_show_lyrics_requested, on_home_requested):
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
        self.on_home_requested = on_home_requested

        self.is_logged_in = False
        self.app_icon = app_icon
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle("YouTube Music - Minimal Client")

        self.icon_play = qta.icon('fa5s.play', color='white')
        self.icon_pause = qta.icon('fa5s.pause', color='white')
        self.icon_next = qta.icon('fa5s.step-forward', color='white')
        self.icon_prev = qta.icon('fa5s.step-backward', color='white')
        self.icon_search = qta.icon('fa5s.search', color='white')
        self.icon_volume = qta.icon('fa5s.volume-up', color='white')
        self.icon_trash = qta.icon('fa5s.trash', color='white')
        self.icon_clear = qta.icon('fa5s.broom', color='white')
        self.icon_login = qta.icon('fa5s.user-circle', color='white')
        self.icon_login_active = qta.icon('fa5s.user-circle', color='#FF0000')
        self.icon_import = qta.icon('fa5s.file-import', color='white')
        self.icon_loop_off = qta.icon('fa5s.sync-alt', color='gray')
        self.icon_loop_queue = qta.icon('fa5s.sync-alt', color='#FF0000')
        self.icon_loop_song = qta.icon('fa5s.redo', color='#FF0000')
        self.icon_autoplay_off = qta.icon('fa5s.magic', color='gray')
        self.icon_autoplay_on = qta.icon('fa5s.magic', color='#FF0000')
        self.icon_lyrics = qta.icon('fa5s.microphone-alt', color='white')
        self.icon_home = qta.icon('fa5s.home', color='white')
        self.icon_library = qta.icon('fa5s.music', color='white')
        self.icon_explore = qta.icon('fa5s.compass', color='white')
        self.icon_playlist = qta.icon('fa5s.list', color='white')

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        top_bar = self._create_top_bar()
        outer_layout.addWidget(top_bar)

        central_split = QSplitter(Qt.Horizontal)
        central_split.setHandleWidth(1)

        sidebar = self._create_sidebar()
        central_split.addWidget(sidebar)

        center_widget = self._create_center_widget()
        central_split.addWidget(center_widget)

        right_panel = self._create_improved_right_panel()
        central_split.addWidget(right_panel)

        central_split.setSizes([180, 600, 320])
        outer_layout.addWidget(central_split, stretch=1)

        player_widget = self._create_player_widget()
        outer_layout.addWidget(player_widget)

        self.setup_quit_shortcut()
        self.init_tray_icon()
        self._apply_styles()

    def _create_top_bar(self):
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(60)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        logo_label = QLabel("YouTube Music")
        logo_label.setObjectName("logo_label")
        logo_label.setFixedWidth(150)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar canción, artista, álbum...")
        self.search_box.returnPressed.connect(self.search_clicked)
        self.search_box.setFixedHeight(38)
        self.search_box.setMaximumWidth(500)

        self.search_button = QPushButton()
        self.search_button.setIcon(self.icon_search)
        self.search_button.clicked.connect(self.search_clicked)
        self.search_button.setFixedSize(38, 38)
        self.search_button.setCursor(Qt.PointingHandCursor)

        self.login_button = QPushButton()
        self.login_button.setIcon(self.icon_login)
        self.login_button.setToolTip("Iniciar Sesión")
        self.login_button.setFixedSize(38, 38)
        self.login_button.clicked.connect(self.login_clicked)
        self.login_button.setCursor(Qt.PointingHandCursor)

        top_layout.addWidget(logo_label)
        top_layout.addStretch()
        top_layout.addWidget(self.search_box)
        top_layout.addWidget(self.search_button)
        top_layout.addSpacing(16)
        top_layout.addWidget(self.login_button)

        return top_bar

    def _create_sidebar(self):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(8, 16, 8, 8)
        side_layout.setSpacing(4)

        nav_buttons = [
            ("Inicio", self.icon_home),
            ("Explorar", self.icon_explore),
            ("Biblioteca", self.icon_library),
        ]

        self.nav_buttons = {}

        for text, icon in nav_buttons:
            btn = QPushButton(text)
            btn.setIcon(icon)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            side_layout.addWidget(btn)
            self.nav_buttons[text] = btn

        self.nav_buttons["Inicio"].clicked.connect(self.on_home_clicked)
        self.nav_buttons["Explorar"].clicked.connect(self.on_explore_clicked)
        self.nav_buttons["Biblioteca"].clicked.connect(self.on_library_clicked)

        side_layout.addSpacing(16)

        import_btn = QPushButton("Importar Playlist")
        import_btn.setIcon(self.icon_import)
        import_btn.clicked.connect(self.import_playlist_clicked)
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.setFixedHeight(40)
        side_layout.addWidget(import_btn)

        side_layout.addStretch()

        return sidebar

    def _create_center_widget(self):
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(16, 16, 16, 16)
        center_layout.setSpacing(12)

        search_info = QLabel("Resultados de Búsqueda")
        search_info.setObjectName("search_info")
        search_info.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.results_list = QListWidget()
        self.results_list.setObjectName("results_list")
        self.results_list.setSpacing(8)
        self.results_list.itemDoubleClicked.connect(self.play_selected_song_now)
        self.results_list.currentItemChanged.connect(self.result_highlighted)
        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_results_context_menu)

        center_layout.addWidget(search_info)
        center_layout.addWidget(self.results_list)

        return center_widget

    def _create_improved_right_panel(self):
        """Panel derecho mejorado con mejor organización"""
        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 16, 8, 8)
        right_layout.setSpacing(8)

        # Pestañas principales
        self.right_tabs = QTabWidget()
        self.right_tabs.setObjectName("right_tabs")

        # ===== TAB 1: BIBLIOTECA (Playlists + Cola) =====
        library_tab = QWidget()
        library_layout = QVBoxLayout(library_tab)
        library_layout.setContentsMargins(8, 8, 8, 8)
        library_layout.setSpacing(12)

        # Sección de Playlists (colapsable)
        playlists_section = CollapsibleSection("Mis Playlists")
        self.playlists_list = QListWidget()
        self.playlists_list.setObjectName("compact_list")
        self.playlists_list.itemDoubleClicked.connect(self.playlist_selected)
        playlists_section.add_content(self.playlists_list)
        library_layout.addWidget(playlists_section)

        # Separador visual
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background: #333; max-height: 1px;")
        library_layout.addWidget(separator)

        # Sección de Cola
        queue_header = QWidget()
        queue_header_layout = QHBoxLayout(queue_header)
        queue_header_layout.setContentsMargins(0, 0, 0, 0)

        queue_title = QLabel("Cola de Reproducción")
        queue_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.queue_count_label = QLabel("(0)")
        self.queue_count_label.setStyleSheet("color: #999; font-size: 12px;")

        clear_queue_btn = QPushButton()
        clear_queue_btn.setIcon(self.icon_clear)
        clear_queue_btn.setToolTip("Limpiar cola")
        clear_queue_btn.setFixedSize(28, 28)
        clear_queue_btn.clicked.connect(self._clear_queue_except_current)
        clear_queue_btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                border-radius: 14px; 
                background: transparent; 
            }
            QPushButton:hover { background: rgba(255,0,0,0.2); }
        """)

        queue_header_layout.addWidget(queue_title)
        queue_header_layout.addWidget(self.queue_count_label)
        queue_header_layout.addStretch()
        queue_header_layout.addWidget(clear_queue_btn)

        library_layout.addWidget(queue_header)

        # Lista de cola mejorada
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.NoFrame)

        self.queue_container = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(4)
        self.queue_layout.addStretch()

        self.queue_scroll.setWidget(self.queue_container)
        library_layout.addWidget(self.queue_scroll, stretch=1)

        # Mantenemos la lista antigua pero oculta (para compatibilidad)
        self.queue_list = QListWidget()
        self.queue_list.hide()

        self.right_tabs.addTab(library_tab, qta.icon('fa5s.music', color='white'), "Biblioteca")

        # ===== TAB 2: LETRA =====
        self.lyrics_tab = QWidget()
        lyrics_layout = QVBoxLayout(self.lyrics_tab)
        lyrics_layout.setContentsMargins(8, 8, 8, 8)

        self.lyrics_list_widget = QListWidget()
        self.lyrics_list_widget.setObjectName("lyrics_list")
        lyrics_layout.addWidget(self.lyrics_list_widget)

        self.right_tabs.addTab(self.lyrics_tab, qta.icon('fa5s.microphone-alt', color='white'), "Letra")

        right_layout.addWidget(self.right_tabs)

        return right_panel

    def _clear_queue_except_current(self):
        reply = QMessageBox.question(
            self,
            "Limpiar Cola",
            "¿Eliminar todas las canciones excepto la actual?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            pass

    def _create_player_widget(self):
        player_widget = QWidget()
        player_widget.setObjectName("player_widget")
        player_widget.setFixedHeight(170)
        player_layout = QVBoxLayout(player_widget)
        player_layout.setContentsMargins(16, 12, 16, 12)
        player_layout.setSpacing(8)

        # Fila de info
        info_row = QHBoxLayout()
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setPixmap(self._placeholder_cover_pixmap(56))
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 6px; background: #1a1a1a;")

        self.song_label = QLabel("Sin reproducción")
        self.song_label.setObjectName("song_label")
        self.song_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        info_row.addWidget(self.cover_label)
        info_row.addSpacing(12)
        info_row.addWidget(self.song_label)
        info_row.addStretch()

        # Progreso
        progress_layout = QHBoxLayout()
        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(45)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(self.seek_position)

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setFixedWidth(45)

        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_slider, stretch=1)
        progress_layout.addWidget(self.total_time_label)

        # Controles
        ctrl_layout = QHBoxLayout()

        # Controles izquierdos
        left_controls = QHBoxLayout()
        left_controls.addStretch()

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.icon_prev)
        self.prev_button.clicked.connect(self.previous_clicked)
        self.prev_button.setFixedSize(42, 42)
        self.prev_button.setCursor(Qt.PointingHandCursor)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icon_play)
        self.play_button.clicked.connect(self.toggle_play_clicked)
        self.play_button.setFixedSize(52, 52)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setObjectName("play_button")

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icon_next)
        self.next_button.clicked.connect(self.next_clicked)
        self.next_button.setFixedSize(42, 42)
        self.next_button.setCursor(Qt.PointingHandCursor)

        left_controls.addWidget(self.prev_button)
        left_controls.addWidget(self.play_button)
        left_controls.addWidget(self.next_button)
        left_controls.addStretch()

        # Controles derechos
        right_controls = QHBoxLayout()

        self.lyrics_button = QPushButton()
        self.lyrics_button.setIcon(self.icon_lyrics)
        self.lyrics_button.setToolTip("Ver letra")
        self.lyrics_button.clicked.connect(self.on_show_lyrics_requested)
        self.lyrics_button.setFixedSize(36, 36)
        self.lyrics_button.setCursor(Qt.PointingHandCursor)

        self.loop_button = QPushButton()
        self.loop_button.setIcon(self.icon_loop_off)
        self.loop_button.setToolTip("Repetir")
        self.loop_button.clicked.connect(self.on_toggle_loop)
        self.loop_button.setFixedSize(36, 36)
        self.loop_button.setCursor(Qt.PointingHandCursor)

        self.autoplay_button = QPushButton()
        self.autoplay_button.setIcon(self.icon_autoplay_off)
        self.autoplay_button.setToolTip("Autoplay")
        self.autoplay_button.clicked.connect(self.on_toggle_autoplay)
        self.autoplay_button.setFixedSize(36, 36)
        self.autoplay_button.setCursor(Qt.PointingHandCursor)

        vol_icon = QLabel()
        vol_icon.setPixmap(self.icon_volume.pixmap(20, 20))

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self.volume_changed)

        right_controls.addWidget(self.lyrics_button)
        right_controls.addWidget(self.loop_button)
        right_controls.addWidget(self.autoplay_button)
        right_controls.addSpacing(12)
        right_controls.addWidget(vol_icon)
        right_controls.addWidget(self.volume_slider)

        ctrl_layout.addLayout(left_controls, stretch=3)
        ctrl_layout.addLayout(right_controls, stretch=2)

        player_layout.addLayout(info_row)
        player_layout.addLayout(progress_layout)
        player_layout.addLayout(ctrl_layout)

        return player_widget

    def _apply_styles(self):
        self.setStyleSheet("""
        QWidget {
            background-color: #0b0b0b;
            color: #e6e6e6;
            font-family: "Segoe UI", system-ui, -apple-system;
            font-size: 13px;
        }

        #top_bar {
            background: #0f0f0f;
            border-bottom: 1px solid #1f1f1f;
        }

        #logo_label {
            color: white;
            font-weight: 700;
            font-size: 18px;
        }

        QLineEdit {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 19px;
            padding: 8px 16px;
            color: #e6e6e6;
        }
        QLineEdit:focus {
            border: 1px solid #FF0000;
        }

        #sidebar {
            background: #0f0f0f;
            border-right: 1px solid #1f1f1f;
        }

        #sidebar QPushButton {
            text-align: left;
            padding-left: 16px;
            border: none;
            border-radius: 6px;
            font-weight: 500;
        }
        #sidebar QPushButton:hover {
            background: rgba(255,255,255,0.05);
        }

        #right_panel {
            background: #0b0b0b;
        }

        #section_header {
            background: transparent;
        }

        #compact_list {
            background: transparent;
            border: none;
        }
        #compact_list::item {
            padding: 8px 12px;
            border-radius: 4px;
            border: none;
        }
        #compact_list::item:hover {
            background: rgba(255,255,255,0.05);
        }
        #compact_list::item:selected {
            background: rgba(255,0,0,0.15);
        }

        #player_widget {
            background: transparent;
            border-top: 1px solid #1f1f1f;
        }

        #song_label {
            font-weight: 600;
            font-size: 14px;
            color: #ffffff;
        }

        #play_button {
            background: #FF0000;
            border-radius: 26px;
            border: none;
        }
        #play_button:hover {
            background: #E60000;
            transform: scale(1.05);
        }

        QSlider::groove:horizontal {
            border: none;
            height: 4px;
            background: #2a2a2a;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: white;
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }
        QSlider::handle:horizontal:hover {
            background: #FF0000;
        }
        QSlider::sub-page:horizontal {
            background: #FF0000;
            border-radius: 2px;
        }

        QTabWidget::pane {
            border: none;
            background: transparent;
        }
        QTabBar::tab {
            background: transparent;
            color: #999;
            padding: 10px 16px;
            border: none;
            font-weight: 500;
        }
        QTabBar::tab:selected {
            color: white;
            border-bottom: 2px solid #FF0000;
        }
        QTabBar::tab:hover {
            color: #ccc;
        }

        QScrollArea {
            border: none;
            background: transparent;
        }

        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #2a2a2a;
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #FF0000;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }

        #results_list {
            background: transparent;
            border: none;
        }
        #results_list::item {
            background: #0f0f0f;
            border: 1px solid #1a1a1a;
            border-radius: 8px;
            margin: 4px 0;
        }
        #results_list::item:selected {
            border-color: #FF0000;
            background: rgba(255,0,0,0.05);
        }
        #results_list::item:hover {
            background: #151515;
        }

        #lyrics_list {
            background: transparent;
            border: none;
            font-size: 14px;
        }
        #lyrics_list::item {
            border: none;
            padding: 8px;
            background: transparent;
        }
        #lyrics_list::item:selected {
            background: rgba(255,0,0,0.15);
            color: white;
            font-weight: 600;
        }

        QMenu {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 4px;
        }
        QMenu::item {
            padding: 8px 24px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background: #FF0000;
        }
        """)

    def _placeholder_cover_pixmap(self, size):
        return self.icon_library.pixmap(size, size)

    def _make_track_item_widget(self, song, is_current=False):
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        thumb = QLabel()
        thumb.setFixedSize(56, 56)
        thumb.setPixmap(self._placeholder_cover_pixmap(56))
        thumb.setScaledContents(True)
        thumb.setStyleSheet("border-radius: 6px; background: #1a1a1a;")

        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(4)

        title = QLabel(song.get('title', 'Desconocido'))
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        title.setWordWrap(False)

        artists = song.get('artists', [])
        artist_text = ", ".join([a.get('name', '') for a in artists]) if artists else "Desconocido"
        artist = QLabel(artist_text)
        artist.setStyleSheet("color: #999; font-size: 12px;")
        artist.setWordWrap(False)

        meta_layout.addWidget(title)
        meta_layout.addWidget(artist)

        layout.addWidget(thumb)
        layout.addLayout(meta_layout, stretch=1)

        if is_current:
            w.setStyleSheet("background: rgba(255,0,0,0.08); border-radius: 8px;")

        return w

    # ===== MÉTODOS DE ACTUALIZACIÓN DE COLA MEJORADOS =====

    def update_queue(self, queue, current_index):
        """Actualiza la cola con el nuevo diseño mejorado"""
        # Limpiar layout anterior
        while self.queue_layout.count() > 1:  # Mantener el stretch al final
            item = self.queue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Actualizar contador
        self.queue_count_label.setText(f"({len(queue)})")

        # Agregar items mejorados
        for i, song in enumerate(queue):
            is_current = (i == current_index)
            item_widget = ImprovedQueueItem(song, i, is_current)

            # Conectar señales
            item_widget.play_clicked.connect(self._on_queue_item_play_clicked)
            item_widget.remove_clicked.connect(self._on_queue_item_remove_clicked)

            self.queue_layout.insertWidget(i, item_widget)

        # Scroll a la canción actual
        if 0 <= current_index < len(queue):
            # Pequeño delay para que el layout se actualice
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._scroll_to_current(current_index))

    def _scroll_to_current(self, index):
        """Scroll automático a la canción actual"""
        if index >= 0 and index < self.queue_layout.count() - 1:
            widget = self.queue_layout.itemAt(index).widget()
            if widget:
                self.queue_scroll.ensureWidgetVisible(widget)

    def _on_queue_item_play_clicked(self, index):
        """Cuando se hace clic en play de un item de la cola"""
        if self.on_queue_item_selected:
            self.on_queue_item_selected(index)

    def _on_queue_item_remove_clicked(self, index):
        """Cuando se hace clic en eliminar de un item de la cola"""
        if self.on_remove_from_queue:
            self.on_remove_from_queue(index)

    def on_home_clicked(self):
        if hasattr(self, "on_home_requested"):
            self.on_home_requested()


    def show_home(self, sections):
        self.results_list.clear()

        for title, items in sections:
            # título de sección
            header = QListWidgetItem(f" {title}")
            header.setFlags(header.flags() & ~Qt.ItemIsSelectable)
            self.results_list.addItem(header)

            # contenido
            for item in items:
                w = QWidget()
                layout = QHBoxLayout(w)
                layout.setContentsMargins(10, 6, 10, 6)

                label = QLabel(item["title"])
                label.setStyleSheet("font-size:14px; font-weight:600;")

                layout.addWidget(label)
                layout.addStretch()

                name = item["title"]
                q = QListWidgetItem()
                q.setSizeHint(QSize(0, 44))
                self.results_list.addItem(q)
                self.results_list.setItemWidget(q, w)

    def on_explore_clicked(self):
        print("Explorar clickeado")
        # Puedes hacer una búsqueda por defecto tipo "Top hits"
        if self.on_search:
            self.on_search("top hits")

    def on_library_clicked(self):
        print("Biblioteca clickeado")
        # Mover al tab de biblioteca del panel derecho
        self.right_tabs.setCurrentIndex(0)

    def setup_quit_shortcut(self):
        quit_action = QAction("Salir", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip("YTMusic Client")
        menu = QMenu(self)
        self.setup_tray_menu(menu)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def setup_tray_menu(self, menu):
        menu.addAction("Mostrar").triggered.connect(self.showNormal)
        menu.addSeparator()
        self.play_pause_action = menu.addAction("Reproducir")
        self.play_pause_action.triggered.connect(self.on_toggle_play)
        menu.addAction(self.icon_prev, "Anterior").triggered.connect(self.on_previous)
        menu.addAction(self.icon_next, "Siguiente").triggered.connect(self.on_next)
        menu.addSeparator()
        menu.addAction("Salir").triggered.connect(QApplication.instance().quit)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()

    def closeEvent(self, e):
        e.ignore()
        self.hide()
        self.tray_icon.showMessage("Minimizado", "Reproduciendo en 2do plano.",
                                   QSystemTrayIcon.MessageIcon.Information, 2000)

    def search_clicked(self):
        text = self.search_box.text().strip()
        if text and self.on_search:
            self.on_search(text)

    def result_highlighted(self, current, previous):
        if self.on_result_highlighted and self.results_list.currentRow() >= 0:
            self.on_result_highlighted(self.results_list.currentRow())

    def update_results(self, results):
        self.results_list.clear()
        for r in results:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 76))
            widget = self._make_track_item_widget(r)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

    def play_selected_song_now(self):
        if self.results_list.currentRow() >= 0 and self.on_select_song:
            self.on_select_song(self.results_list.currentRow())

    def update_song_info(self, text):
        self.song_label.setText(f" {text}")

    def toggle_play_clicked(self):
        if self.on_toggle_play:
            self.on_toggle_play()

    def update_play_button_icon(self, is_playing):
        self.play_button.setIcon(self.icon_pause if is_playing else self.icon_play)
        if hasattr(self, 'play_pause_action'):
            self.play_pause_action.setText("⏸ Pausar" if is_playing else "▶ Reproducir")

    def update_loop_button_icon(self, mode):
        icons = {0: self.icon_loop_off, 1: self.icon_loop_queue, 2: self.icon_loop_song}
        tooltips = {0: "Repetir (Apagado)", 1: "Repetir Cola", 2: "Repetir Canción"}
        self.loop_button.setIcon(icons.get(mode, self.icon_loop_off))
        self.loop_button.setToolTip(tooltips.get(mode, "Repetir"))

    def update_autoplay_button_icon(self, enabled):
        self.autoplay_button.setIcon(self.icon_autoplay_on if enabled else self.icon_autoplay_off)

    def volume_changed(self, val):
        if self.on_volume_change:
            self.on_volume_change(val)

    def seek_position(self, val):
        if self.on_seek:
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
        if self.on_next:
            self.on_next()

    def previous_clicked(self):
        if self.on_previous:
            self.on_previous()

    def update_playlists(self, playlists):
        self.playlists_list.clear()
        if not playlists:
            self.playlists_list.addItem("Inicia sesión para ver playlists")
            return
        for p in playlists:
            self.playlists_list.addItem(f" {p.get('title', 'Sin título')}")

    def playlist_selected(self):
        if self.on_playlist_selected:
            self.on_playlist_selected(self.playlists_list.currentRow())

    def import_playlist_clicked(self):
        url, ok = QInputDialog.getText(self, "Importar Playlist", "Pega la URL:")
        if ok and url and self.on_import_playlist:
            self.on_import_playlist(url)

    def show_results_context_menu(self, pos):
        if not self.results_list.itemAt(pos):
            return
        menu = QMenu(self)
        play = menu.addAction(self.icon_play, "Reproducir ahora")
        add_next = menu.addAction(qta.icon('fa5s.level-down-alt', color='white'), "Siguiente")
        add_queue = menu.addAction(qta.icon('fa5s.plus', color='white'), "Agregar a cola")
        action = menu.exec(self.results_list.mapToGlobal(pos))

        if action == play:
            self.play_selected_song_now()
        elif action == add_next and self.on_add_next:
            self.on_add_next(self.results_list.currentRow())
        elif action == add_queue and self.on_add_to_queue:
            self.on_add_to_queue(self.results_list.currentRow())

    def set_lyrics_lines(self, lines):
        self.lyrics_list_widget.clear()
        for line in lines:
            item = QListWidgetItem(line)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_list_widget.addItem(item)
        self.lyrics_button.setIcon(qta.icon('fa5s.microphone-alt', color='#FF0000'))

    def set_lyrics_message(self, message, switch_focus=False):
        self.lyrics_list_widget.clear()
        item = QListWidgetItem(message)
        item.setTextAlignment(Qt.AlignCenter)
        self.lyrics_list_widget.addItem(item)
        if switch_focus:
            self.right_tabs.setCurrentWidget(self.lyrics_tab)
        self.lyrics_button.setIcon(qta.icon('fa5s.microphone-alt', color='gray'))

    def highlight_lyric_index(self, index):
        if 0 <= index < self.lyrics_list_widget.count():
            self.lyrics_list_widget.setCurrentRow(index)
            self.lyrics_list_widget.scrollToItem(
                self.lyrics_list_widget.item(index),
                QListWidget.PositionAtCenter
            )

    def login_clicked(self):
        if self.is_logged_in:
            reply = QMessageBox.question(
                self, "Cerrar Sesión",
                "¿Cerrar la sesión actual?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes and self.on_logout_requested:
                self.on_logout_requested()
        else:
            instructions = """Para iniciar sesión:
                1. Abre YouTube Music en tu navegador
                2. Inicia sesión con tu cuenta
                3. Abre herramientas de desarrollador (F12)
                4. Ve a "Red" y recarga (Ctrl+Shift+R)
                5. Filtra por "browse"
                6. Clic derecho → Copiar como cURL
                7. Pega el contenido abajo"""

            text, ok = QInputDialog.getMultiLineText(
                self, 'Iniciar Sesión', instructions
            )
            if ok and text:
                headers_list = []
                unwrapped = re.sub(r'[\^\\]\s*\n', ' ', text).replace('\n', ' ')
                h_matches = re.findall(r"-H\s+(['\"])(.*?)\1", unwrapped)
                if h_matches:
                    headers_list.extend([m[1] for m in h_matches])
                c_match = re.search(r"(--cookie|-b)\s+(['\"])(.*?)\2", unwrapped)
                if c_match:
                    headers_list.append(f"Cookie: {c_match.group(3)}")
                if self.on_login_requested:
                    self.on_login_requested("\n".join(headers_list))

    def update_auth_status(self, is_authenticated):
        self.is_logged_in = is_authenticated
        icon = self.icon_login_active if is_authenticated else self.icon_login
        tooltip = "Cerrar sesión" if is_authenticated else "Iniciar sesión"
        self.login_button.setIcon(icon)
        self.login_button.setToolTip(tooltip)

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
            if msg.exec() == QMessageBox.Yes:
                self.on_save_imported_playlist(False)

    def show_save_playlist_success(self, t, l):
        QMessageBox.information(self, "Éxito", f"'{t}' guardada en {l}")

    def show_save_playlist_error(self, t):
        QMessageBox.warning(self, "Error", f"No se pudo guardar '{t}'")

    def show_auth_success(self):
        QMessageBox.information(self, "Éxito", "Sesión iniciada correctamente")

    def show_auth_error(self):
        QMessageBox.warning(self, "Error", "No se pudo iniciar sesión")