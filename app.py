import sys
from PySide6.QtWidgets import QApplication
from services.ytmusic_service import YTMusicService
from core.player import Player
from core.queue_manager import QueueManager
from ui.main_window import MainWindow
import re

app = QApplication(sys.argv)

service = YTMusicService()
player = Player()
queue_manager = QueueManager()
results_cache = []
PLAYLIST_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")


def handle_search(query):
    global results_cache

    #Revisar si la consulta es una URL de playlist
    match = PLAYLIST_RE.search(query)

    if match:
        playlist_id = match.group(1)
        print(f"Detectada playlist ID: {playlist_id}")

        #Obtener las canciones de la playlist
        playlist_songs = service.get_playlist_songs(playlist_id)

        if playlist_songs:
            results_cache = []
            window.update_results(results_cache)
            queue_manager.clear()

            print(f"Cargando {len(playlist_songs)} canciones en la cola...")

            first_song_to_play = None
            for song in playlist_songs:
                #Añadir cada canción a la cola
                # add_song devuelve la canción si es la primera en ser añadida
                maybe_first = queue_manager.add_song(song)

                if maybe_first and first_song_to_play is None:
                    first_song_to_play = maybe_first

            #Reproducir la primera canción de la playlist
            if first_song_to_play:
                play_song(first_song_to_play)

            window.update_song_info(f"Playlist cargada ({len(playlist_songs)} canciones)")
            window.search_box.clear()  # Limpiar la barra de búsqueda

        else:
            window.update_song_info("Error al cargar la playlist o está vacía")

    else:
        #Si no es una playlist, hacer la búsqueda normal
        print("Realizando búsqueda normal...")
        results_cache = service.search(query)
        window.update_results(results_cache)


def handle_song_selected(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]

        current_song = queue_manager.play_now(song_data)
        play_song(current_song)


def handle_add_to_queue(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        first_song = queue_manager.add_song(song_data)

        if first_song:
            play_song(first_song)


def play_song(song_data):
    url = service.get_stream_url(song_data["videoId"])
    title = player.play(url)

    if title:
        window.update_song_info(title)
        window.update_play_button_icon(True)
    else:
        window.update_song_info("Error al reproducir")


def handle_toggle_play():
    player.toggle_play()
    window.update_play_button_icon(player.is_playing)


def handle_volume_change(value):
    player.set_volume(value)


def handle_seek(position):
    player.seek(position)


def handle_next():
    next_song = queue_manager.next()
    if next_song:
        play_song(next_song)


def handle_previous():
    prev_song = queue_manager.previous()
    if prev_song:
        play_song(prev_song)


def handle_remove_from_queue(index):
    queue_manager.remove_at(index)


def handle_queue_item_selected(index):
    song = queue_manager.jump_to(index)
    if song:
        play_song(song)


def on_song_finished():
    if queue_manager.has_next():
        handle_next()
    else:
        window.update_song_info("Cola terminada")
        window.update_play_button_icon(False)


def on_queue_updated():
    window.update_queue(queue_manager.get_queue(), queue_manager.get_current_index())


# Crear la ventana
window = MainWindow(
    handle_search,
    handle_song_selected,
    handle_add_to_queue,
    handle_toggle_play,
    handle_volume_change,
    handle_seek,
    handle_next,
    handle_previous,
    handle_remove_from_queue,
    handle_queue_item_selected
)

player.position_changed.connect(window.update_progress)
player.time_changed.connect(window.update_time)
player.song_finished.connect(on_song_finished)

queue_manager.queue_updated.connect(on_queue_updated)
queue_manager.current_changed.connect(on_queue_updated)

window.clear_btn.clicked.connect(queue_manager.clear)

window.resize(900, 600)
window.show()

sys.exit(app.exec())