import sys
import qtawesome as qta
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from services.ytmusic_service import YTMusicService
from core.player import Player
from core.queue_manager import QueueManager
from ui.main_window import MainWindow
import re
import json

app = QApplication(sys.argv)

app.setQuitOnLastWindowClosed(False)
app_icon = qta.icon('fa5s.music', color='#03adb7')
app.setWindowIcon(app_icon)
service = YTMusicService()
player = Player()
queue_manager = QueueManager()
results_cache = []
playlists_cache = []
last_imported_playlist_data = None
PLAYLIST_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")


def handle_search(query):
    global results_cache
    print("Realizando búsqueda normal de texto...")
    results_cache = service.search(query)
    window.update_results(results_cache)


def handle_import_playlist(url):
    global results_cache, last_imported_playlist_data
    match = PLAYLIST_RE.search(url)

    if match:
        playlist_id = match.group(1)
        print(f"Detectada playlist ID: {playlist_id}")

        playlist_data = service.get_playlist_songs(playlist_id)

        if playlist_data and playlist_data['tracks']:
            playlist_songs = playlist_data['tracks']
            playlist_title = playlist_data['title']

            results_cache = []
            window.update_results(results_cache)
            queue_manager.clear()

            print(f"Cargando {len(playlist_songs)} canciones en la cola...")

            first_song_to_play = None
            for song in playlist_songs:
                maybe_first = queue_manager.add_song(song)
                if maybe_first and first_song_to_play is None:
                    first_song_to_play = maybe_first

            if first_song_to_play:
                play_song(first_song_to_play)
                # Precargar las siguientes 2 canciones
                preload_next_songs(2)

            window.search_box.clear()

            last_imported_playlist_data = playlist_data

            if service.is_authenticated:
                window.ask_to_save_playlist(playlist_title)

        else:
            print("Error al cargar la playlist o está vacía")
    else:
        print("La URL de la playlist no es válida")


def handle_save_imported_playlist():
    """
    Se llama cuando el usuario hace clic en "Sí" en el diálogo de guardado.
    """
    global last_imported_playlist_data, playlists_cache
    if not last_imported_playlist_data:
        return

    title = last_imported_playlist_data['title']
    songs = last_imported_playlist_data['tracks']
    description = f"Importada desde URL. Contiene {len(songs)} canciones."

    print(f"Intentando guardar la playlist '{title}' en la biblioteca...")
    playlist_id = service.create_playlist(title, description, songs)

    if playlist_id:
        print(f"Playlist guardada con éxito. ID: {playlist_id}")
        playlists_cache = service.get_library_playlists()
        window.update_playlists(playlists_cache)
        window.show_save_playlist_success(title)
    else:
        print("Error al guardar la playlist.")
        window.show_save_playlist_error(title)

    last_imported_playlist_data = None


def handle_song_selected(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        current_song = queue_manager.play_now(song_data)
        if current_song:
            play_song(current_song)
            # Precargar las siguientes 2 canciones
            preload_next_songs(2)


def handle_add_to_queue(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        first_song = queue_manager.add_song(song_data)
        if first_song:
            play_song(first_song)
            # Precargar las siguientes 2 canciones
            preload_next_songs(2)


def preload_next_songs(count=2):
    """
    Precarga las siguientes N canciones en la cola para reproducción instantánea
    """
    queue = queue_manager.get_queue()
    current_index = queue_manager.get_current_index()

    for i in range(1, count + 1):
        next_index = current_index + i
        if next_index < len(queue):
            next_song = queue[next_index]
            if "videoId" in next_song:
                video_id = next_song["videoId"]
                url = service.get_stream_url(video_id)
                player.preload_stream(video_id, url)


def play_song(song_data):
    if not song_data or "videoId" not in song_data:
        window.update_song_info("Error al cargar la canción")
        return

    video_id = song_data["videoId"]
    url = service.get_stream_url(video_id)

    # Mostrar mensaje de carga
    artist_name = song_data.get('artists', [{}])[0].get('name', 'Desconocido')
    window.update_song_info(f"Cargando: {song_data['title']} - {artist_name}")

    title = player.play(video_id, url)

    if title:
        # Reproducción inmediata desde caché
        display_text = f"{title} - {artist_name}"
        window.update_song_info(display_text)
        window.update_play_button_icon(True)
    # Si no hay título, se actualizará vía signal cuando esté listo


def on_stream_ready(video_id, title):
    """Callback cuando el stream está listo y empieza a reproducir"""
    current_song = queue_manager.get_current()
    if current_song and current_song.get("videoId") == video_id:
        artist_name = current_song.get('artists', [{}])[0].get('name', 'Desconocido')
        display_text = f"{title} - {artist_name}"
        window.update_song_info(display_text)
        window.update_play_button_icon(True)


def on_stream_error(error_msg):
    """Callback cuando hay error al obtener el stream"""
    window.update_song_info(f"Error al reproducir: {error_msg}")
    window.update_play_button_icon(False)


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
        # Precargar las siguientes 2 canciones
        preload_next_songs(2)


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
        # Precargar las siguientes 2 canciones
        preload_next_songs(2)


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
    Se llama al hacer doble clic en una playlist de "Mis Playlists".
    """
    global results_cache
    if 0 <= index < len(playlists_cache):
        playlist = playlists_cache[index]
        playlist_id = playlist.get('playlistId')

        if not playlist_id:
            print(f"[ERROR] La playlist '{playlist.get('title')}' no tiene un 'playlistId' válido.")
            return

        songs_data = service.get_playlist_songs(playlist_id)

        if songs_data and 'tracks' in songs_data:
            songs_list = songs_data['tracks']
            playlist_title = songs_data.get('title', 'Playlist')

            print(f"Cargando {len(songs_list)} canciones de la playlist '{playlist_title}' a la cola.")

            results_cache = []
            window.update_results([])
            queue_manager.clear()

            for song in songs_list:
                queue_manager.add_song(song)

            first_song = queue_manager.jump_to(0)
            if first_song:
                play_song(first_song)
                preload_next_songs(2)
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
    on_playlist_selected=handle_playlist_selected,
    on_import_playlist=handle_import_playlist,
    on_save_imported_playlist=handle_save_imported_playlist,
    app_icon=app_icon
)

# Conectar signals del player
player.position_changed.connect(window.update_progress)
player.time_changed.connect(window.update_time)
player.song_finished.connect(on_song_finished)
player.stream_ready.connect(on_stream_ready)
player.stream_error.connect(on_stream_error)

# Conectar signals del queue manager
queue_manager.queue_updated.connect(on_queue_updated)
queue_manager.current_changed.connect(on_queue_updated)
window.clear_btn.clicked.connect(queue_manager.clear)

initial_load()
window.resize(1000, 600)
window.show()
sys.exit(app.exec())