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

# --- VARIABLES GLOBALES PARA LA LETRA ---
current_lyrics_lines = []
lyrics_active = False
last_highlighted_index = -1


# ---------------------------------------

def save_state_on_exit():
    print("[STATE] Guardando estado...")
    try:
        if queue_manager and player:
            queue = queue_manager.get_queue()
            current_index = queue_manager.get_current_index()
            stream_cache = player.get_stream_cache_for_saving()
            state_data = {"queue": queue, "current_index": current_index, "stream_cache": stream_cache}
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[STATE] Error: {e}")


def handle_result_highlighted(index):
    if 0 <= index < len(results_cache):
        song = results_cache[index]
        if "videoId" in song: player.preload_stream(song["videoId"])


def handle_queue_item_moved(src, dst): queue_manager.move_song(src, dst)


def handle_toggle_loop(): queue_manager.toggle_loop_mode()


def handle_search(query):
    global results_cache
    results_cache = service.search(query)
    window.update_results(results_cache)


def handle_import_playlist(url):
    global results_cache, last_imported_playlist_data
    match = PLAYLIST_RE.search(url)
    if match:
        data = service.get_playlist_songs(match.group(1))
        if data and data['tracks']:
            results_cache = [];
            window.update_results(results_cache)
            queue_manager.clear()
            for s in data['tracks']: queue_manager.add_song(s)
            play_song(queue_manager.jump_to(0));
            preload_next_songs(5)
            window.search_box.clear()
            last_imported_playlist_data = data
            window.ask_to_save_playlist(data['title'], service.is_authenticated)
        else:
            print("Error playlist vacía")
    else:
        print("URL inválida")


def handle_save_imported_playlist(save_to_ytmusic=False):
    global last_imported_playlist_data, playlists_cache
    if not last_imported_playlist_data: return
    title = last_imported_playlist_data['title']
    songs = last_imported_playlist_data['tracks']
    if save_to_ytmusic and service.is_authenticated:
        if service.create_playlist(title, "Importada", songs):
            playlists_cache = get_combined_playlists()
            window.update_playlists(playlists_cache)
            window.show_save_playlist_success(title, "YouTube Music")
        else:
            window.show_save_playlist_error(title)
    else:
        if playlist_manager.add_playlist(title, songs, "imported"):
            playlists_cache = get_combined_playlists()
            window.update_playlists(playlists_cache)
            window.show_save_playlist_success(title, "local")
        else:
            window.show_save_playlist_error(title)
    last_imported_playlist_data = None


def get_combined_playlists():
    local = playlist_manager.get_all_playlists()
    if service.is_authenticated:
        return playlist_manager.merge_with_ytmusic_playlists(service.get_library_playlists())
    return [{'playlistId': p['playlistId'], 'title': p['title'], 'source': p.get('source', 'local')} for p in local]


def handle_song_selected(index):
    if 0 <= index < len(results_cache):
        play_song(queue_manager.play_now(results_cache[index]));
        preload_next_songs(5)


def handle_add_to_queue(index):
    if 0 <= index < len(results_cache):
        s = results_cache[index]
        if queue_manager.add_song(s):
            play_song(s); preload_next_songs(5)
        else:
            player.preload_stream(s.get("videoId"))


def handle_add_next(index):
    if 0 <= index < len(results_cache):
        s = results_cache[index]
        if queue_manager.add_next(s):
            play_song(s); preload_next_songs(5)
        else:
            player.preload_stream(s.get("videoId"))


def preload_next_songs(count=5):
    q = queue_manager.get_queue();
    curr = queue_manager.get_current_index()
    for i in range(1, count + 1):
        if curr + i < len(q): player.preload_stream(q[curr + i].get("videoId"))


def play_song(song_data):
    global current_lyrics_lines, lyrics_active, last_highlighted_index
    if not song_data or "videoId" not in song_data:
        window.update_song_info("Error canción")
        return

    # Reseteamos variables de letra sin cambiar de pestaña
    current_lyrics_lines = []
    lyrics_active = False
    last_highlighted_index = -1

    # IMPORTANTE: switch_focus=False evita que se cambie la pestaña
    window.set_lyrics_message("...", switch_focus=False)

    video_id = song_data["videoId"]
    artist = song_data.get('artists', [{}])[0].get('name', 'Desconocido')
    window.update_play_button_icon(True)
    window.update_song_info(f"Cargando: {song_data['title']} - {artist}")

    if player.play(video_id):
        window.update_song_info(f"{song_data['title']} - {artist}")


def on_stream_ready(video_id, title):
    s = queue_manager.get_current()
    if s and s.get("videoId") == video_id:
        artist = s.get('artists', [{}])[0].get('name', 'Desconocido')
        window.update_song_info(f"{title} - {artist}")
        window.update_play_button_icon(True)


def on_stream_error(msg): window.update_song_info(f"Error: {msg}"); window.update_play_button_icon(False)


def handle_toggle_play():
    if not player.has_media_loaded() and not player.is_playing:
        s = queue_manager.get_current()
        if s: play_song(s)
    else:
        player.toggle_play()
        window.update_play_button_icon(player.is_playing)


def handle_volume_change(val): player.set_volume(val)


def handle_seek(pos): player.seek(pos)


def handle_next():
    s = queue_manager.next()
    if s: play_song(s); preload_next_songs(5)


def handle_previous():
    s = queue_manager.previous()
    if s: play_song(s)


def handle_remove_from_queue(idx): queue_manager.remove_at(idx)


def handle_queue_item_selected(idx):
    s = queue_manager.jump_to(idx)
    if s: play_song(s); preload_next_songs(5)


def on_song_finished():
    if queue_manager.get_loop_mode() == QueueManager.LOOP_SONG:
        s = queue_manager.get_current()
        if s: play_song(s)
    else:
        if queue_manager.should_autoplay():
            handle_fetch_and_play_recommendation()
        else:
            s = queue_manager.next()
            if s:
                play_song(s); preload_next_songs(5)
            else:
                window.update_song_info("Cola terminada"); window.update_play_button_icon(False)


def on_queue_updated(): window.update_queue(queue_manager.get_queue(), queue_manager.get_current_index())


def handle_login(headers):
    global playlists_cache
    if service.setup_authentication(headers):
        window.show_auth_success()
        playlists_cache = get_combined_playlists()
        window.update_playlists(playlists_cache)
        window.update_auth_status(True)
    else:
        window.show_auth_error(); window.update_auth_status(False)


def handle_logout():
    if service.logout():
        playlists_cache = get_combined_playlists()
        window.update_playlists(playlists_cache)
        window.update_auth_status(False)


def handle_playlist_selected(index):
    global results_cache
    if 0 <= index < len(playlists_cache):
        p = playlists_cache[index]
        pid = p.get('playlistId')
        src = p.get('source', 'ytmusic')
        if src in ['local', 'imported', 'user_created']:
            data = playlist_manager.get_playlist(pid)
        else:
            data = service.get_playlist_songs(pid)
        if data and 'tracks' in data:
            results_cache = [];
            window.update_results([])
            queue_manager.clear()
            for s in data['tracks']: queue_manager.add_song(s)
            play_song(queue_manager.jump_to(0));
            preload_next_songs(5)
        else:
            print("Error playlist")


def handle_toggle_autoplay(): queue_manager.toggle_autoplay()


def handle_fetch_and_play_recommendation():
    s = queue_manager.get_current()
    if not s: return
    recs = service.get_song_recommendations(s['videoId'], 10)
    if not recs: return
    q_ids = {x.get('videoId') for x in queue_manager.get_queue()}
    new_recs = [x for x in recs if x.get('videoId') not in q_ids]
    rec = new_recs[0] if new_recs else recs[0]
    if queue_manager.add_song(rec):
        play_song(rec); preload_next_songs(5)
    else:
        play_song(queue_manager.next()); preload_next_songs(5)


# --- MANEJO DE LETRAS ---

def time_str_to_ms(time_str):
    if not time_str: return 0
    try:
        parts = time_str.split(':')
        seconds = 0
        if len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            seconds = float(time_str)
        return int(seconds * 1000)
    except:
        return 0


def handle_show_lyrics():
    """Obtiene la letra y la muestra en la lista"""
    global current_lyrics_lines, lyrics_active, last_highlighted_index

    s = queue_manager.get_current()
    # Si no hay canción, mensaje y NO cambio de pestaña
    if not s: window.set_lyrics_message("Sin canción", switch_focus=False); return

    # Si hay canción y el usuario pidió la letra, cambiamos de pestaña
    window.set_lyrics_message(f"Buscando letra de:\n{s['title']}...", switch_focus=True)

    lyrics_data = service.get_song_lyrics(s.get("videoId"))

    if s != queue_manager.get_current(): return

    if lyrics_data:
        # 1. Caso: Letra sincronizada
        if 'lines' in lyrics_data and lyrics_data['lines']:
            raw_lines = lyrics_data['lines']
            processed_lines = []
            has_timing = False

            for line in raw_lines:
                text = line.get('text', '')
                t_str = line.get('time', '0:00')
                t_ms = time_str_to_ms(t_str)

                if t_ms > 0: has_timing = True
                processed_lines.append({'text': text, 'time_ms': t_ms})

            current_lyrics_lines = processed_lines
            lyrics_active = has_timing
            last_highlighted_index = -1

            text_only = [l['text'] for l in processed_lines]
            window.set_lyrics_lines(text_only)

        # 2. Caso: Texto plano
        elif lyrics_data.get('lyrics'):
            current_lyrics_lines = []
            lyrics_active = False
            text_lines = lyrics_data['lyrics'].split('\n')
            window.set_lyrics_lines(text_lines)
        else:
            window.set_lyrics_message("Formato desconocido.", switch_focus=True)
    else:
        window.set_lyrics_message("Letra no encontrada.", switch_focus=True)


def on_time_ms_updated(current_ms):
    global last_highlighted_index

    if not lyrics_active or not current_lyrics_lines:
        return

    active_index = -1
    start = max(0, last_highlighted_index)

    for i in range(len(current_lyrics_lines)):
        line_time = current_lyrics_lines[i]['time_ms']
        if current_ms >= line_time:
            active_index = i
        else:
            break

    if active_index != -1 and active_index != last_highlighted_index:
        window.highlight_lyric_index(active_index)
        last_highlighted_index = active_index


# ----------------------------------------------

def initial_load():
    global playlists_cache
    playlists_cache = get_combined_playlists()
    window.update_playlists(playlists_cache)
    window.update_auth_status(service.is_authenticated)
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
            player.set_stream_cache(d.get("stream_cache", {}))
            queue_manager.set_queue_state(d.get("queue", []), d.get("current_index", -1))
            on_queue_updated()
            idx = queue_manager.get_current_index()
            if idx >= 0:
                window.queue_list.setCurrentRow(idx)
                s = queue_manager.get_current()
                if s: window.update_song_info(f"{s['title']} - {s['artists'][0]['name']}")
        except:
            pass


def start_main_application():
    global player, queue_manager, window, app_icon, service, playlist_manager
    playlist_manager = PlaylistManager(BASE_DIR)
    player = Player(service)
    queue_manager = QueueManager()
    window = MainWindow(
        handle_search, handle_song_selected, handle_add_to_queue, handle_toggle_play, handle_add_next,
        handle_volume_change, handle_seek, handle_next, handle_previous, handle_remove_from_queue,
        handle_queue_item_selected, handle_login, handle_playlist_selected, handle_import_playlist,
        app_icon, handle_save_imported_playlist, handle_result_highlighted, handle_queue_item_moved,
        handle_toggle_loop, handle_logout, handle_toggle_autoplay, handle_show_lyrics
    )
    player.position_changed.connect(window.update_progress)
    player.time_changed.connect(window.update_time)
    player.current_time_ms.connect(on_time_ms_updated)
    player.song_finished.connect(on_song_finished)
    player.stream_ready.connect(on_stream_ready)
    player.stream_error.connect(on_stream_error)
    queue_manager.queue_updated.connect(on_queue_updated)
    queue_manager.current_changed.connect(on_queue_updated)
    queue_manager.loop_mode_changed.connect(window.update_loop_button_icon)
    queue_manager.autoplay_mode_changed.connect(window.update_autoplay_button_icon)
    window.clear_btn.clicked.connect(queue_manager.clear)
    atexit.register(save_state_on_exit)
    initial_load()
    window.resize(1080, 750)
    window.show()
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