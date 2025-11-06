# app.py
import sys
import qtawesome as qta
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from services.ytmusic_service import YTMusicService
from core.player import Player
from core.queue_manager import QueueManager
from ui.main_window import MainWindow
from ui.login_window import LoginWindow  # <-- NUEVA IMPORTACIÓN
import re
import json

# --- 1. CONFIGURACIÓN INICIAL (GLOBAL) ---
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
app_icon = qta.icon('fa5s.music', color='#03adb7')
app.setWindowIcon(app_icon)

service = YTMusicService()
player = None
queue_manager = None
window = None
login_window = None

results_cache = []
playlists_cache = []
last_imported_playlist_data = None
PLAYLIST_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")


# --- 2. TODAS LAS FUNCIONES DE LÓGICA (HANDLERS) ---
# (Todo este bloque es idéntico a tu archivo anterior)

def handle_result_highlighted(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        if "videoId" in song_data:
            player.preload_stream(song_data["videoId"])


def handle_queue_item_moved(source_index, dest_index):
    queue_manager.move_song(source_index, dest_index)


def handle_toggle_loop():
    queue_manager.toggle_loop_mode()


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
                preload_next_songs(5)
            window.search_box.clear()
            last_imported_playlist_data = playlist_data
            if service.is_authenticated:
                window.ask_to_save_playlist(playlist_title)
        else:
            print("Error al cargar la playlist o está vacía")
    else:
        print("La URL de la playlist no es válida")


def handle_save_imported_playlist():
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
            preload_next_songs(5)


def handle_add_to_queue(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        first_song = queue_manager.add_song(song_data)
        if first_song:
            play_song(first_song)
            preload_next_songs(5)
        else:
            if "videoId" in song_data:
                player.preload_stream(song_data["videoId"])


def handle_add_next(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        first_song = queue_manager.add_next(song_data)
        if first_song:
            play_song(first_song)
            preload_next_songs(5)
        else:
            if "videoId" in song_data:
                player.preload_stream(song_data["videoId"])


def preload_next_songs(count=5):
    queue = queue_manager.get_queue()
    current_index = queue_manager.get_current_index()
    for i in range(1, count + 1):
        next_index = current_index + i
        if next_index < len(queue):
            next_song = queue[next_index]
            if "videoId" in next_song:
                player.preload_stream(next_song["videoId"])


def play_song(song_data):
    if not song_data or "videoId" not in song_data:
        window.update_song_info("Error al cargar la canción")
        return
    video_id = song_data["videoId"]
    artist_name = song_data.get('artists', [{}])[0].get('name', 'Desconocido')
    display_text = f"{song_data['title']} - {artist_name}"
    window.update_play_button_icon(True)
    window.update_song_info(f"Cargando: {display_text}")
    title_from_cache = player.play(video_id)
    if title_from_cache:
        print("[UI] Cache hit, actualizando título final.")
        window.update_song_info(display_text)


def on_stream_ready(video_id, title):
    current_song = queue_manager.get_current()
    if current_song and current_song.get("videoId") == video_id:
        artist_name = current_song.get('artists', [{}])[0].get('name', 'Desconocido')
        display_text = f"{title} - {artist_name}"
        window.update_song_info(display_text)
        window.update_play_button_icon(True)


def on_stream_error(error_msg):
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
        preload_next_songs(5)


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
        preload_next_songs(5)


def on_song_finished():
    mode = queue_manager.get_loop_mode()
    if mode == QueueManager.LOOP_SONG:
        print("[LOOP] Repitiendo canción actual.")
        current_song = queue_manager.get_current()
        if current_song:
            play_song(current_song)
    else:
        next_song = queue_manager.next()
        if next_song:
            play_song(next_song)
            preload_next_songs(5)
        else:
            window.update_song_info("Cola terminada")
            window.update_play_button_icon(False)


def on_queue_updated():
    window.update_queue(queue_manager.get_queue(), queue_manager.get_current_index())


def handle_login(headers_raw):
    """
    Esta función ahora es solo para el botón "Login" DENTRO de la app principal.
    """
    global playlists_cache
    success = service.setup_authentication(headers_raw)
    if success:
        window.show_auth_success()
        playlists_cache = service.get_library_playlists()
        window.update_playlists(playlists_cache)
    else:
        window.show_auth_error()


def handle_playlist_selected(index):
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
                preload_next_songs(5)
        else:
            print(f"La playlist '{playlist.get('title')}' está vacía o no se pudo cargar.")


def initial_load():
    global playlists_cache
    if service.is_authenticated:
        playlists_cache = service.get_library_playlists()
        window.update_playlists(playlists_cache)
    else:
        window.update_playlists([])


# --- 3. LÓGICA DE ARRANQUE MODIFICADA ---

def start_main_application():
    """
    Esta función se llama DESPUÉS de que el usuario interactúa
    con la ventana de login.
    """
    global player, queue_manager, window, app_icon, service

    # Ahora sí, inicializamos los componentes principales
    player = Player(service)
    queue_manager = QueueManager()

    # Crear la ventana principal
    window = MainWindow(
        on_search=handle_search,
        on_select_song=handle_song_selected,
        on_add_to_queue=handle_add_to_queue,
        on_add_next=handle_add_next,
        on_toggle_play=handle_toggle_play,
        on_volume_change=handle_volume_change,
        on_seek=handle_seek,
        on_next=handle_next,
        on_previous=handle_previous,
        on_remove_from_queue=handle_remove_from_queue,
        on_queue_item_selected=handle_queue_item_selected,
        on_login_requested=handle_login,  # Para el botón de login *dentro* de la app
        on_playlist_selected=handle_playlist_selected,
        on_import_playlist=handle_import_playlist,
        on_save_imported_playlist=handle_save_imported_playlist,
        on_result_highlighted=handle_result_highlighted,
        on_queue_item_moved=handle_queue_item_moved,
        on_toggle_loop=handle_toggle_loop,
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
    queue_manager.loop_mode_changed.connect(window.update_loop_button_icon)
    window.clear_btn.clicked.connect(queue_manager.clear)

    # Cargar datos iniciales (playlists si se logueó)
    initial_load()

    window.resize(1080, 750)
    window.show()

    # Cerrar la ventana de login
    login_window.close()


# --- 4. PUNTO DE ENTRADA PRINCIPAL ---

def main():
    global login_window, service

    # Crear la ventana de login primero
    # === CAMBIO CLAVE AQUÍ ===
    # Pasamos el estado de autenticación (True/False) a la ventana de login
    login_window = LoginWindow(service, app_icon, service.is_authenticated)

    # Conectar las señales de la ventana de login
    login_window.login_success.connect(start_main_application)
    login_window.login_skipped.connect(start_main_application)

    # Mostrar la ventana de login
    login_window.show()

    # Ejecutar la aplicación
    sys.exit(app.exec())


if __name__ == "__main__":
    main()