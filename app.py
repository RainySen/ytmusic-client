import sys
import qtawesome as qta
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from services.ytmusic_service import YTMusicService
from core.player import Player
from core.queue_manager import QueueManager
from ui.main_window import MainWindow
from ui.login_window import LoginWindow
from core.playlist_manager import PlaylistManager
import re
import json
import atexit
import os
import traceback
from datetime import datetime

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
elif __file__:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    BASE_DIR = os.getcwd()

app = QApplication(sys.argv)

app.setQuitOnLastWindowClosed(False)
app_icon = qta.icon('fa5s.music', color='#03adb7')
app.setWindowIcon(app_icon)
service = YTMusicService(BASE_DIR)
player = None
queue_manager = None
playlist_manager = None
window = None
login_window = None

results_cache = []
playlists_cache = []
last_imported_playlist_data = None
PLAYLIST_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")
STATE_FILE = os.path.join(BASE_DIR, "queue_and_cache.json")

def save_state_on_exit():
    """Se ejecuta automáticamente al cerrar la app."""
    print("[STATE] Guardando estado de la cola y caché...")
    try:
        queue = queue_manager.get_queue()
        current_index = queue_manager.get_current_index()
        stream_cache = player.get_stream_cache_for_saving()

        state_data = {
            "queue": queue,
            "current_index": current_index,
            "stream_cache": stream_cache,
        }

        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"[STATE] Error fatal al guardar estado: {e}")
        traceback.print_exc()

def handle_result_highlighted(index):
    """
    Se llama cuando el usuario resalta un ítem en la búsqueda.
    Inicia la precarga del stream.
    """
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

            window.ask_to_save_playlist(playlist_title, service.is_authenticated)

        else:
            print("Error al cargar la playlist o está vacía")
    else:
        print("La URL de la playlist no es válida")


def handle_save_imported_playlist(save_to_ytmusic=False):
    global last_imported_playlist_data, playlists_cache
    if not last_imported_playlist_data:
        return

    title = last_imported_playlist_data['title']
    songs = last_imported_playlist_data['tracks']

    if save_to_ytmusic and service.is_authenticated:
        # Guardar en YouTube Music
        description = f"Importada desde URL. Contiene {len(songs)} canciones."
        print(f"Intentando guardar la playlist '{title}' en YouTube Music...")
        playlist_id = service.create_playlist(title, description, songs)

        if playlist_id:
            print(f"Playlist guardada en YouTube Music con éxito. ID: {playlist_id}")
            playlists_cache = get_combined_playlists()
            window.update_playlists(playlists_cache)
            window.show_save_playlist_success(title, "YouTube Music")
        else:
            print("Error al guardar la playlist en YouTube Music.")
            window.show_save_playlist_error(title)
    else:
        # Guardar localmente
        print(f"Guardando la playlist '{title}' localmente...")
        playlist_id = playlist_manager.add_playlist(title, songs, source="imported")

        if playlist_id:
            print(f"Playlist guardada localmente con éxito. ID: {playlist_id}")
            playlists_cache = get_combined_playlists()
            window.update_playlists(playlists_cache)
            window.show_save_playlist_success(title, "local")
        else:
            print("Error al guardar la playlist localmente.")
            window.show_save_playlist_error(title)

    last_imported_playlist_data = None


def get_combined_playlists():
    """
    Combina playlists locales con las de YouTube Music.
    Retorna una lista unificada.
    """
    local_playlists = playlist_manager.get_all_playlists()

    if service.is_authenticated:
        ytmusic_playlists = service.get_library_playlists()
        return playlist_manager.merge_with_ytmusic_playlists(ytmusic_playlists)
    else:
        # Solo playlists locales
        return [{
            'playlistId': p['playlistId'],
            'title': p['title'],
            'source': p.get('source', 'local'),
            'track_count': len(p.get('tracks', []))
        } for p in local_playlists]


def handle_song_selected(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        current_song = queue_manager.play_now(song_data)
        if current_song:
            play_song(current_song)
            # Precargar las siguientes 5 canciones
            preload_next_songs(5)


def handle_add_to_queue(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]
        first_song = queue_manager.add_song(song_data)
        if first_song:
            play_song(first_song)
            # Precargar las siguientes 5 canciones
            preload_next_songs(5)
        else:
            # Si no es la primera canción, precargar la que acabamos de agregar
            if "videoId" in song_data:
                player.preload_stream(song_data["videoId"])


def handle_add_next(index):
    if 0 <= index < len(results_cache):
        song_data = results_cache[index]

        # queue_manager.add_next solo devuelve la canción si la cola estaba vacía
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
    if not player.has_media_loaded() and not player.is_playing:
        print("[PLAYER] No hay medios. Iniciando reproducción desde la cola.")
        current_song = queue_manager.get_current()
        if current_song:
            play_song(current_song)
        else:
            print("[PLAYER] No hay nada en la cola para reproducir.")
    else:
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
        # Precargar las siguientes 5 canciones
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
        # Verificar si debemos usar autoplay
        if queue_manager.should_autoplay():
            print("[AUTOPLAY] Activando reproducción automática...")
            handle_fetch_and_play_recommendation()
        else:
            # Modo LOOP_OFF o LOOP_QUEUE normal
            next_song = queue_manager.next()
            if next_song:
                play_song(next_song)
                preload_next_songs(5)
            else:
                # Se llegó al final de la cola y el modo es LOOP_OFF
                window.update_song_info("Cola terminada")
                window.update_play_button_icon(False)


def on_queue_updated():
    window.update_queue(queue_manager.get_queue(), queue_manager.get_current_index())


def handle_login(headers_raw):
    global playlists_cache
    success = service.setup_authentication(headers_raw)
    if success:
        window.show_auth_success()
        playlists_cache = get_combined_playlists()
        window.update_playlists(playlists_cache)
        window.update_auth_status(True)
    else:
        window.show_auth_error()
        window.update_auth_status(False)

def handle_logout():
    """Cierra la sesión del usuario."""
    global playlists_cache
    if service.logout():
        playlists_cache = get_combined_playlists()
        window.update_playlists(playlists_cache)
        window.update_auth_status(False)
        print("[AUTH] Sesión cerrada y UI actualizada.")
    else:
        print("[AUTH] Error al cerrar sesión.")


def handle_playlist_selected(index):
    """
    Se llama al hacer doble clic en una playlist de "Mis Playlists".
    """
    global results_cache
    if 0 <= index < len(playlists_cache):
        playlist = playlists_cache[index]
        playlist_id = playlist.get('playlistId')
        source = playlist.get('source', 'ytmusic')

        if not playlist_id:
            print(f"[ERROR] La playlist '{playlist.get('title')}' no tiene un 'playlistId' válido.")
            return

        # local o de YouTube Music
        if source in ['local', 'imported', 'user_created']:
            # Es una playlist local
            local_playlist = playlist_manager.get_playlist(playlist_id)
            if local_playlist and 'tracks' in local_playlist:
                songs_list = local_playlist['tracks']
                playlist_title = local_playlist['title']

                print(f"Cargando {len(songs_list)} canciones de la playlist local '{playlist_title}' a la cola.")

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
                print(f"No se pudo cargar la playlist local '{playlist.get('title')}'")
        else:
            # Es una playlist de YouTube Music
            songs_data = service.get_playlist_songs(playlist_id)

            if songs_data and 'tracks' in songs_data:
                songs_list = songs_data['tracks']
                playlist_title = songs_data.get('title', 'Playlist')

                print(f"Cargando {len(songs_list)} canciones de la playlist de YTMusic '{playlist_title}' a la cola.")

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

    # Cargar playlists combinadas (locales + YTMusic si hay sesión)
    playlists_cache = get_combined_playlists()
    window.update_playlists(playlists_cache)
    window.update_auth_status(service.is_authenticated)

    # Restaurar estado de la sesión anterior
    if os.path.exists(STATE_FILE):

        try:
            # Leer y mostrar tamaño
            file_size = os.path.getsize(STATE_FILE)

            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            # Verificar contenido
            saved_at = state_data.get('saved_at', 'desconocido')
            queue_data = state_data.get("queue", [])
            current_index = state_data.get("current_index", -1)
            stream_cache = state_data.get("stream_cache", {})

            # Restaurar en el player
            if stream_cache:
                player.set_stream_cache(stream_cache)

            # Restaurar en el queue manager
            if queue_data:
                queue_manager.set_queue_state(queue_data, current_index)

                # Actualizar UI
                on_queue_updated()

                # Seleccionar el ítem actual en la lista
                if 0 <= current_index < len(queue_data):
                    window.queue_list.setCurrentRow(current_index)

                    # Mostrar info de la canción (sin reproducirla)
                    current_song = queue_manager.get_current()
                    if current_song:
                        artist_name = current_song.get('artists', [{}])[0].get('name', 'Desconocido')
                        display_text = f"{current_song['title']} - {artist_name}"
                        window.update_song_info(display_text)


        except json.JSONDecodeError as e:
            try:
                os.remove(STATE_FILE)
            except:
                pass

        except Exception as e:
            traceback.print_exc()
            try:
                os.remove(STATE_FILE)
            except:
                pass


def handle_toggle_autoplay():
    """Activa/desactiva el modo de reproducción automática"""
    queue_manager.toggle_autoplay()


def handle_fetch_and_play_recommendation():
    """
    Obtiene una canción recomendada basada en la actual y la reproduce.
    """
    current_song = queue_manager.get_current()

    if not current_song or 'videoId' not in current_song:
        print("[AUTOPLAY] No hay canción actual para obtener recomendaciones")
        return

    print(f"[AUTOPLAY] Obteniendo recomendación basada en: {current_song['title']}")

    # Obtener recomendaciones
    recommendations = service.get_song_recommendations(current_song['videoId'], limit=10)

    if not recommendations:
        print("[AUTOPLAY] No se encontraron recomendaciones")
        window.update_song_info("No se encontraron recomendaciones")
        return

    # Filtrar canciones que ya están en la cola
    queue_video_ids = {song.get('videoId') for song in queue_manager.get_queue()}
    new_recommendations = [song for song in recommendations if song.get('videoId') not in queue_video_ids]

    if not new_recommendations:
        # Si todas las recomendaciones ya están en la cola, usar la primera de todas formas
        new_recommendations = recommendations[:1]

    # Tomar la primera recomendación
    recommended_song = new_recommendations[0]

    print(f"[AUTOPLAY] Agregando a la cola: {recommended_song['title']}")

    # Agregar a la cola y reproducir
    first_song = queue_manager.add_song(recommended_song)
    if first_song:
        play_song(first_song)
        preload_next_songs(5)
    else:
        # La canción se agregó pero no es la primera, avanzar a ella
        next_song = queue_manager.next()
        if next_song:
            play_song(next_song)
            preload_next_songs(5)


# --- 3. LÓGICA DE ARRANQUE MODIFICADA ---

def start_main_application():
    global player, queue_manager, window, app_icon, service, playlist_manager

    playlist_manager = PlaylistManager(BASE_DIR)
    player = Player(service)
    queue_manager = QueueManager()

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
        on_login_requested=handle_login,
        on_logout_requested=handle_logout,
        on_playlist_selected=handle_playlist_selected,
        on_import_playlist=handle_import_playlist,
        on_save_imported_playlist=handle_save_imported_playlist,
        on_result_highlighted=handle_result_highlighted,
        on_queue_item_moved=handle_queue_item_moved,
        on_toggle_loop=handle_toggle_loop,
        on_toggle_autoplay=handle_toggle_autoplay,
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
    queue_manager.autoplay_mode_changed.connect(window.update_autoplay_button_icon)
    window.clear_btn.clicked.connect(queue_manager.clear)

    atexit.register(save_state_on_exit)

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