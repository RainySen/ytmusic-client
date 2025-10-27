import sys
from PySide6.QtWidgets import QApplication
from services.ytmusic_service import YTMusicService
from core.player import Player
from ui.main_window import MainWindow

app = QApplication(sys.argv)

service = YTMusicService()
player = Player()
results_cache = []
current_video_id = None

def handle_search(query):
    global results_cache
    results_cache = service.search(query)
    window.update_results(results_cache)

def handle_song_selected(index):
    global current_video_id
    video_id = results_cache[index]["videoId"]
    current_video_id = video_id
    url = service.get_stream_url(video_id)
    title = player.play(url)
    window.update_song_info(title)

def handle_toggle_play():
    if current_video_id:
        player.toggle_play()

def handle_volume_change(value):
    player.set_volume(value)

window = MainWindow(handle_search, handle_song_selected, handle_toggle_play, handle_volume_change)
window.resize(450, 550)
window.show()

sys.exit(app.exec())
