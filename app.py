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
player = None
queue_manager = None
playlist_manager = None
window = None
login_window = None


def save_state_on_exit():
    app_controller.save_state_on_exit()


def handle_result_highlighted(index):
    app_controller.handle_result_highlighted(index)


def handle_queue_item_moved(src, dst):
    app_controller.handle_queue_item_moved(src, dst)


def handle_toggle_loop():
    app_controller.handle_toggle_loop()


def handle_search(query):
    app_controller.handle_search(query)


def handle_import_playlist(url):
    app_controller.handle_import_playlist(url)


def handle_save_imported_playlist(save_to_ytmusic=False):
    app_controller.handle_save_imported_playlist(save_to_ytmusic)


def get_combined_playlists():
    return app_controller.get_combined_playlists()


def handle_song_selected(index):
    app_controller.handle_song_selected(index)


def handle_add_to_queue(index):
    app_controller.handle_add_to_queue(index)


def handle_add_next(index):
    app_controller.handle_add_next(index)


def handle_clear_queue():
    app_controller.handle_clear_queue()


def handle_save_queue_playlist(title=None):
    app_controller.handle_save_queue_playlist(title)


def handle_toggle_play():
    app_controller.handle_toggle_play()


def handle_volume_change(val):
    app_controller.handle_volume_change(val)


def handle_seek(pos):
    app_controller.handle_seek(pos)


def handle_next():
    app_controller.handle_next()


def handle_previous():
    app_controller.handle_previous()


def handle_remove_from_queue(idx):
    app_controller.handle_remove_from_queue(idx)


def handle_queue_item_selected(idx):
    app_controller.handle_queue_item_selected(idx)


def on_song_finished():
    app_controller.on_song_finished()


def on_queue_updated():
    app_controller.on_queue_updated()


def handle_login(headers):
    app_controller.handle_login(headers)


def handle_logout():
    app_controller.handle_logout()


def handle_playlist_selected(index):
    app_controller.handle_playlist_selected(index)


def handle_toggle_autoplay():
    app_controller.handle_toggle_autoplay()


def handle_fetch_and_play_recommendation():
    app_controller.handle_fetch_and_play_recommendation()


def handle_show_lyrics():
    app_controller.handle_show_lyrics()


def on_time_ms_updated(current_ms):
    app_controller.on_time_ms_updated(current_ms)


def initial_load():
    app_controller.initial_load()


def handle_home():
    app_controller.handle_home()


def start_main_application():
    global player, queue_manager, playlist_manager, window
    playlist_manager = PlaylistManager(BASE_DIR)
    player = Player(service)
    queue_manager = QueueManager()
    window = MainWindow(
        handle_search,
        handle_song_selected,
        handle_add_to_queue,
        handle_toggle_play,
        handle_add_next,
        handle_volume_change,
        handle_seek,
        handle_next,
        handle_previous,
        handle_remove_from_queue,
        handle_queue_item_selected,
        handle_login,
        handle_playlist_selected,
        handle_import_playlist,
        app_icon,
        handle_save_imported_playlist,
        handle_result_highlighted,
        handle_queue_item_moved,
        handle_toggle_loop,
        handle_logout,
        handle_toggle_autoplay,
        handle_show_lyrics,
        handle_home,
        handle_clear_queue,
        handle_save_queue_playlist,
    )
    app_controller.bind_runtime(player, queue_manager, playlist_manager, window)
    player.position_changed.connect(window.update_progress)
    player.time_changed.connect(window.update_time)
    player.current_time_ms.connect(on_time_ms_updated)
    player.song_finished.connect(on_song_finished)
    player.stream_ready.connect(app_controller.on_stream_ready)
    player.stream_error.connect(app_controller.on_stream_error)
    queue_manager.queue_updated.connect(on_queue_updated)
    queue_manager.current_changed.connect(on_queue_updated)
    queue_manager.loop_mode_changed.connect(window.update_loop_button_icon)
    queue_manager.autoplay_mode_changed.connect(window.update_autoplay_button_icon)
    atexit.register(save_state_on_exit)
    initial_load()
    window.resize(1240, 750)
    window.show()
    if login_window:
        login_window.close()


def main():
    global login_window, service
    login_window = LoginWindow(service, app_icon, service.is_authenticated)
    login_window.login_success.connect(start_main_application)
    login_window.login_skipped.connect(start_main_application)
    login_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()