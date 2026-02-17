import re

import qtawesome as qta
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence, QDrag, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QLabel, QSlider, QSplitter, QMenu,
    QInputDialog, QMessageBox, QSystemTrayIcon, QApplication,
    QTabWidget, QListWidgetItem, QFrame, QSizePolicy, QScrollArea, QToolButton
)


class CollapsibleSection(QWidget):
    """collapsible section widget with expand/collapse functionality"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_collapsed = False
        self._setup_ui(title)

    def _setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = self._create_header(title)
        layout.addWidget(header)

        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)

    def _create_header(self, title):
        """header widget with toggle button"""
        header = QWidget()
        header.setObjectName("section_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)

        # Toggle button
        self.toggle_button = QToolButton()
        self.toggle_button.setIcon(qta.icon('fa5s.chevron-down', color='white'))
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.clicked.connect(self.toggle)
        self.toggle_button.setStyleSheet("border: none; background: transparent;")

        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")

        header_layout.addWidget(self.toggle_button)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        return header

    def toggle(self):
        """Toggle the collapsed state"""
        self.is_collapsed = not self.is_collapsed
        self.content.setVisible(not self.is_collapsed)

        icon_name = 'fa5s.chevron-right' if self.is_collapsed else 'fa5s.chevron-down'
        self.toggle_button.setIcon(qta.icon(icon_name, color='white'))

    def add_content(self, widget):
        """Add a widget to the content area"""
        self.content_layout.addWidget(widget)


# Queue items

class ImprovedQueueItem(QWidget):
    """Custom widget for displaying a song in the queue with drag-and-drop"""

    play_clicked = Signal(int)
    remove_clicked = Signal(int)
    drag_started = Signal(int)

    def __init__(self, song, index, is_current=False):
        super().__init__()
        self.index = index
        self.song = song
        self.is_current = is_current
        self.drag_start_position = None

        self.full_title = song.get('title', 'Desconocido')
        self.full_artist = self._get_artist_text(song)

        self._setup_ui()
        self._apply_styling()

    def _get_artist_text(self, song):
        """Extract artist text from song data"""
        artists = song.get('artists', [])
        if artists:
            return ", ".join([a.get('name', '') for a in artists])
        return "Desconocido"

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Drag indicator / play status
        self.play_indicator = self._create_play_indicator()
        layout.addWidget(self.play_indicator)

        # Thumbnail
        thumbnail = self._create_thumbnail()
        layout.addWidget(thumbnail)

        # Song info
        info_layout = self._create_info_layout()
        layout.addLayout(info_layout, stretch=1)

        # Action buttons
        buttons = self._create_action_buttons()
        layout.addWidget(buttons)

        self.setFixedHeight(56)

    def _create_play_indicator(self):
        """play indicator/drag handle"""
        indicator = QLabel()

        if self.is_current:
            indicator.setPixmap(qta.icon('fa5s.volume-up', color='#FF0000').pixmap(14, 14))
        else:
            indicator.setPixmap(qta.icon('fa5s.grip-vertical', color='#666').pixmap(14, 14))

        indicator.setFixedWidth(20)
        indicator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        indicator.setCursor(Qt.OpenHandCursor)

        return indicator

    def _create_thumbnail(self):
        """Song thumbnail"""
        thumb = QLabel()
        thumb.setFixedSize(40, 40)
        thumb.setPixmap(qta.icon('fa5s.music', color='#666').pixmap(40, 40))
        thumb.setScaledContents(True)
        thumb.setStyleSheet("border-radius: 4px; background: #1a1a1a;")
        thumb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return thumb

    def _create_info_layout(self):
        """Song information layout"""
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        self.title_label = QLabel(self.full_title)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.title_label.setWordWrap(False)
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.title_label.setTextFormat(Qt.PlainText)
        self.title_label.setTextInteractionFlags(Qt.NoTextInteraction)

        # Artist
        self.artist_label = QLabel(self.full_artist)
        self.artist_label.setStyleSheet("color: #999; font-size: 11px;")
        self.artist_label.setWordWrap(False)
        self.artist_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.artist_label.setTextInteractionFlags(Qt.NoTextInteraction)

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)

        return info_layout

    def _create_action_buttons(self):
        """Create play and remove buttons"""
        buttons_container = QWidget()
        buttons_container.setFixedWidth(64)
        buttons_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(4)

        # Play button
        btn_play = self._create_icon_button(
            qta.icon('fa5s.play', color='white'),
            lambda: self.play_clicked.emit(self.index)
        )

        # Remove button
        btn_remove = self._create_icon_button(
            qta.icon('fa5s.times', color='#999'),
            lambda: self.remove_clicked.emit(self.index),
            hover_style="background: rgba(255,0,0,0.2);"
        )

        buttons_layout.addWidget(btn_play)
        buttons_layout.addWidget(btn_remove)

        return buttons_container

    def _create_icon_button(self, icon, callback, hover_style=None):
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setFixedSize(28, 28)
        btn.clicked.connect(callback)
        btn.setCursor(Qt.PointingHandCursor)

        base_style = """
            QPushButton { 
                border: none; 
                border-radius: 14px; 
                background: transparent; 
            }
        """

        if hover_style:
            base_style += f"QPushButton:hover {{ {hover_style} }}"
        else:
            base_style += "QPushButton:hover { background: rgba(255,255,255,0.1); }"

        btn.setStyleSheet(base_style)
        return btn

    def _apply_styling(self):
        """Apply styling based on current state"""
        bg_color = "rgba(255,0,0,0.08)" if self.is_current else "transparent"
        border_color = "rgba(255,0,0,0.3)" if self.is_current else "transparent"

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

    # Drag and drop events
    def mousePressEvent(self, event):
        """Mouse press for drag start"""
        if event.button() == Qt.LeftButton:
            if self.play_indicator.geometry().contains(event.pos()):
                self.drag_start_position = event.pos()
                self.play_indicator.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Mouse move for dragging"""
        if not (event.buttons() & Qt.LeftButton):
            return

        if self.drag_start_position is None:
            return

        # Check if drag threshold is met
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return

        self._start_drag(event)

    def _start_drag(self, event):
        """Start the drag operation"""
        from PySide6.QtCore import QMimeData

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.index))
        drag.setMimeData(mime_data)

        # Set drag pixmap
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        drag.exec(Qt.MoveAction)

        self.play_indicator.setCursor(Qt.OpenHandCursor)
        self.drag_start_position = None

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.play_indicator.setCursor(Qt.OpenHandCursor)
        self.drag_start_position = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """Handle resize to truncate text"""
        super().resizeEvent(event)

        available_width = self.width() - 156

        if available_width > 50:
            font_metrics = self.title_label.fontMetrics()

            elided_title = font_metrics.elidedText(
                self.full_title, Qt.ElideRight, available_width
            )
            self.title_label.setText(elided_title)

            elided_artist = font_metrics.elidedText(
                self.full_artist, Qt.ElideRight, available_width
            )
            self.artist_label.setText(elided_artist)


# ============================================================================
# CUSTOM WIDGETS - DROPPABLE QUEUE CONTAINER
# ============================================================================

class DroppableQueueContainer(QWidget):
    """Container widget that accepts drops for queue reordering"""

    item_dropped = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.drag_source_index = -1
        self.drop_indicator_pos = -1

    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move to show drop indicator"""
        if event.mimeData().hasText():
            pos = event.position().toPoint()
            self.drop_indicator_pos = self._get_drop_position(pos)
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self.drop_indicator_pos = -1
        self.update()

    def dropEvent(self, event):
        """Handle drop to reorder queue"""
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
        """Calculate drop position based on mouse position"""
        layout = self.layout()
        if not layout:
            return -1

        count = layout.count() - 1  # Exclude stretch

        for i in range(count):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                widget_rect = widget.geometry()

                if widget_rect.contains(pos):
                    mid_point = widget_rect.top() + widget_rect.height() // 2
                    return i if pos.y() < mid_point else i + 1

        return count

    def paintEvent(self, event):
        """Paint drop indicator line"""
        super().paintEvent(event)

        if self.drop_indicator_pos >= 0:
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


# Icon

class IconManager:
    """Icon management"""

    def __init__(self):
        self._icons = {}
        self._initialize_icons()

    def _initialize_icons(self):
        """Application icons"""
        icon_definitions = {
            'play': ('fa5s.play', 'white'),
            'pause': ('fa5s.pause', 'white'),
            'next': ('fa5s.step-forward', 'white'),
            'prev': ('fa5s.step-backward', 'white'),
            'search': ('fa5s.search', 'white'),
            'volume': ('fa5s.volume-up', 'white'),
            'trash': ('fa5s.trash', 'white'),
            'clear': ('fa5s.broom', 'white'),
            'login': ('fa5s.user-circle', 'white'),
            'login_active': ('fa5s.user-circle', '#FF0000'),
            'import': ('fa5s.file-import', 'white'),
            'loop_off': ('fa5s.sync-alt', 'gray'),
            'loop_queue': ('fa5s.sync-alt', '#FF0000'),
            'loop_song': ('fa5s.redo', '#FF0000'),
            'autoplay_off': ('fa5s.magic', 'gray'),
            'autoplay_on': ('fa5s.magic', '#FF0000'),
            'lyrics': ('fa5s.microphone-alt', 'white'),
            'lyrics_active': ('fa5s.microphone-alt', '#FF0000'),
            'lyrics_inactive': ('fa5s.microphone-alt', 'gray'),
            'home': ('fa5s.home', 'white'),
            'library': ('fa5s.music', 'white'),
            'explore': ('fa5s.compass', 'white'),
            'playlist': ('fa5s.list', 'white'),
        }

        for name, (icon_name, color) in icon_definitions.items():
            self._icons[name] = qta.icon(icon_name, color=color)

    def get(self, name):
        """Get icon by name"""
        return self._icons.get(name)


# Main window

class MainWindow(QWidget):
    def __init__(self, on_search, on_select_song, on_add_to_queue, on_toggle_play,
                 on_add_next, on_volume_change, on_seek, on_next, on_previous,
                 on_remove_from_queue, on_queue_item_selected, on_login_requested,
                 on_playlist_selected, on_import_playlist, app_icon,
                 on_save_imported_playlist, on_result_highlighted, on_queue_item_moved,
                 on_toggle_loop, on_logout_requested, on_toggle_autoplay,
                 on_show_lyrics_requested, on_home_requested, on_clear_queue):
        super().__init__()

        # Store callbacks
        self.callbacks = {
            'search': on_search,
            'select_song': on_select_song,
            'add_to_queue': on_add_to_queue,
            'add_next': on_add_next,
            'toggle_play': on_toggle_play,
            'volume_change': on_volume_change,
            'seek': on_seek,
            'next': on_next,
            'previous': on_previous,
            'remove_from_queue': on_remove_from_queue,
            'queue_item_selected': on_queue_item_selected,
            'login_requested': on_login_requested,
            'playlist_selected': on_playlist_selected,
            'import_playlist': on_import_playlist,
            'save_imported_playlist': on_save_imported_playlist,
            'result_highlighted': on_result_highlighted,
            'queue_item_moved': on_queue_item_moved,
            'toggle_loop': on_toggle_loop,
            'logout_requested': on_logout_requested,
            'toggle_autoplay': on_toggle_autoplay,
            'show_lyrics': on_show_lyrics_requested,
            'home': on_home_requested,
            'clear_queue': on_clear_queue,
        }

        # State
        self.is_logged_in = False
        self.app_icon = app_icon

        # Icons
        self.icons = IconManager()

        # UI
        self._setup_window()
        self._create_ui()
        self._apply_styles()
        self._setup_shortcuts()
        self._init_system_tray()

        # Cargar home al inicio
        QTimer.singleShot(100, self._load_initial_home)

    def _setup_window(self):
        """window properties"""
        self.setWindowIcon(self.app_icon)
        self.setWindowTitle("YouTube Music - Minimal Client")

    def _create_ui(self):
        """Main UI layout"""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Top bar
        top_bar = TopBar(self.icons, self)
        top_bar.search_requested.connect(self._on_search)
        top_bar.login_clicked.connect(self._on_login_clicked)
        self.top_bar = top_bar
        outer_layout.addWidget(top_bar)

        # Central content
        central_split = self._create_central_area()
        outer_layout.addWidget(central_split, stretch=1)

        # Player controls
        player_widget = PlayerWidget(self.icons, self)
        player_widget.toggle_play_clicked.connect(self._call('toggle_play'))
        player_widget.volume_changed.connect(self._call('volume_change'))
        player_widget.seek_requested.connect(self._call('seek'))
        player_widget.next_clicked.connect(self._call('next'))
        player_widget.previous_clicked.connect(self._call('previous'))
        player_widget.loop_clicked.connect(self._call('toggle_loop'))
        player_widget.autoplay_clicked.connect(self._call('toggle_autoplay'))
        player_widget.lyrics_clicked.connect(self._call('show_lyrics'))
        self.player_widget = player_widget
        outer_layout.addWidget(player_widget)

    def _create_central_area(self):
        """The central split area with sidebar, center, and right panel"""
        central_split = QSplitter(Qt.Horizontal)
        central_split.setHandleWidth(1)

        # Sidebar
        sidebar = Sidebar(self.icons, self)
        sidebar.home_clicked.connect(self._on_home_clicked)
        sidebar.explore_clicked.connect(self._on_explore_clicked)
        sidebar.library_clicked.connect(self._on_library_clicked)
        sidebar.import_clicked.connect(self._on_import_playlist_clicked)
        self.sidebar = sidebar
        central_split.addWidget(sidebar)

        # Center area (search results)
        center_widget = CenterPanel(self)
        center_widget.song_selected.connect(self._on_song_selected)
        center_widget.result_highlighted.connect(self._call('result_highlighted'))
        center_widget.add_to_queue.connect(self._call('add_to_queue'))
        center_widget.add_next.connect(self._call('add_next'))
        self.center_panel = center_widget
        central_split.addWidget(center_widget)

        # Right panel (queue + lyrics)
        right_panel = RightPanel(self.icons, self)
        right_panel.playlist_selected.connect(self._call('playlist_selected'))
        right_panel.queue_item_selected.connect(self._call('queue_item_selected'))
        right_panel.queue_item_removed.connect(self._call('remove_from_queue'))
        right_panel.queue_item_moved.connect(self._call('queue_item_moved'))
        right_panel.clear_queue_clicked.connect(self._on_clear_queue)
        self.right_panel = right_panel

        central_split.addWidget(right_panel)
        central_split.setSizes([180, 600, 320])

        return central_split

    def _call(self, callback_name):
        """get a callback function"""
        return lambda *args: self.callbacks[callback_name](*args) if self.callbacks[callback_name] else None

    def _setup_shortcuts(self):
        """keyboard shortcuts"""
        quit_action = QAction("Salir", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

    def _init_system_tray(self):
        """system tray icon"""
        self.tray_icon = SystemTrayManager(self.app_icon, self.icons, self)
        self.tray_icon.show_window.connect(self.showNormal)
        self.tray_icon.play_pause.connect(self._call('toggle_play'))
        self.tray_icon.next_song.connect(self._call('next'))
        self.tray_icon.previous_song.connect(self._call('previous'))
        self.tray_icon.quit_app.connect(QApplication.instance().quit)
        self.tray_icon.show()

    def _load_initial_home(self):
        """Cargar el home al inicio"""
        if self.callbacks['home']:
            self.callbacks['home']()

    # Event handlers

    def _on_search(self, query):
        """search request"""
        if self.callbacks['search']:
            self.callbacks['search'](query)

    def _on_song_selected(self, index):
        """song selection from results"""
        if self.callbacks['select_song']:
            self.callbacks['select_song'](index)

    def _on_login_clicked(self):
        """login button click"""
        LoginDialog(self).exec(
            self.is_logged_in,
            self.callbacks['login_requested'],
            self.callbacks['logout_requested']
        )

    def _on_home_clicked(self):
        """home button click"""
        if self.callbacks['home']:
            self.callbacks['home']()

    def _on_explore_clicked(self):
        """explore button click"""
        if self.callbacks['search']:
            self.callbacks['search']("top hits")

    def _on_library_clicked(self):
        """library button click"""
        self.right_panel.show_library_tab()

    def _on_import_playlist_clicked(self):
        """import playlist button click"""
        url, ok = QInputDialog.getText(self, "Importar Playlist", "Pega la URL:")
        if ok and url and self.callbacks['import_playlist']:
            self.callbacks['import_playlist'](url)

    def _on_clear_queue(self):
        """clear queue request"""
        reply = QMessageBox.question(
            self,
            "Limpiar Cola",
            "¿Eliminar todas las canciones excepto la actual?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes and self.callbacks['clear_queue']:
            self.callbacks['clear_queue']()

    # Public update methods
    def update_results(self, results):
        self.center_panel.update_results(results)

    def update_queue(self, queue, current_index):
        self.right_panel.update_queue(queue, current_index)

    def update_playlists(self, playlists):
        self.right_panel.update_playlists(playlists)

    def update_song_info(self, text):
        self.player_widget.update_song_info(text)

    def update_play_button_icon(self, is_playing):
        self.player_widget.update_play_button(is_playing)
        self.tray_icon.update_play_pause_action(is_playing)

    def update_loop_button_icon(self, mode):
        self.player_widget.update_loop_button(mode)

    def update_autoplay_button_icon(self, enabled):
        self.player_widget.update_autoplay_button(enabled)

    def update_progress(self, pos):
        self.player_widget.update_progress(pos)

    def update_time(self, current, total):
        self.player_widget.update_time(current, total)

    def update_auth_status(self, is_authenticated):
        self.is_logged_in = is_authenticated
        self.top_bar.update_auth_status(is_authenticated)

    def set_lyrics_lines(self, lines):
        self.right_panel.set_lyrics_lines(lines)
        self.player_widget.set_lyrics_active(True)

    def set_lyrics_message(self, message, switch_focus=False):
        self.right_panel.set_lyrics_message(message, switch_focus)
        self.player_widget.set_lyrics_active(False)

    def highlight_lyric_index(self, index):
        self.right_panel.highlight_lyric_index(index)

    def show_home(self, sections):
        self.center_panel.show_home(sections)

    def ask_to_save_playlist(self, title, auth):
        """Ask where to save imported playlist"""
        SavePlaylistDialog(self).exec(
            title,
            auth,
            self.callbacks['save_imported_playlist']
        )

    # Message dialogs
    def show_import_error(self, message):
        QMessageBox.warning(self, "Error al Importar Playlist", message)

    def show_save_playlist_success(self, title, location):
        QMessageBox.information(self, "Éxito", f"'{title}' guardada en {location}")

    def show_save_playlist_error(self, title):
        QMessageBox.warning(self, "Error", f"No se pudo guardar '{title}'")

    def show_auth_success(self):
        QMessageBox.information(self, "Éxito", "Sesión iniciada correctamente")

    def show_auth_error(self):
        QMessageBox.warning(self, "Error", "No se pudo iniciar sesión")

    # Window events
    def closeEvent(self, event):
        """window close"""
        event.ignore()
        self.hide()
        self.tray_icon.show_message(
            "Minimizado",
            "Reproduciendo en 2do plano.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def _apply_styles(self):
        """Apply application stylesheet"""
        self.setStyleSheet(StyleSheet.get())


# Top bar

class TopBar(QWidget):
    """Top navigation bar with search and login"""

    search_requested = Signal(str)
    login_clicked = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self._setup_ui()

    def _setup_ui(self):
        """UI"""
        self.setObjectName("top_bar")
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        # Logo
        logo_label = QLabel("YouTube Music")
        logo_label.setObjectName("logo_label")
        logo_label.setFixedWidth(150)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar canción, artista, álbum...")
        self.search_box.returnPressed.connect(self._on_search)
        self.search_box.setFixedHeight(38)
        self.search_box.setMaximumWidth(500)

        # Search button
        search_button = QPushButton()
        search_button.setIcon(self.icons.get('search'))
        search_button.clicked.connect(self._on_search)
        search_button.setFixedSize(38, 38)
        search_button.setCursor(Qt.PointingHandCursor)

        # Login button
        self.login_button = QPushButton()
        self.login_button.setIcon(self.icons.get('login'))
        self.login_button.setToolTip("Iniciar Sesión")
        self.login_button.setFixedSize(38, 38)
        self.login_button.clicked.connect(self.login_clicked.emit)
        self.login_button.setCursor(Qt.PointingHandCursor)

        layout.addWidget(logo_label)
        layout.addStretch()
        layout.addWidget(self.search_box)
        layout.addWidget(search_button)
        layout.addSpacing(16)
        layout.addWidget(self.login_button)

    def _on_search(self):
        """search"""
        text = self.search_box.text().strip()
        if text:
            self.search_requested.emit(text)

    def update_auth_status(self, is_authenticated):
        """Update login button based on auth status"""
        icon = self.icons.get('login_active' if is_authenticated else 'login')
        tooltip = "Cerrar sesión" if is_authenticated else "Iniciar sesión"
        self.login_button.setIcon(icon)
        self.login_button.setToolTip(tooltip)


# Sidebar

class Sidebar(QWidget):
    """Left sidebar with navigation"""

    home_clicked = Signal()
    explore_clicked = Signal()
    library_clicked = Signal()
    import_clicked = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self._setup_ui()

    def _setup_ui(self):
        """UI"""
        self.setObjectName("sidebar")
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(4)

        # Navigation buttons
        nav_config = [
            ("Inicio", 'home', self.home_clicked),
            ("Explorar", 'explore', self.explore_clicked),
            ("Biblioteca", 'library', self.library_clicked),
        ]

        for text, icon_name, signal in nav_config:
            btn = self._create_nav_button(text, icon_name)
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)

        layout.addSpacing(16)

        # Import button
        import_btn = self._create_nav_button("Importar Playlist", 'import')
        import_btn.clicked.connect(self.import_clicked.emit)
        layout.addWidget(import_btn)

        layout.addStretch()

    def _create_nav_button(self, text, icon_name):
        btn = QPushButton(text)
        btn.setIcon(self.icons.get(icon_name))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(40)
        return btn


# Center panel

class CenterPanel(QWidget):
    """search results"""

    song_selected = Signal(int)
    result_highlighted = Signal(int)
    add_to_queue = Signal(int)
    add_next = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.home_scroll = None  # INICIALIZAR AQUÍ
        self._setup_ui()

    def _setup_ui(self):
        """UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        search_info = QLabel("Resultados de Búsqueda")
        search_info.setObjectName("search_info")
        search_info.setStyleSheet("font-weight: bold; font-size: 14px;")

        # Results list
        self.results_list = QListWidget()
        self.results_list.setObjectName("results_list")
        self.results_list.setSpacing(8)
        self.results_list.itemDoubleClicked.connect(
            lambda: self.song_selected.emit(self.results_list.currentRow())
        )
        self.results_list.currentItemChanged.connect(self._on_item_changed)
        self.results_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(search_info)
        layout.addWidget(self.results_list)

    def _on_item_changed(self, current, previous):
        if self.results_list.currentRow() >= 0:
            self.result_highlighted.emit(self.results_list.currentRow())

    def _show_context_menu(self, pos):
        """context menu for results"""
        if not self.results_list.itemAt(pos):
            return

        menu = QMenu(self)
        play_action = menu.addAction(qta.icon('fa5s.play', color='white'), "Reproducir ahora")
        add_next_action = menu.addAction(qta.icon('fa5s.level-down-alt', color='white'), "Siguiente")
        add_queue_action = menu.addAction(qta.icon('fa5s.plus', color='white'), "Agregar a cola")

        action = menu.exec(self.results_list.mapToGlobal(pos))
        current_row = self.results_list.currentRow()

        if action == play_action:
            self.song_selected.emit(current_row)
        elif action == add_next_action:
            self.add_next.emit(current_row)
        elif action == add_queue_action:
            self.add_to_queue.emit(current_row)

    def update_results(self, results):
        """Update search results"""
        # Mostrar lista de resultados y ocultar home
        if self.home_scroll:
            self.home_scroll.hide()
        self.results_list.show()

        self.results_list.clear()

        for song in results:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 76))
            widget = self._create_track_widget(song)
            self.results_list.addItem(item)
            self.results_list.setItemWidget(item, widget)

    def _create_track_widget(self, song):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # Thumbnail
        thumb = QLabel()
        thumb.setFixedSize(56, 56)
        thumb.setPixmap(qta.icon('fa5s.music', color='#666').pixmap(56, 56))
        thumb.setScaledContents(True)
        thumb.setStyleSheet("border-radius: 6px; background: #1a1a1a;")

        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        title = QLabel(song.get('title', 'Desconocido'))
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        title.setWordWrap(False)

        artists = song.get('artists', [])
        artist_text = ", ".join([a.get('name', '') for a in artists]) if artists else "Desconocido"
        artist = QLabel(artist_text)
        artist.setStyleSheet("color: #999; font-size: 12px;")
        artist.setWordWrap(False)

        info_layout.addWidget(title)
        info_layout.addWidget(artist)

        layout.addWidget(thumb)
        layout.addLayout(info_layout, stretch=1)

        return widget

    def show_home(self, sections):
        """Home"""
        self.results_list.hide()
        if self.home_scroll:
            self.layout().removeWidget(self.home_scroll)
            self.home_scroll.deleteLater()
            self.home_scroll = None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(24)

        for section in sections:
            title = section.get("title", "Sección")
            items = section.get("items", [])

            # Header
            title_label = QLabel(title)
            title_label.setStyleSheet("font-size:18px; font-weight:700;")
            main_layout.addWidget(title_label)

            # Horizontal scroll
            h_scroll = QScrollArea()
            h_scroll.setWidgetResizable(True)
            h_scroll.setFixedHeight(220)
            h_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            h_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            h_scroll.setFrameShape(QFrame.NoFrame)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(6, 6, 6, 6)
            row_layout.setSpacing(12)

            for item in items:
                card = self._create_home_card(item)
                row_layout.addWidget(card)

            row_layout.addStretch()
            h_scroll.setWidget(row_widget)

            main_layout.addWidget(h_scroll)

        scroll.setWidget(container)

        self.home_scroll = scroll
        self.layout().addWidget(scroll)
        scroll.show()

    def _create_home_card(self, item):
        card = QWidget()
        card.setFixedSize(160, 200)
        card.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Cover
        img = QLabel()
        img.setFixedSize(148, 148)
        img.setScaledContents(True)
        img.setStyleSheet("""
            background:#1e1e1e;
            border-radius:10px;
        """)

        img.setPixmap(qta.icon('fa5s.music', color='#555').pixmap(148, 148))

        # Título
        title = QLabel(item.get("title", ""))
        title.setStyleSheet("font-size:13px; font-weight:600;")
        title.setWordWrap(False)
        title.setFixedHeight(18)

        # Subtítulo
        subtitle_text = ""
        if item.get("type") == "song":
            artists = item.get("artists", [])
            if artists:
                subtitle_text = ", ".join([a.get("name", "") for a in artists[:2]])
        else:
            subtitle_text = item.get("type", "").capitalize()

        subtitle = QLabel(subtitle_text)
        subtitle.setStyleSheet("font-size:11px; color:#999;")
        subtitle.setFixedHeight(16)

        layout.addWidget(img)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Click
        def on_click(event):
            self._handle_home_click(item)

        card.mousePressEvent = on_click

        return card

    def _handle_home_click(self, item):
        """Manejar click en items del home"""
        item_type = item.get("type")

        # Buscar el MainWindow parent
        parent_widget = self.parent()
        while parent_widget and not isinstance(parent_widget, MainWindow):
            parent_widget = parent_widget.parent()

        if not parent_widget:
            print("[HOME] No se encontró MainWindow")
            return

        if item_type == "song":
            video_id = item.get("videoId")
            if video_id and parent_widget.callbacks.get("select_song"):
                # Aquí deberíamos buscar el índice en results_cache, pero como
                # estamos en home, podemos agregar directamente a la cola
                print(f"[HOME] Reproduciendo canción: {item.get('title')}")
                # Por ahora solo imprimimos, necesitarías adaptar esto

        elif item_type == "playlist":
            playlist_id = item.get("playlistId")
            if playlist_id and parent_widget.callbacks.get("playlist_selected"):
                print(f"[HOME] Abriendo playlist: {item.get('title')}")
                # Necesitarías encontrar el índice de la playlist

        elif item_type == "album":
            album_id = item.get("browseId")
            if album_id:
                print(f"[HOME] Abriendo álbum: {item.get('title')}")


# Right panel

class RightPanel(QWidget):
    """queue and lyrics"""

    playlist_selected = Signal(int)
    queue_item_selected = Signal(int)
    queue_item_removed = Signal(int)
    queue_item_moved = Signal(int, int)
    clear_queue_clicked = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self._setup_ui()

    def _setup_ui(self):
        """UI"""
        self.setObjectName("right_panel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 8, 8)
        layout.setSpacing(8)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("right_tabs")

        # Library tab (playlists + queue)
        library_tab = self._create_library_tab()
        self.tabs.addTab(library_tab, self.icons.get('library'), "Biblioteca")

        # Lyrics tab
        lyrics_tab = self._create_lyrics_tab()
        self.tabs.addTab(lyrics_tab, self.icons.get('lyrics'), "Letra")

        layout.addWidget(self.tabs)

    def _create_library_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Playlists section (collapsible)
        playlists_section = CollapsibleSection("Mis Playlists")
        playlists_section.is_collapsed = True
        playlists_section.content.setVisible(False)
        playlists_section.toggle_button.setIcon(qta.icon('fa5s.chevron-right', color='white'))

        self.playlists_list = QListWidget()
        self.playlists_list.setObjectName("compact_list")
        self.playlists_list.setMaximumHeight(150)
        self.playlists_list.itemDoubleClicked.connect(
            lambda: self.playlist_selected.emit(self.playlists_list.currentRow())
        )
        playlists_section.add_content(self.playlists_list)
        layout.addWidget(playlists_section)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background: #333; max-height: 1px;")
        layout.addWidget(separator)

        # Queue header
        queue_header = self._create_queue_header()
        layout.addWidget(queue_header)

        # Queue list
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.NoFrame)
        self.queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.queue_container = DroppableQueueContainer()
        self.queue_container.item_dropped.connect(self.queue_item_moved.emit)

        self.queue_layout = QVBoxLayout(self.queue_container)
        self.queue_layout.setContentsMargins(0, 0, 0, 0)
        self.queue_layout.setSpacing(4)
        self.queue_layout.addStretch()

        self.queue_scroll.setWidget(self.queue_container)
        layout.addWidget(self.queue_scroll, stretch=10)

        return tab

    def _create_queue_header(self):
        """queue section header"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Cola de Reproducción")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.queue_count_label = QLabel("(0)")
        self.queue_count_label.setStyleSheet("color: #999; font-size: 12px;")

        clear_btn = QPushButton()
        clear_btn.setIcon(self.icons.get('clear'))
        clear_btn.setToolTip("Limpiar cola")
        clear_btn.setFixedSize(28, 28)
        clear_btn.clicked.connect(self.clear_queue_clicked.emit)
        clear_btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                border-radius: 14px; 
                background: transparent; 
            }
            QPushButton:hover { background: rgba(255,0,0,0.2); }
        """)

        layout.addWidget(title)
        layout.addWidget(self.queue_count_label)
        layout.addStretch()
        layout.addWidget(clear_btn)

        return header

    def _create_lyrics_tab(self):
        """lyrics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.lyrics_list = QListWidget()
        self.lyrics_list.setObjectName("lyrics_list")
        layout.addWidget(self.lyrics_list)

        return tab

    def update_queue(self, queue, current_index):
        """Update queue display"""
        # Clear existing items
        while self.queue_layout.count() > 1:  # Keep stretch
            item = self.queue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Update counter
        self.queue_count_label.setText(f"({len(queue)})")

        # Add queue items
        for i, song in enumerate(queue):
            is_current = (i == current_index)
            item_widget = ImprovedQueueItem(song, i, is_current)

            item_widget.play_clicked.connect(self.queue_item_selected.emit)
            item_widget.remove_clicked.connect(self.queue_item_removed.emit)

            self.queue_layout.insertWidget(i, item_widget)

        # Scroll to current
        if 0 <= current_index < len(queue):
            QTimer.singleShot(100, lambda: self._scroll_to_index(current_index))

    def _scroll_to_index(self, index):
        """Scroll to specific queue item"""
        if 0 <= index < self.queue_layout.count() - 1:
            widget = self.queue_layout.itemAt(index).widget()
            if widget:
                self.queue_scroll.ensureWidgetVisible(widget)

    def update_playlists(self, playlists):
        """Update playlists list"""
        self.playlists_list.clear()

        if not playlists:
            self.playlists_list.addItem("Inicia sesión para ver playlists")
            return

        for playlist in playlists:
            self.playlists_list.addItem(f"  {playlist.get('title', 'Sin título')}")

    def set_lyrics_lines(self, lines):
        """Display lyrics lines"""
        self.lyrics_list.clear()

        for line in lines:
            item = QListWidgetItem(line)
            item.setTextAlignment(Qt.AlignCenter)
            self.lyrics_list.addItem(item)

    def set_lyrics_message(self, message, switch_focus=False):
        """Display lyrics message"""
        self.lyrics_list.clear()

        item = QListWidgetItem(message)
        item.setTextAlignment(Qt.AlignCenter)
        self.lyrics_list.addItem(item)

        if switch_focus:
            self.tabs.setCurrentIndex(1)  # Switch to lyrics tab

    def highlight_lyric_index(self, index):
        """Highlight a lyric line"""
        if 0 <= index < self.lyrics_list.count():
            self.lyrics_list.setCurrentRow(index)
            self.lyrics_list.scrollToItem(
                self.lyrics_list.item(index),
                QListWidget.PositionAtCenter
            )

    def show_library_tab(self):
        self.tabs.setCurrentIndex(0)


# Player widget

class PlayerWidget(QWidget):
    """Bottom player controls"""

    toggle_play_clicked = Signal()
    volume_changed = Signal(int)
    seek_requested = Signal(float)
    next_clicked = Signal()
    previous_clicked = Signal()
    loop_clicked = Signal()
    autoplay_clicked = Signal()
    lyrics_clicked = Signal()

    def __init__(self, icons, parent=None):
        super().__init__(parent)
        self.icons = icons
        self._setup_ui()

    def _setup_ui(self):
        """UI"""
        self.setObjectName("player_widget")
        self.setFixedHeight(170)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Song info row
        info_row = self._create_info_row()
        layout.addLayout(info_row)

        # Progress bar
        progress_row = self._create_progress_row()
        layout.addLayout(progress_row)

        # Controls
        controls_row = self._create_controls_row()
        layout.addLayout(controls_row)

    def _create_info_row(self):
        """song info display"""
        layout = QHBoxLayout()

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(56, 56)
        self.cover_label.setPixmap(self.icons.get('library').pixmap(56, 56))
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet("border-radius: 6px; background: #1a1a1a;")

        self.song_label = QLabel("Sin reproducción")
        self.song_label.setObjectName("song_label")
        self.song_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(self.cover_label)
        layout.addSpacing(12)
        layout.addWidget(self.song_label)
        layout.addStretch()

        return layout

    def _create_progress_row(self):
        """progress bar with time labels"""
        layout = QHBoxLayout()

        self.time_label = QLabel("0:00")
        self.time_label.setFixedWidth(45)
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderMoved.connect(
            lambda val: self.seek_requested.emit(val / 1000.0)
        )

        self.total_time_label = QLabel("0:00")
        self.total_time_label.setFixedWidth(45)

        layout.addWidget(self.time_label)
        layout.addWidget(self.progress_slider, stretch=1)
        layout.addWidget(self.total_time_label)

        return layout

    def _create_controls_row(self):
        """playback controls"""
        layout = QHBoxLayout()

        # Left controls (playback)
        left_controls = self._create_playback_controls()

        # Right controls (volume, etc.)
        right_controls = self._create_secondary_controls()

        layout.addLayout(left_controls, stretch=3)
        layout.addLayout(right_controls, stretch=2)

        return layout

    def _create_playback_controls(self):
        """main playback buttons"""
        layout = QHBoxLayout()
        layout.addStretch()

        self.prev_button = QPushButton()
        self.prev_button.setIcon(self.icons.get('prev'))
        self.prev_button.clicked.connect(self.previous_clicked.emit)
        self.prev_button.setFixedSize(42, 42)
        self.prev_button.setCursor(Qt.PointingHandCursor)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.icons.get('play'))
        self.play_button.clicked.connect(self.toggle_play_clicked.emit)
        self.play_button.setFixedSize(52, 52)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setObjectName("play_button")

        self.next_button = QPushButton()
        self.next_button.setIcon(self.icons.get('next'))
        self.next_button.clicked.connect(self.next_clicked.emit)
        self.next_button.setFixedSize(42, 42)
        self.next_button.setCursor(Qt.PointingHandCursor)

        layout.addWidget(self.prev_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.next_button)
        layout.addStretch()

        return layout

    def _create_secondary_controls(self):
        """secondary controls (lyrics, loop, autoplay, volume)"""
        layout = QHBoxLayout()

        self.lyrics_button = QPushButton()
        self.lyrics_button.setIcon(self.icons.get('lyrics'))
        self.lyrics_button.setToolTip("Ver letra")
        self.lyrics_button.clicked.connect(self.lyrics_clicked.emit)
        self.lyrics_button.setFixedSize(36, 36)
        self.lyrics_button.setCursor(Qt.PointingHandCursor)

        self.loop_button = QPushButton()
        self.loop_button.setIcon(self.icons.get('loop_off'))
        self.loop_button.setToolTip("Repetir")
        self.loop_button.clicked.connect(self.loop_clicked.emit)
        self.loop_button.setFixedSize(36, 36)
        self.loop_button.setCursor(Qt.PointingHandCursor)

        self.autoplay_button = QPushButton()
        self.autoplay_button.setIcon(self.icons.get('autoplay_off'))
        self.autoplay_button.setToolTip("Autoplay")
        self.autoplay_button.clicked.connect(self.autoplay_clicked.emit)
        self.autoplay_button.setFixedSize(36, 36)
        self.autoplay_button.setCursor(Qt.PointingHandCursor)

        vol_icon = QLabel()
        vol_icon.setPixmap(self.icons.get('volume').pixmap(20, 20))

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(120)
        self.volume_slider.valueChanged.connect(self.volume_changed.emit)

        layout.addWidget(self.lyrics_button)
        layout.addWidget(self.loop_button)
        layout.addWidget(self.autoplay_button)
        layout.addSpacing(12)
        layout.addWidget(vol_icon)
        layout.addWidget(self.volume_slider)

        return layout

    # Update methods
    def update_song_info(self, text):
        self.song_label.setText(f"  {text}")

    def update_play_button(self, is_playing):
        icon = self.icons.get('pause' if is_playing else 'play')
        self.play_button.setIcon(icon)

    def update_loop_button(self, mode):
        icons = {
            0: self.icons.get('loop_off'),
            1: self.icons.get('loop_queue'),
            2: self.icons.get('loop_song')
        }
        tooltips = {
            0: "Repetir (Apagado)",
            1: "Repetir Cola",
            2: "Repetir Canción"
        }
        self.loop_button.setIcon(icons.get(mode, self.icons.get('loop_off')))
        self.loop_button.setToolTip(tooltips.get(mode, "Repetir"))

    def update_autoplay_button(self, enabled):
        icon = self.icons.get('autoplay_on' if enabled else 'autoplay_off')
        self.autoplay_button.setIcon(icon)

    def update_progress(self, position):
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(int(position * 1000))
        self.progress_slider.blockSignals(False)

    def update_time(self, current, total):
        self.time_label.setText(self._format_time(current))
        self.total_time_label.setText(self._format_time(total))

    def set_lyrics_active(self, active):
        icon = self.icons.get('lyrics_active' if active else 'lyrics_inactive')
        self.lyrics_button.setIcon(icon)

    @staticmethod
    def _format_time(seconds):
        """Format seconds to MM:SS"""
        return f"{seconds // 60}:{seconds % 60:02d}"


# system tray

class SystemTrayManager(QSystemTrayIcon):
    """System tray icon manager"""

    show_window = Signal()
    play_pause = Signal()
    next_song = Signal()
    previous_song = Signal()
    quit_app = Signal()

    def __init__(self, app_icon, icons, parent=None):
        super().__init__(app_icon, parent)
        self.icons = icons
        self.setToolTip("YTMusic Client")
        self._create_menu()
        self.activated.connect(self._on_activated)

    def _create_menu(self):
        menu = QMenu()

        menu.addAction("Mostrar").triggered.connect(self.show_window.emit)
        menu.addSeparator()

        self.play_pause_action = menu.addAction("Reproducir")
        self.play_pause_action.triggered.connect(self.play_pause.emit)

        menu.addAction(self.icons.get('prev'), "Anterior").triggered.connect(
            self.previous_song.emit
        )
        menu.addAction(self.icons.get('next'), "Siguiente").triggered.connect(
            self.next_song.emit
        )

        menu.addSeparator()
        menu.addAction("Salir").triggered.connect(self.quit_app.emit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window.emit()

    def update_play_pause_action(self, is_playing):
        self.play_pause_action.setText("⏸ Pausar" if is_playing else "▶ Reproducir")

    def show_message(self, title, message, icon, duration):
        self.showMessage(title, message, icon, duration)


# Dialogs

class LoginDialog:

    def __init__(self, parent):
        self.parent = parent

    def exec(self, is_logged_in, on_login, on_logout):
        """Execute login/logout dialog"""
        if is_logged_in:
            self._logout_dialog(on_logout)
        else:
            self._login_dialog(on_login)

    def _logout_dialog(self, on_logout):
        """Show logout confirmation"""
        reply = QMessageBox.question(
            self.parent,
            "Cerrar Sesión",
            "¿Cerrar la sesión actual?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes and on_logout:
            on_logout()

    def _login_dialog(self, on_login):
        """Show login dialog"""
        instructions = """Para iniciar sesión:
1. Abre YouTube Music en tu navegador
2. Inicia sesión con tu cuenta
3. Abre herramientas de desarrollador (F12)
4. Ve a "Red" y recarga (Ctrl+Shift+R)
5. Filtra por "browse"
6. Clic derecho → Copiar como cURL
7. Pega el contenido abajo"""

        text, ok = QInputDialog.getMultiLineText(
            self.parent,
            'Iniciar Sesión',
            instructions
        )

        if ok and text and on_login:
            headers = self._parse_curl_headers(text)
            on_login("\n".join(headers))

    @staticmethod
    def _parse_curl_headers(curl_text):
        """Parse headers from cURL command"""
        headers_list = []

        # Unwrap line continuations
        unwrapped = re.sub(r'[\^\\]\s*\n', ' ', curl_text).replace('\n', ' ')

        # Extract -H headers
        h_matches = re.findall(r"-H\s+(['\"])(.*?)\1", unwrapped)
        if h_matches:
            headers_list.extend([m[1] for m in h_matches])

        # Extract cookie
        c_match = re.search(r"(--cookie|-b)\s+(['\"])(.*?)\2", unwrapped)
        if c_match:
            headers_list.append(f"Cookie: {c_match.group(3)}")

        return headers_list


class SavePlaylistDialog:
    """Save playlist dialog helper"""

    def __init__(self, parent):
        self.parent = parent

    def exec(self, title, is_authenticated, on_save):
        """Execute save playlist dialog"""
        if is_authenticated:
            self._save_with_options(title, on_save)
        else:
            self._save_local_only(title, on_save)

    def _save_with_options(self, title, on_save):
        """Show save options (local or cloud)"""
        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Guardar Playlist")
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"¿Dónde guardar '{title}'?")

        local_btn = msg.addButton("Local", QMessageBox.ActionRole)
        cloud_btn = msg.addButton("YTMusic", QMessageBox.ActionRole)
        msg.addButton("Cancelar", QMessageBox.RejectRole)

        msg.exec()

        if msg.clickedButton() == local_btn:
            on_save(False)
        elif msg.clickedButton() == cloud_btn:
            on_save(True)

    def _save_local_only(self, title, on_save):
        """Show local save confirmation"""
        msg = QMessageBox(self.parent)
        msg.setWindowTitle("Guardar Playlist")
        msg.setIcon(QMessageBox.Question)
        msg.setText(f"¿Guardar '{title}' localmente?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg.exec() == QMessageBox.Yes:
            on_save(False)


# Stylesheet

class StyleSheet:

    @staticmethod
    def get():
        """Complete application stylesheet"""
        return """
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
        """