from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSplitter, QMenu,
    QInputDialog, QMessageBox, QSystemTrayIcon, QApplication,
    QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QSize, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QAction, QKeySequence, QPixmap
import qtawesome as qta

from ui.components.queue_widgets import ImprovedQueueItem
from ui.components.top_bar import TopBar
from ui.components.sidebar import Sidebar
from ui.components.results_panel import ResultsPanel
from ui.components.player_panel import PlayerPanel
from ui.components.library_panel import LibraryPanel
from ui.components.library_browser import LibraryBrowserPanel
from ui.components.track_result_item import TrackResultItem
from ui.components.home_panel import HomePanel
from ui.components.now_playing_panel import NowPlayingPanel
from core.thumbnail_cache import ThumbnailCache
from utils import parse_curl_headers, get_thumbnail_url, scale_cover


class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_add_to_queue, on_toggle_play, on_add_next,
                 on_volume_change, on_seek, on_next, on_previous, on_remove_from_queue,
                 on_queue_item_selected, on_login_requested, on_playlist_selected, on_import_playlist, app_icon,
                 on_save_imported_playlist, on_result_highlighted, on_queue_item_moved, on_toggle_loop,
                 on_logout_requested, on_toggle_autoplay, on_show_lyrics_requested, on_home_requested,
                 on_clear_queue, on_save_queue_playlist
                 ):
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
        self.on_clear_queue = on_clear_queue
        self.on_save_queue_playlist = on_save_queue_playlist

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
        self.library_panel.hide()
        outer_layout.addWidget(central_split, stretch=1)

        player_widget = self._create_player_widget()
        outer_layout.addWidget(player_widget)

        self.thumbnail_cache = ThumbnailCache(self)
        self.setup_quit_shortcut()
        self.init_tray_icon()
        self._apply_styles()

    def _create_top_bar(self):
        self.top_bar = TopBar(self.icon_search, self.icon_login, self.icon_login_active)
        self.search_box = self.top_bar.search_box
        self.search_box.returnPressed.connect(self.search_clicked)
        self.search_button = self.top_bar.search_button
        self.search_button.clicked.connect(self.search_clicked)
        self.login_button = self.top_bar.login_button
        self.login_button.clicked.connect(self.login_clicked)
        self.top_bar.search_requested.connect(self.search_clicked)
        self.top_bar.login_requested.connect(self.login_clicked)
        return self.top_bar

    def _create_sidebar(self):
        self.sidebar = Sidebar({
            "home": self.icon_home,
            "explore": self.icon_explore,
            "library": self.icon_library,
            "import": self.icon_import,
        })
        self.nav_buttons = self.sidebar.nav_buttons
        self.nav_buttons["Inicio"].clicked.connect(self.on_home_clicked)
        self.nav_buttons["Explorar"].clicked.connect(self.on_explore_clicked)
        self.sidebar.import_button.clicked.connect(self.import_playlist_clicked)
        self.sidebar.home_requested.connect(self.on_home_clicked)
        self.sidebar.explore_requested.connect(self.on_explore_clicked)
        self.sidebar.import_requested.connect(self.import_playlist_clicked)
        return self.sidebar

    def _create_center_widget(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.home_panel = HomePanel()
        layout.addWidget(self.home_panel)

        self.results_panel = ResultsPanel()
        self.results_list = self.results_panel.results_list
        self.results_list.itemDoubleClicked.connect(self.play_selected_song_now)
        self.results_list.currentItemChanged.connect(self.result_highlighted)
        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_results_context_menu)
        self.results_panel.hide()
        layout.addWidget(self.results_panel)

        # Library browser panel
        self.library_browser = LibraryBrowserPanel()
        self.library_browser.hide()
        layout.addWidget(self.library_browser)

        # Now playing panel (large cover)
        self.now_playing_panel = NowPlayingPanel()
        self.now_playing_panel.hide()
        layout.addWidget(self.now_playing_panel)

        # Hidden list kept for backward compat with update_playlists / playlist_selected
        self.playlists_list = QListWidget()
        self.playlists_list.hide()

        return container

    def _create_improved_right_panel(self):
        self.library_panel = LibraryPanel()
        self.right_tabs = self.library_panel.right_tabs
        self.queue_count_label = self.library_panel.queue_count_label
        self.queue_layout = self.library_panel.queue_layout
        self.queue_scroll = self.library_panel.queue_scroll
        self.lyrics_list_widget = self.library_panel.lyrics_list_widget
        self.lyrics_tab = self.library_panel.lyrics_tab
        self.library_panel.item_dropped.connect(self._on_queue_item_dropped)
        self.library_panel.clear_requested.connect(self._clear_queue_except_current)
        self.library_panel.save_requested.connect(self._save_queue_as_playlist)
        return self.library_panel

    def _clear_queue_except_current(self):
        reply = QMessageBox.question(
            self,
            "Limpiar Cola",
            "¿Eliminar todas las canciones excepto la actual?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.on_clear_queue:
                self.on_clear_queue()

    def _save_queue_as_playlist(self):
        if not self.on_save_queue_playlist:
            return

        base_title = "Mi Cola"
        title, ok = QInputDialog.getText(
            self,
            "Guardar cola como playlist",
            "Nombre de la playlist:",
            text=base_title
        )

        if ok and title.strip():
            self.on_save_queue_playlist(title.strip())

    def _create_player_widget(self):
        self.player_panel = PlayerPanel({
            "play": self.icon_play,
            "pause": self.icon_pause,
            "next": self.icon_next,
            "prev": self.icon_prev,
            "volume": self.icon_volume,
            "lyrics": self.icon_lyrics,
            "loop_off": self.icon_loop_off,
            "loop_queue": self.icon_loop_queue,
            "loop_song": self.icon_loop_song,
            "autoplay_off": self.icon_autoplay_off,
            "autoplay_on": self.icon_autoplay_on,
            "library": self.icon_library,
        })

        self.cover_label = self.player_panel.cover_label
        self.cover_label.setPixmap(self._placeholder_cover_pixmap(56))
        self.artist_label = self.player_panel.artist_label
        self.player_panel.expand_clicked.connect(self.toggle_now_playing)
        self.player_panel.hide()

        self.song_label = self.player_panel.song_label
        self.time_label = self.player_panel.time_label
        self.progress_slider = self.player_panel.progress_slider
        self.progress_slider.sliderMoved.connect(self.seek_position)
        self.total_time_label = self.player_panel.total_time_label

        self.prev_button = self.player_panel.prev_button
        self.prev_button.clicked.connect(self.previous_clicked)

        self.play_button = self.player_panel.play_button
        self.play_button.clicked.connect(self.toggle_play_clicked)

        self.next_button = self.player_panel.next_button
        self.next_button.clicked.connect(self.next_clicked)

        self.loop_button = self.player_panel.loop_button
        self.loop_button.clicked.connect(self.on_toggle_loop)

        self.volume_slider = self.player_panel.volume_slider
        self.volume_slider.valueChanged.connect(self.volume_changed)

        return self.player_panel

    def _on_queue_item_dropped(self, source_index, target_index):
        print(f"[DRAG] Moviendo item de {source_index} a {target_index}")
        if self.on_queue_item_moved:
            self.on_queue_item_moved(source_index, target_index)

    def _apply_styles(self):
        self.setStyleSheet("""
        QWidget {
            background-color: #030303;
            color: #e6e6e6;
            font-family: "Segoe UI", "Inter", system-ui, -apple-system;
            font-size: 13px;
        }

        #top_bar {
            background: #0f0f0f;
            border-bottom: 1px solid #1a1a1a;
        }

        #logo_label {
            color: white;
            font-weight: 700;
            font-size: 18px;
        }

        QLineEdit {
            background: #121212;
            border: 1px solid #2a2a2a;
            border-radius: 22px;
            padding: 8px 20px;
            color: #e6e6e6;
        }
        QLineEdit:focus {
            border: 1px solid rgba(255,255,255,0.4);
            background: #1a1a1a;
        }

        #sidebar {
            background: #0f0f0f;
            border-right: 1px solid #1a1a1a;
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

        /* Scrollbar Vertical */
        QScrollBar:vertical {
            background: transparent;
            width: 12px;
            margin: 0;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            min-height: 30px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: rgba(255, 0, 0, 0.5);
        }
        
        QScrollBar::handle:vertical:pressed {
            background: rgba(255, 0, 0, 0.7);
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
            background: transparent;
        }
        
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: transparent;
        }

        /* Scrollbar Horizontal */
        QScrollBar:horizontal {
            background: transparent;
            height: 12px;
            margin: 0;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            min-width: 30px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background: rgba(255, 0, 0, 0.5);
        }
        
        QScrollBar::handle:horizontal:pressed {
            background: rgba(255, 0, 0, 0.7);
        }
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0px;
            background: transparent;
        }
        
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: transparent;
        }
        QListWidget QScrollBar:vertical {
            background: transparent;
            width: 10px;
        }
        
        QListWidget QScrollBar::handle:vertical {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 5px;
            min-height: 20px;
        }
        
        QListWidget QScrollBar::handle:vertical:hover {
            background: rgba(255, 0, 0, 0.4);
        }

        #results_list {
            background: transparent;
            border: none;
        }
        #results_list::item {
            background: transparent;
            border-radius: 6px;
            margin: 1px 0;
        }
        #results_list::item:selected {
            background: rgba(255,255,255,0.08);
        }
        #results_list::item:hover {
            background: rgba(255,255,255,0.05);
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

    def _placeholder_cover_pixmap(self, size=56):
        return self.icon_library.pixmap(size, size)

    def update_cover_art(self, song):
        url = get_thumbnail_url(song)
        if url:
            def _on_thumb(px):
                self.cover_label.setPixmap(scale_cover(px, 56))
                self.now_playing_panel.set_cover(px)
            self.thumbnail_cache.request(url, _on_thumb)
        else:
            self.cover_label.setPixmap(self._placeholder_cover_pixmap(56))
            self.now_playing_panel.set_cover(QPixmap())


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
            item_widget.play_clicked.connect(self._on_queue_item_play_clicked)
            item_widget.remove_clicked.connect(self._on_queue_item_remove_clicked)
            self.queue_layout.insertWidget(i, item_widget)
            url = get_thumbnail_url(song)
            if url:
                self.thumbnail_cache.request(url, item_widget.set_thumbnail)

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
        self.home_panel.show_sections(sections, self.thumbnail_cache)
        self.results_panel.hide()
        self.library_browser.hide()
        self.now_playing_panel.hide()
        self.library_panel.hide()
        self.player_panel.set_expanded(False)
        self.home_panel.show()
        self.sidebar.set_active("Inicio")

    def show_library_browser(self):
        self.home_panel.hide()
        self.results_panel.hide()
        self.now_playing_panel.hide()
        self.library_panel.hide()
        self.player_panel.set_expanded(False)
        self.library_browser.show()
        self.sidebar.set_active("Biblioteca")

    def on_explore_clicked(self):
        print("Explorar clickeado")
        # Puedes hacer una búsqueda por defecto tipo "Top hits"
        if self.on_search:
            self.on_search("top hits")

    def on_library_clicked(self):
        pass  # handled via sidebar.library_requested → app_controller

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
        self.home_panel.hide()
        self.library_browser.hide()
        self.now_playing_panel.hide()
        self.library_panel.hide()
        self.player_panel.set_expanded(False)
        self.results_panel.show()
        self.sidebar.set_active("Explorar")
        self.results_list.clear()
        for r in results:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 76))
            widget = TrackResultItem(r)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)
            url = get_thumbnail_url(r)
            if url:
                self.thumbnail_cache.request(url, widget.set_thumbnail)

    def play_selected_song_now(self):
        if self.results_list.currentRow() >= 0 and self.on_select_song:
            self.on_select_song(self.results_list.currentRow())

    def toggle_now_playing(self):
        if self.now_playing_panel.isVisible():
            self.now_playing_panel.hide()
            self.library_panel.hide()
            self.home_panel.show()
            self.player_panel.set_expanded(False)
        else:
            self.home_panel.hide()
            self.results_panel.hide()
            self.library_browser.hide()
            self.now_playing_panel.show()
            self.library_panel.show()
            self.player_panel.set_expanded(True)

    def show_similar_songs(self, songs):
        self.library_panel.show_similar_songs(songs, self.thumbnail_cache)

    def update_now_playing(self, title: str, artist: str):
        self.song_label.setText(title)
        self.artist_label.setText(artist)
        if not self.player_panel.isVisible():
            self.player_panel.show()

    def update_song_info(self, text):
        self.song_label.setText(f" {text}")
        if not self.player_panel.isVisible():
            self.player_panel.show()

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
        pass  # autoplay button removed — queue auto-extends

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

    def show_import_error(self, message):
        QMessageBox.warning(self, "Error al Importar Playlist", message)

    def set_lyrics_lines(self, lines):
        self.lyrics_list_widget.clear()
        for line in lines:
            item = QListWidgetItem(line)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_list_widget.addItem(item)

    def set_lyrics_message(self, message, switch_focus=False):
        self.lyrics_list_widget.clear()
        item = QListWidgetItem(message)
        item.setTextAlignment(Qt.AlignCenter)
        self.lyrics_list_widget.addItem(item)
        if switch_focus:
            self.right_tabs.setCurrentWidget(self.lyrics_tab)

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
                if self.on_login_requested:
                    self.on_login_requested(parse_curl_headers(text))

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