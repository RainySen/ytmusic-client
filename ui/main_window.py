from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSplitter, QSystemTrayIcon, QVBoxLayout, QWidget

from domain.models import format_seconds
from ui.components import dialogs
from ui.components.album_panel import AlbumPanel
from ui.components.artist_panel import ArtistPanel
from ui.components.explore_panel import ExplorePanel
from ui.components.home_panel import HomePanel
from ui.components.library_browser import LibraryBrowserPanel
from ui.components.now_playing_panel import NowPlayingPanel
from ui.components.player_panel import PlayerPanel
from ui.components.save_to_playlist_dialog import SaveToPlaylistDialog
from ui.components.search_panel import SearchPanel
from ui.components.side_panel import SidePanel
from ui.components.sidebar import Sidebar
from ui.components.toast import Toast
from ui.components.top_bar import TopBar
from ui.imaging import scale_cover
from ui.styles import APP_STYLESHEET

_VIEW_NAV_LABELS = {"home": "Inicio", "explore": "Explorar", "search": "", "library": "Biblioteca",
                    "artist": "", "album": ""}


# ventana principal vistas
class MainWindow(QWidget):
    search_submitted = Signal(str)
    explore_requested = Signal()
    home_requested = Signal()
    library_requested = Signal()
    import_url_submitted = Signal(str)

    view_shown = Signal(str)
    login_requested = Signal()
    logout_requested = Signal()

    play_pause_clicked = Signal()
    next_clicked = Signal()
    previous_clicked = Signal()
    loop_clicked = Signal()
    shuffle_clicked = Signal()
    seek_requested = Signal(float)
    volume_changed = Signal(int)

    save_to_playlist_requested = Signal(dict)
    collection_action_requested = Signal(str, dict)
    queue_clear_confirmed = Signal()
    queue_save_requested = Signal(str)

    def __init__(self, thumbnails, app_icon):
        super().__init__()
        self.thumbnails = thumbnails
        self._app_icon = app_icon
        self._logged_in = False
        self._view = "home"

        self.setWindowIcon(app_icon)
        self.setWindowTitle("YouTube Music - Minimal Client")
        self._load_icons()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_top_bar())

        split = QSplitter(Qt.Horizontal)
        split.setHandleWidth(1)
        split.addWidget(self._build_sidebar())
        split.addWidget(self._build_center())
        self.side_panel = SidePanel()
        self.side_panel.hide()
        self.side_panel.clear_requested.connect(self._confirm_clear_queue)
        self.side_panel.save_requested.connect(self._prompt_queue_name)
        split.addWidget(self.side_panel)
        split.setSizes([90, 800, 280])
        self._relay_playlist_requests()
        outer.addWidget(split, stretch=1)

        outer.addWidget(self._build_player_bar())

        self._toast = Toast(self)
        self._setup_shortcuts()
        self._setup_tray()
        self.setStyleSheet(APP_STYLESHEET)

    def _load_icons(self):
        icon = qta.icon
        self.icons = {
            "play": icon("fa5s.play", color="#0f0f0f"),
            "pause": icon("fa5s.pause", color="#0f0f0f"),
            "next": icon("fa5s.step-forward", color="white"),
            "prev": icon("fa5s.step-backward", color="white"),
            "volume": icon("fa5s.volume-up", color="white"),
            "search": icon("fa5s.search", color="white"),
            "login": icon("fa5s.user-circle", color="white"),
            "login_active": icon("fa5s.user-circle", color="#FF0000"),
            "import": icon("fa5s.file-import", color="white"),
            "loop_off": icon("fa5s.sync-alt", color="gray"),
            "loop_queue": icon("fa5s.sync-alt", color="#FF0000"),
            "loop_song": icon("fa5s.redo", color="#FF0000"),
            "home": icon("fa5s.home", color="white"),
            "library": icon("fa5s.music", color="white"),
            "explore": icon("fa5s.compass", color="white"),
        }

    def _build_top_bar(self):
        self.top_bar = TopBar(self.icons["search"], self.icons["login"], self.icons["login_active"])
        self.top_bar.search_box.returnPressed.connect(self._submit_search)
        self.top_bar.search_requested.connect(self._submit_search)
        self.top_bar.login_requested.connect(self._on_account_clicked)
        return self.top_bar

    def _build_sidebar(self):
        self.sidebar = Sidebar({
            "home": self.icons["home"], "explore": self.icons["explore"],
            "library": self.icons["library"], "import": self.icons["import"],
        })
        self.sidebar.home_requested.connect(self.home_requested)
        self.sidebar.explore_requested.connect(self.explore_requested)
        self.sidebar.library_requested.connect(self.library_requested)
        self.sidebar.import_requested.connect(self._prompt_import_url)
        return self.sidebar

    def _build_center(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.home_panel = HomePanel()
        self.explore_panel = ExplorePanel()
        self.search_panel = SearchPanel()
        self.library_browser = LibraryBrowserPanel()
        self.artist_panel = ArtistPanel()
        self.album_panel = AlbumPanel()
        self.now_playing_panel = NowPlayingPanel()
        self._pages = {"home": self.home_panel, "explore": self.explore_panel, "search": self.search_panel,
                       "library": self.library_browser, "artist": self.artist_panel, "album": self.album_panel}
        for panel in (*self._pages.values(), self.now_playing_panel):
            layout.addWidget(panel)
        for name, panel in self._pages.items():
            panel.setVisible(name == "home")
        self.now_playing_panel.hide()
        return container

    def _relay_playlist_requests(self):
        for signal in (self.home_panel.add_playlist_clicked, self.explore_panel.add_playlist_clicked,
                       self.search_panel.add_playlist_clicked, self.library_browser.song_add_playlist,
                       self.side_panel.similar_add_playlist, self.artist_panel.add_playlist_clicked,
                       self.album_panel.add_playlist_clicked):
            signal.connect(self.save_to_playlist_requested)
        for signal in (self.home_panel.collection_action_requested, self.explore_panel.collection_action_requested,
                       self.artist_panel.collection_action_requested, self.album_panel.collection_action_requested,
                       self.side_panel.similar_collection_action):
            signal.connect(self.collection_action_requested)

    def _build_player_bar(self):
        self.player_panel = PlayerPanel({
            "play": self.icons["play"], "pause": self.icons["pause"],
            "next": self.icons["next"], "prev": self.icons["prev"],
            "volume": self.icons["volume"],
            "loop_off": self.icons["loop_off"],
        })
        self.player_panel.cover_label.setPixmap(self.icons["library"].pixmap(56, 56))
        self.player_panel.expand_clicked.connect(self.toggle_now_playing)
        self.player_panel.prev_button.clicked.connect(self.previous_clicked)
        self.player_panel.play_button.clicked.connect(self.play_pause_clicked)
        self.player_panel.next_button.clicked.connect(self.next_clicked)
        self.player_panel.loop_button.clicked.connect(self.loop_clicked)
        self.player_panel.shuffle_button.clicked.connect(self.shuffle_clicked)
        self.player_panel.progress_slider.sliderMoved.connect(lambda v: self.seek_requested.emit(v / 1000.0))
        self.player_panel.volume_slider.valueChanged.connect(self.volume_changed)
        self.player_panel.hide()
        return self.player_panel

    def _setup_shortcuts(self):
        quit_action = QAction("Salir", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(QApplication.instance().quit)
        self.addAction(quit_action)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self._app_icon, self)
        self.tray_icon.setToolTip("YTMusic Client")
        menu = QMenu(self)
        menu.addAction("Mostrar").triggered.connect(self.showNormal)
        menu.addSeparator()
        self._tray_play_action = menu.addAction("▶ Reproducir")
        self._tray_play_action.triggered.connect(self.play_pause_clicked)
        menu.addAction(self.icons["prev"], "Anterior").triggered.connect(self.previous_clicked)
        menu.addAction(self.icons["next"], "Siguiente").triggered.connect(self.next_clicked)
        menu.addSeparator()
        menu.addAction("Salir").triggered.connect(QApplication.instance().quit)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("Minimizado", "Reproduciendo en 2do plano.",
                                   QSystemTrayIcon.MessageIcon.Information, 2000)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._toast.reposition()

    @property
    def current_view(self):
        return self._view

    # vistas navegacion
    def show_view(self, name):
        self._view = name
        for key, panel in self._pages.items():
            panel.setVisible(key == name)
        self.now_playing_panel.hide()
        self.side_panel.hide()
        self.player_panel.set_expanded(False)
        self.sidebar.set_active(_VIEW_NAV_LABELS[name])
        self.view_shown.emit(name)

    def toggle_now_playing(self):
        if self.now_playing_panel.isVisible():
            self.show_view(self._view)
            return
        for panel in self._pages.values():
            panel.hide()
        self.now_playing_panel.show()
        self.side_panel.show()
        self.player_panel.set_expanded(True)

    def _submit_search(self):
        text = self.top_bar.search_box.text().strip()
        if text:
            self.search_submitted.emit(text)

    def set_now_playing(self, title, artist):
        self.player_panel.song_label.setText(title)
        self.player_panel.artist_label.setText(artist)
        self.player_panel.show()

    def set_cover(self, pixmap: QPixmap | None):
        if pixmap is None or pixmap.isNull():
            self.player_panel.cover_label.setPixmap(self.icons["library"].pixmap(56, 56))
            self.now_playing_panel.set_cover(QPixmap())
            return
        self.player_panel.cover_label.setPixmap(scale_cover(pixmap, 56, self.devicePixelRatioF()))
        self.now_playing_panel.set_cover(pixmap)

    def set_playing(self, is_playing):
        self.player_panel.play_button.setIcon(self.icons["pause"] if is_playing else self.icons["play"])
        self._tray_play_action.setText("⏸ Pausar" if is_playing else "▶ Reproducir")

    def set_loop_mode(self, mode):
        icons = {0: self.icons["loop_off"], 1: self.icons["loop_queue"], 2: self.icons["loop_song"]}
        tips = {0: "Repetir (Apagado)", 1: "Repetir Cola", 2: "Repetir Canción"}
        self.player_panel.loop_button.setIcon(icons.get(mode, self.icons["loop_off"]))
        self.player_panel.loop_button.setToolTip(tips.get(mode, "Repetir"))

    def set_progress(self, fraction):
        slider = self.player_panel.progress_slider
        if slider.isSliderDown():
            return
        slider.blockSignals(True)
        slider.setValue(int(fraction * 1000))
        slider.blockSignals(False)

    def set_time(self, current, total):
        self.player_panel.time_label.setText(format_seconds(current))
        self.player_panel.total_time_label.setText(format_seconds(total))

    def reset_progress(self):
        self.set_progress(0)
        self.set_time(0, 0)

    @property
    def volume(self):
        return self.player_panel.volume_slider.value()

    def set_auth_state(self, logged_in):
        self._logged_in = logged_in
        self.top_bar.set_login_state(logged_in)

    def _on_account_clicked(self):
        if not self._logged_in:
            self.login_requested.emit()
            return
        if dialogs.confirm(self, "¿Cerrar sesión?", "Dejarás de ver tu biblioteca y tus playlists de YouTube Music.",
                           ok="Cerrar sesión"):
            self.logout_requested.emit()

    def show_toast(self, level, text):
        self._toast.show_message(level, text)

    def _prompt_import_url(self):
        url = dialogs.prompt_text(self, "Importar playlist", "Pega la URL de la playlist de YouTube Music.",
                                  ok="Importar", placeholder="https://music.youtube.com/playlist?list=…")
        if url:
            self.import_url_submitted.emit(url)

    def _confirm_clear_queue(self):
        if dialogs.confirm(self, "¿Limpiar la cola?", "Se quitarán todas las canciones excepto la que suena ahora.",
                           ok="Limpiar"):
            self.queue_clear_confirmed.emit()

    def _prompt_queue_name(self):
        title = dialogs.prompt_text(self, "Guardar cola como playlist", "Ponle un nombre a tu playlist.",
                                    text="Mi Cola", ok="Guardar", placeholder="Título")
        if title:
            self.queue_save_requested.emit(title)

    def copy_text(self, text):
        QApplication.clipboard().setText(text)

    def choose_playlist(self, targets):
        dialog = SaveToPlaylistDialog(targets, self.thumbnails, self)
        dialog.exec()
        return dialog.choice

    def ask_save_target(self, title, authenticated):
        if authenticated:
            return dialogs.choose(self, "Guardar playlist", f"¿Dónde quieres guardar «{title}»?",
                                  [("En este equipo", "local"), ("En YouTube Music", "cloud")])
        return "local" if dialogs.confirm(self, "Guardar playlist", f"¿Guardar «{title}» en este equipo?",
                                          ok="Guardar") else None
