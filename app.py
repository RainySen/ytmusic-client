import sys
from PySide6.QtWidgets import QApplication
from services.ytmusic_service import YTMusicService
from core.player import Player
from core.queue_manager import QueueManager
from ui.main_window import MainWindow
import re
import json

app = QApplication(sys.argv)
service = YTMusicService()
player = Player()
queue_manager = QueueManager()
results_cache = []
playlists_cache = []
PLAYLIST_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")


def handle_search(query):
    global results_cache
    match = PLAYLIST_RE.search(query)
    if match:
        playlist_id = match.group(1)
        playlist_songs = service.get_playlist_songs(playlist_id)
        if playlist_songs:
            results_cache = []
            window.update_results(results_cache)
            queue_manager.clear()
            first_song_to_play = None
            for song in playlist_songs:
                maybe_first = queue_manager.add_song(song)
                if maybe_first and first_song_to_play is None:
                    first_song_to_play = maybe_first
            if first_song_to_play:
                play_song(first_song_to_play)
            window.update_song_info(f"Playlist cargada ({len(playlist_songs)} canciones)")
            window.search_box.clear()
        else:
            window.update_song_info("Error al cargar la playlist o está vacía")
    else:
        results_cache = service.search(query)
        window.update_results(results_cache)


def handle_song_selected(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        current_song = queue_manager.play_now(song_data)
        if current_song:
            play_song(current_song)


def handle_add_to_queue(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        first_song = queue_manager.add_song(song_data)
        if first_song:
            play_song(first_song)


def play_song(song_data):
    if not song_data or "videoId" not in song_data:
        window.update_song_info("Error al cargar la canción")
        return
    url = service.get_stream_url(song_data["videoId"])
    title = player.play(url)
    if title:
        artist_name = song_data.get('artists', [{}])[0].get('name', 'Desconocido')
        display_text = f"{title} - {artist_name}"
        window.update_song_info(display_text)
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


def handle_login(headers_raw):
    global playlists_cache
    success = service.setup_authentication(headers_raw)
    if success:
        window.show_auth_success()
        playlists_cache = service.get_library_playlists()
        window.update_playlists(playlists_cache)
    else:
        window.show_auth_error()


def handle_playlist_selected(index):
    """
    === LÓGICA CORREGIDA Y FINAL ===
    Esta función ahora carga la playlist directamente en la cola de reproducción.
    """
    global results_cache
    if 0 <= index < len(playlists_cache):
        playlist = playlists_cache[index]
        # Usamos 'playlistId' que es la clave correcta para las playlists de la librería.
        playlist_id = playlist.get('playlistId')

        if not playlist_id:
            print(f"[ERROR] La playlist '{playlist.get('title')}' no tiene un 'playlistId' válido.")
            # Imprimimos los datos de la playlist para depurar si vuelve a fallar.
            print(f"[DEBUG] Datos de la playlist con error: {playlist}")
            return

        songs = service.get_playlist_songs(playlist_id)

        if songs:
            print(f"Cargando {len(songs)} canciones de la playlist '{playlist.get('title')}' a la cola.")

            # 1. Limpiamos la lista de búsqueda y la cola actual.
            results_cache = []
            window.update_results([])
            queue_manager.clear()

            # 2. Añadimos todas las canciones a la cola.
            for song in songs:
                queue_manager.add_song(song)

            # 3. Le decimos al gestor que salte a la primera canción (índice 0) y la obtenemos.
            first_song = queue_manager.jump_to(0)

            # 4. Reproducimos la primera canción.
            if first_song:
                play_song(first_song)
        else:
            print(f"La playlist '{playlist.get('title')}' está vacía o no se pudo cargar.")


def initial_load():
    global playlists_cache
    if service.is_authenticated:
        playlists_cache = service.get_library_playlists()
        window.update_playlists(playlists_cache)
    else:
        window.update_playlists([])


window = MainWindow(
    on_search=handle_search,
    on_select_song=handle_song_selected,
    on_add_to_queue=handle_add_to_queue,
    on_toggle_play=handle_toggle_play,
    on_volume_change=handle_volume_change,
    on_seek=handle_seek,
    on_next=handle_next,
    on_previous=handle_previous,
    on_remove_from_queue=handle_remove_from_queue,
    on_queue_item_selected=handle_queue_item_selected,
    on_login_requested=handle_login,
    on_playlist_selected=handle_playlist_selected
)

player.position_changed.connect(window.update_progress)
player.time_changed.connect(window.update_time)
player.song_finished.connect(on_song_finished)
queue_manager.queue_updated.connect(on_queue_updated)
queue_manager.current_changed.connect(on_queue_updated)
window.clear_btn.clicked.connect(queue_manager.clear)

initial_load()
window.resize(900, 600)
window.show()
sys.exit(app.exec())