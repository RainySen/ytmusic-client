import os
import sys
import atexit

import qtawesome as qta
from PySide6.QtWidgets import QApplication

from core.app_controller import AppController
from core.player import Player
from core.playlist_manager import PlaylistManager
from core.queue_manager import QueueManager
from services.ytmusic_service import YTMusicService
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
app_icon = qta.icon('fa5s.music', color='#03adb7')
app.setWindowIcon(app_icon)

service = YTMusicService(BASE_DIR)
app_controller = AppController(BASE_DIR, service)
login_window = None


def start_main_application():
    global login_window
    player = Player(service)
    queue_manager = QueueManager()
    playlist_manager = PlaylistManager(BASE_DIR)
    window = MainWindow(
        app_controller.handle_search,
        app_controller.handle_song_selected,
        app_controller.handle_add_to_queue,
        app_controller.handle_toggle_play,
        app_controller.handle_add_next,
        app_controller.handle_volume_change,
        app_controller.handle_seek,
        app_controller.handle_next,
        app_controller.handle_previous,
        app_controller.handle_remove_from_queue,
        app_controller.handle_queue_item_selected,
        app_controller.handle_login,
        app_controller.handle_playlist_selected,
        app_controller.handle_import_playlist,
        app_icon,
        app_controller.handle_save_imported_playlist,
        app_controller.handle_result_highlighted,
        app_controller.handle_queue_item_moved,
        app_controller.handle_toggle_loop,
        app_controller.handle_logout,
        app_controller.handle_toggle_autoplay,
        app_controller.handle_show_lyrics,
        app_controller.handle_home,
        app_controller.handle_clear_queue,
        app_controller.handle_save_queue_playlist,
    )
    app_controller.bind_runtime(player, queue_manager, playlist_manager, window)
    window.home_panel.item_clicked.connect(app_controller.handle_home_item_selected)
    window.home_panel.mood_selected.connect(app_controller.handle_mood_selected)
    window.sidebar.library_requested.connect(app_controller.handle_show_library)
    window.library_browser.chip_selected.connect(app_controller.handle_library_chip_selected)
    window.library_browser.playlist_activated.connect(app_controller.handle_library_playlist_selected)
    window.library_browser.song_activated.connect(app_controller.handle_library_song_selected)
    window.library_panel.similar_song_activated.connect(app_controller.handle_library_song_selected)
    window.library_panel.similar_filter_changed.connect(app_controller.handle_similar_filter)
    player.position_changed.connect(window.update_progress)
    player.time_changed.connect(window.update_time)
    player.current_time_ms.connect(app_controller.on_time_ms_updated)
    player.song_finished.connect(app_controller.on_song_finished)
    player.stream_ready.connect(app_controller.on_stream_ready)
    player.stream_error.connect(app_controller.on_stream_error)
    queue_manager.queue_updated.connect(app_controller.on_queue_updated)
    queue_manager.current_changed.connect(app_controller.on_queue_updated)
    queue_manager.loop_mode_changed.connect(window.update_loop_button_icon)
    app.aboutToQuit.connect(app_controller.save_state_on_exit)
    atexit.register(app_controller.save_state_on_exit)
    app_controller.initial_load()
    window.resize(1240, 750)
    window.show()
    if login_window:
        login_window.close()


def main():
    global login_window
    login_window = LoginWindow(service, app_icon, service.is_authenticated)
    login_window.login_success.connect(start_main_application)
    login_window.login_skipped.connect(start_main_application)
    login_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
