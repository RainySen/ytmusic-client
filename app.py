import atexit
import json
import os
import re
import sys
import traceback

import qtawesome as qta
from PySide6.QtWidgets import QApplication

from core.player import Player
from core.playlist_manager import PlaylistManager
from core.queue_manager import QueueManager
from services.ytmusic_service import YTMusicService
from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from platform_utils import get_config_dir, get_base_dir, get_platform, print_platform_info

if "--debug" in sys.argv:
    print_platform_info()

if getattr(sys, 'frozen', False):
    BASE_DIR = get_base_dir()
    CONFIG_DIR = get_config_dir()
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR = BASE_DIR

print(f"[PLATFORM] Sistema: {get_platform()}")
print(f"[PLATFORM] Directorio base: {BASE_DIR}")
print(f"[PLATFORM] Directorio de configuración: {CONFIG_DIR}")

# Const
DEFAULT_PRELOAD_COUNT = 5
PLAYLIST_URL_PATTERN = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")
STATE_FILENAME = "queue_and_cache.json"
STATE_FILE = os.path.join(CONFIG_DIR, STATE_FILENAME)

# Application state

class ApplicationState:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.state_file = os.path.join(base_dir, STATE_FILENAME)

        # Core services
        self.service = None
        self.player = None
        self.queue_manager = None
        self.playlist_manager = None

        self.window = None
        self.login_window = None

        # Cache
        self.results_cache = []
        self.playlists_cache = []
        self.last_imported_playlist_data = None

        # Lyrics
        self.current_lyrics_lines = []
        self.lyrics_active = False
        self.last_highlighted_index = -1

    def save_state(self):
        """Save current queue and player state"""
        print("[STATE] Guardando estado...")
        try:
            if self.queue_manager and self.player:
                state_data = {
                    "queue": self.queue_manager.get_queue(),
                    "current_index": self.queue_manager.get_current_index(),
                    "stream_cache": self.player.get_stream_cache_for_saving()
                }

                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
                print(f"[STATE] Estado guardado en: {self.state_file}")
        except Exception as e:
            print(f"[STATE] Error: {e}")

    def load_state(self):
        """Load saved state"""
        if not os.path.exists(self.state_file):
            return

        try:
            print(f"[STATE] Cargando estado desde: {self.state_file}")
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.player.set_stream_cache(data.get("stream_cache", {}))
            self.queue_manager.set_queue_state(
                data.get("queue", []),
                data.get("current_index", -1)
            )

            # Update UI
            idx = self.queue_manager.get_current_index()
            if idx >= 0:
                # Queue UI will update via queue_updated signal
                song = self.queue_manager.get_current()
                if song:
                    artist = song.get('artists', [{}])[0].get('name', 'Desconocido')
                    self.window.update_song_info(f"{song['title']} - {artist}")
        except Exception as e:
            print(f"[STATE] Error loading state: {e}")
            traceback.print_exc()


# Search and result

class SearchHandler:
    """search-related operations"""

    def __init__(self, state):
        self.state = state

    def search(self, query):
        """search and update results"""
        self.state.results_cache = self.state.service.search(query)
        self.state.window.update_results(self.state.results_cache)

    def handle_result_highlighted(self, index):
        """Preload stream when result is highlighted"""
        if 0 <= index < len(self.state.results_cache):
            song = self.state.results_cache[index]
            if "videoId" in song:
                self.state.player.preload_stream(song["videoId"])

    def handle_song_selected(self, index):
        """Play selected song from search results"""
        if 0 <= index < len(self.state.results_cache):
            song = self.state.queue_manager.play_now(self.state.results_cache[index])
            PlaybackController(self.state).play_song(song)
            self._preload_upcoming_songs()

    def handle_add_to_queue(self, index):
        """Add song to end"""
        if 0 <= index < len(self.state.results_cache):
            song = self.state.results_cache[index]

            if self.state.queue_manager.add_song(song):
                PlaybackController(self.state).play_song(song)
                self._preload_upcoming_songs()
            else:
                self.state.player.preload_stream(song.get("videoId"))

    def handle_add_next(self, data):
        """Add song to play next"""
        if isinstance(data, dict):
            song = data

        elif isinstance(data, int):
            if 0 <= data < len(self.state.results_cache):
                song = self.state.results_cache[data]
            else:
                return
        else:
            return

        added = self.state.queue_manager.add_song(song)

        if added:
            PlaybackController(self.state).play_song(song)
            self._preload_upcoming_songs()
        else:
            self.state.player.preload_stream(song.get("videoId"))

    def _preload_upcoming_songs(self, count=DEFAULT_PRELOAD_COUNT):
        """Preload next songs"""
        queue = self.state.queue_manager.get_queue()
        current_idx = self.state.queue_manager.get_current_index()

        for i in range(1, count + 1):
            if current_idx + i < len(queue):
                video_id = queue[current_idx + i].get("videoId")
                self.state.player.preload_stream(video_id)


# Playback

class PlaybackController:
    """playback operations"""

    def __init__(self, state):
        self.state = state

    def play_song(self, song_data):
        if not song_data or "videoId" not in song_data:
            self.state.window.update_song_info("Error canción")
            return

        queue = self.state.queue_manager
        if song_data not in queue.get_queue():
            queue.add_song(song_data)

        #current index
        current_index = queue.get_queue().index(song_data)
        queue.current_index = current_index
        queue.current_changed.emit(current_index)

        # lyrics state
        self.state.current_lyrics_lines = []
        self.state.lyrics_active = False
        self.state.last_highlighted_index = -1
        self.state.window.set_lyrics_message("...", switch_focus=False)

        # song info
        video_id = song_data["videoId"]
        artist = song_data.get("artists", [{}])[0].get("name", "Desconocido")

        self.state.window.update_play_button_icon(True)
        self.state.window.update_song_info(f"Cargando: {song_data['title']} - {artist}")


        if self.state.player.play(video_id):
            self.state.window.update_song_info(f"{song_data['title']} - {artist}")

    def toggle_play(self):
        """play/pause state"""
        if not self.state.player.has_media_loaded() and not self.state.player.is_playing:
            song = self.state.queue_manager.get_current()
            if song:
                self.play_song(song)
        else:
            self.state.player.toggle_play()
            self.state.window.update_play_button_icon(self.state.player.is_playing)

    def next_song(self):
        song = self.state.queue_manager.next()
        if song:
            self.play_song(song)
            self._preload_upcoming_songs()

    def previous_song(self):
        song = self.state.queue_manager.previous()
        if song:
            self.play_song(song)

    def seek(self, position):
        """Seek to position in current song"""
        self.state.player.seek(position)

    def set_volume(self, value):
        self.state.player.set_volume(value)

    def on_song_finished(self):
        # loop mode
        if self.state.queue_manager.get_loop_mode() == QueueManager.LOOP_SONG:
            song = self.state.queue_manager.get_current()
            if song:
                self.play_song(song)
            return

        # autoplay
        if self.state.queue_manager.should_autoplay():
            RecommendationHandler(self.state).fetch_and_play_recommendation()
            return

        # Normal flow
        song = self.state.queue_manager.next()
        if song:
            self.play_song(song)
            self._preload_upcoming_songs()
        else:
            self.state.window.update_song_info("Cola terminada")
            self.state.window.update_play_button_icon(False)

    def on_stream_ready(self, video_id, title):
        song = self.state.queue_manager.get_current()
        if song and song.get("videoId") == video_id:
            artist = song.get('artists', [{}])[0].get('name', 'Desconocido')
            self.state.window.update_song_info(f"{title} - {artist}")
            self.state.window.update_play_button_icon(True)

    def on_stream_error(self, message):
        self.state.window.update_song_info(f"Error: {message}")
        self.state.window.update_play_button_icon(False)

    def _preload_upcoming_songs(self, count=DEFAULT_PRELOAD_COUNT):
        queue = self.state.queue_manager.get_queue()
        current_idx = self.state.queue_manager.get_current_index()

        for i in range(1, count + 1):
            if current_idx + i < len(queue):
                video_id = queue[current_idx + i].get("videoId")
                self.state.player.preload_stream(video_id)


# Queue management

class QueueHandler:
    """queue-related operations"""

    def __init__(self, state):
        self.state = state

    def clear_queue(self):
        self.state.queue_manager.clear()

    def remove_from_queue(self, index):
        self.state.queue_manager.remove_at(index)

    def jump_to_song(self, index):
        song = self.state.queue_manager.jump_to(index)
        if song:
            PlaybackController(self.state).play_song(song)
            self._preload_upcoming_songs()

    def move_song(self, source_index, dest_index):
        self.state.queue_manager.move_song(source_index, dest_index)

    def toggle_loop_mode(self):
        self.state.queue_manager.toggle_loop_mode()

    def toggle_autoplay(self):
        self.state.queue_manager.toggle_autoplay()

    def on_queue_updated(self):
        self.state.window.update_queue(
            self.state.queue_manager.get_queue(),
            self.state.queue_manager.get_current_index()
        )

    def _preload_upcoming_songs(self, count=DEFAULT_PRELOAD_COUNT):
        queue = self.state.queue_manager.get_queue()
        current_idx = self.state.queue_manager.get_current_index()

        for i in range(1, count + 1):
            if current_idx + i < len(queue):
                video_id = queue[current_idx + i].get("videoId")
                self.state.player.preload_stream(video_id)


# Playlist

class PlaylistHandler:
    """Handles playlist operations"""

    def __init__(self, state):
        self.state = state

    def get_combined_playlists(self):
        """Get both local and YTMusic playlists"""
        local_playlists = self.state.playlist_manager.get_all_playlists()

        if self.state.service.is_authenticated:
            ytmusic_playlists = self.state.service.get_library_playlists()
            return self.state.playlist_manager.merge_with_ytmusic_playlists(ytmusic_playlists)

        return [{
            'playlistId': p['playlistId'],
            'title': p['title'],
            'source': p.get('source', 'local')
        } for p in local_playlists]

    def select_playlist(self, index):
        """Load and play a playlist"""
        if not (0 <= index < len(self.state.playlists_cache)):
            return

        playlist = self.state.playlists_cache[index]
        playlist_id = playlist.get('playlistId')
        source = playlist.get('source', 'ytmusic')

        # Get playlist data based on source
        if source in ['local', 'imported', 'user_created']:
            data = self.state.playlist_manager.get_playlist(playlist_id)
        else:
            data = self.state.service.get_playlist_songs(playlist_id)

        if not data or 'tracks' not in data:
            print("Error loading playlist")
            return

        # Clear current state and load playlist
        self.state.player.stop()
        self.state.results_cache = []
        self.state.window.update_results([])
        self.state.queue_manager.clear(keep_current=False)

        for song in data['tracks']:
            self.state.queue_manager.add_song(song)

        # Start playing
        song = self.state.queue_manager.jump_to(0)
        PlaybackController(self.state).play_song(song)
        SearchHandler(self.state)._preload_upcoming_songs()

    def import_playlist(self, url):
        match = PLAYLIST_URL_PATTERN.search(url)
        if not match:
            self.state.window.show_import_error(
                "URL inválida. Formato esperado: https://music.youtube.com/playlist?list=PLxxxxxx"
            )
            return

        playlist_id = match.group(1)

        try:
            data = self.state.service.get_playlist_songs(playlist_id)

            if not data:
                self.state.window.show_import_error(
                    "No se pudo acceder a la playlist. Verifica:\n"
                    "- La URL es correcta\n"
                    "- La playlist no está privada\n"
                    "- Tienes conexión a internet"
                )
                return

            if not data.get('tracks'):
                self.state.window.show_import_error(
                    "La playlist está vacía o no tiene canciones accesibles."
                )
                return

            # Clear and load playlist
            self.state.player.stop()
            self.state.results_cache = []
            self.state.window.update_results([])
            self.state.queue_manager.clear(keep_current=False)

            for song in data['tracks']:
                self.state.queue_manager.add_song(song)

            # Start playing
            first_song = self.state.queue_manager.jump_to(0)
            if first_song:
                PlaybackController(self.state).play_song(first_song)
                SearchHandler(self.state)._preload_upcoming_songs()

            self.state.window.top_bar.search_box.clear()
            self.state.last_imported_playlist_data = data

            # Ask user to save
            self.state.window.ask_to_save_playlist(
                data['title'],
                self.state.service.is_authenticated
            )

        except Exception as e:
            traceback.print_exc()
            self.state.window.show_import_error(f"Error al importar:\n{str(e)}")

    def save_imported_playlist(self, save_to_ytmusic=False):
        """Save the last imported playlist"""
        if not self.state.last_imported_playlist_data:
            print("[SAVE] No hay datos para guardar")
            return

        title = self.state.last_imported_playlist_data['title']
        songs = self.state.last_imported_playlist_data['tracks']

        try:
            if save_to_ytmusic and self.state.service.is_authenticated:
                result = self.state.service.create_playlist(
                    title,
                    "Importada desde YTMusic Client",
                    songs
                )

                if result:
                    self._update_playlists_cache()
                    self.state.window.show_save_playlist_success(title, "YouTube Music")
                else:
                    self.state.window.show_save_playlist_error(title)
            else:
                # Save locally
                self._ensure_playlists_directory()
                result = self.state.playlist_manager.add_playlist(title, songs, "imported")

                if result:
                    self._update_playlists_cache()
                    self.state.window.show_save_playlist_success(title, "local")
                else:
                    self.state.window.show_save_playlist_error(title)

            self.state.last_imported_playlist_data = None

        except Exception as e:
            traceback.print_exc()
            self.state.window.show_save_playlist_error(title)

    def _ensure_playlists_directory(self):
        """Ensure playlists directory exists"""
        playlists_dir = os.path.dirname(self.state.playlist_manager.playlists_file)
        if not os.path.exists(playlists_dir):
            os.makedirs(playlists_dir, exist_ok=True)

    def _update_playlists_cache(self):
        self.state.playlists_cache = self.get_combined_playlists()
        self.state.window.update_playlists(self.state.playlists_cache)


# Auth

class AuthenticationHandler:
    """Authentication operations"""

    def __init__(self, state):
        self.state = state

    def login(self, headers):
        success = self.state.service.setup_authentication(headers)

        if success:
            if self.state.window:
                self.state.window.show_auth_success()
                self._update_after_auth(True)

            if self.state.login_window:
                self.state.login_window.login_success.emit()

        else:
            if self.state.window:
                self.state.window.show_auth_error()
                self.state.window.update_auth_status(False)
            elif self.state.login_window:
                self.state.login_window._show_error_message()

    def logout(self):
        """Logout from YTMusic"""
        if self.state.service.logout():
            self._update_after_auth(False)

    def _update_after_auth(self, is_authenticated):
        """Update UI and cache after authentication change"""
        playlist_handler = PlaylistHandler(self.state)
        self.state.playlists_cache = playlist_handler.get_combined_playlists()
        self.state.window.update_playlists(self.state.playlists_cache)
        self.state.window.update_auth_status(is_authenticated)

        # Refresh home feed so personalized content loads immediately
        if self.state.window and hasattr(self.state.window, 'callbacks'):
            home_cb = self.state.window.callbacks.get('home')
            if home_cb:
                home_cb()


# Recommendations

class RecommendationHandler:
    """Handles song recommendations"""

    def __init__(self, state):
        self.state = state

    def fetch_and_play_recommendation(self):
        current_song = self.state.queue_manager.get_current()
        if not current_song:
            return

        recommendations = self.state.service.get_song_recommendations(
            current_song['videoId'],
            10
        )

        if not recommendations:
            return

        # Filter out songs already in queue
        queue_video_ids = {
            song.get('videoId')
            for song in self.state.queue_manager.get_queue()
        }

        new_recommendations = [
            rec for rec in recommendations
            if rec.get('videoId') not in queue_video_ids
        ]

        # Pick first new recommendation or fallback to first overall
        recommendation = (
            new_recommendations[0] if new_recommendations
            else recommendations[0]
        )

        # Add to queue and play
        if self.state.queue_manager.add_song(recommendation):
            PlaybackController(self.state).play_song(recommendation)
            SearchHandler(self.state)._preload_upcoming_songs()
        else:
            next_song = self.state.queue_manager.next()
            PlaybackController(self.state).play_song(next_song)
            SearchHandler(self.state)._preload_upcoming_songs()


# lyrics

class LyricsHandler:
    """Lyrics display and synchronization"""

    def __init__(self, state):
        self.state = state

    def show_lyrics(self):
        """Fetch and display lyrics for current song"""
        current_song = self.state.queue_manager.get_current()

        if not current_song:
            self.state.window.set_lyrics_message("Sin canción", switch_focus=False)
            return

        # Show loading message
        self.state.window.set_lyrics_message(
            f"Buscando letra de:\n{current_song['title']}...",
            switch_focus=True
        )

        # Fetch lyrics
        lyrics_data = self.state.service.get_song_lyrics(current_song.get("videoId"))

        # Check if song changed while fetching
        if current_song != self.state.queue_manager.get_current():
            return

        if not lyrics_data:
            self.state.window.set_lyrics_message("Letra no encontrada.", switch_focus=True)
            return

        # Process synced lyrics
        if 'lines' in lyrics_data and lyrics_data['lines']:
            self._process_synced_lyrics(lyrics_data['lines'])
        # Process plain text lyrics
        elif lyrics_data.get('lyrics'):
            self._process_plain_lyrics(lyrics_data['lyrics'])
        else:
            self.state.window.set_lyrics_message("Formato desconocido.", switch_focus=True)

    def update_lyrics_highlight(self, current_time_ms):
        """Update highlighted lyric line based on playback time"""
        if not self.state.lyrics_active or not self.state.current_lyrics_lines:
            return

        active_index = self._find_active_lyric_index(current_time_ms)

        if active_index != -1 and active_index != self.state.last_highlighted_index:
            self.state.window.highlight_lyric_index(active_index)
            self.state.last_highlighted_index = active_index

    def _process_synced_lyrics(self, raw_lines):
        """Process lyrics with timing information"""
        processed_lines = []
        has_timing = False

        for line in raw_lines:
            text = line.get('text', '')
            time_str = line.get('time', '0:00')
            time_ms = self._parse_time_string(time_str)

            if time_ms > 0:
                has_timing = True

            processed_lines.append({
                'text': text,
                'time_ms': time_ms
            })

        self.state.current_lyrics_lines = processed_lines
        self.state.lyrics_active = has_timing
        self.state.last_highlighted_index = -1

        text_only = [line['text'] for line in processed_lines]
        self.state.window.set_lyrics_lines(text_only)

    def _process_plain_lyrics(self, lyrics_text):
        """Process plain text lyrics without timing"""
        self.state.current_lyrics_lines = []
        self.state.lyrics_active = False

        text_lines = lyrics_text.split('\n')
        self.state.window.set_lyrics_lines(text_lines)

    def _find_active_lyric_index(self, current_time_ms):
        """Find which lyric line should be highlighted"""
        active_index = -1

        for i, line in enumerate(self.state.current_lyrics_lines):
            if current_time_ms >= line['time_ms']:
                active_index = i
            else:
                break

        return active_index

    @staticmethod
    def _parse_time_string(time_str):
        """Convert time string to milliseconds"""
        if not time_str:
            return 0

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


# Home

from PySide6.QtCore import QThread, Signal as QtSignal


class _HomeLoaderThread(QThread):
    """Load the home screen in the background so as not to block the UI."""
    sections_ready = QtSignal(list)
    load_error = QtSignal(str)

    def __init__(self, service):
        super().__init__()
        self.service = service

    def run(self):
        try:
            home_data = self.service.get_home()
            parsed = []
            for section in home_data:
                title = section.get("title", "Sección")
                content = self.service.parse_home_section(section)
                if content:
                    parsed.append({"title": title, "items": content})
            self.sections_ready.emit(parsed)
        except Exception as e:
            import traceback as tb
            print(f"[HOME] Error en hilo de carga: {e}")
            tb.print_exc()
            self.load_error.emit(str(e))


class HomeHandler:
    """Home screen"""

    def __init__(self, state):
        self.state = state
        self._loader_thread = None  # Keep reference to prevent GC

    def show_home(self):
        """Load home screen in background."""
        self.state.window.show_home_loading()

        # Clear previous thread if it's still running
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.quit()
            self._loader_thread.wait(500)

        self._loader_thread = _HomeLoaderThread(self.state.service)
        self._loader_thread.sections_ready.connect(self._on_sections_ready)
        self._loader_thread.load_error.connect(self._on_load_error)
        self._loader_thread.start()

    def _on_sections_ready(self, parsed_sections):
        # Check if session expired silently during home load
        if not parsed_sections and not self.state.service.is_authenticated:
            self.state.window.show_home_error(
                "Tu sesión ha expirado.\n"
                "Por favor, inicia sesión de nuevo desde el botón de usuario."
            )
            self.state.window.update_auth_status(False)
            return

        if not parsed_sections:
            self.state.window.show_home_empty()
        else:
            self.state.window.show_home(parsed_sections)

    def _on_load_error(self, error_msg):
        self.state.window.show_home_error(error_msg)


# Application controllers

class ApplicationController:
    """Main application controller - wires everything together"""

    def __init__(self, base_dir, service):
        self.state = ApplicationState(base_dir)
        self.state.service = service

        # Initialize handlers immediately so signals can connect before start_main_application
        self.search_handler = SearchHandler(self.state)
        self.playback_controller = PlaybackController(self.state)
        self.queue_handler = QueueHandler(self.state)
        self.playlist_handler = PlaylistHandler(self.state)
        self.auth_handler = AuthenticationHandler(self.state)
        self.recommendation_handler = RecommendationHandler(self.state)
        self.lyrics_handler = LyricsHandler(self.state)
        self.home_handler = HomeHandler(self.state)

    def start_main_application(self, app_icon=None):
        # Initialize core components
        self.state.playlist_manager = PlaylistManager(CONFIG_DIR)
        self.state.player = Player(self.state.service)
        self.state.queue_manager = QueueManager()

        # Create main window with all handlers
        self.state.window = MainWindow(
            self.search_handler.search,
            self.search_handler.handle_song_selected,
            self.search_handler.handle_add_to_queue,
            self.playback_controller.toggle_play,
            self.search_handler.handle_add_next,
            self.playback_controller.set_volume,
            self.playback_controller.seek,
            self.playback_controller.next_song,
            self.playback_controller.previous_song,
            self.queue_handler.remove_from_queue,
            self.queue_handler.jump_to_song,
            self.auth_handler.login,
            self.playlist_handler.select_playlist,
            self.playlist_handler.import_playlist,
            app_icon,
            self.playlist_handler.save_imported_playlist,
            self.search_handler.handle_result_highlighted,
            self.queue_handler.move_song,
            self.queue_handler.toggle_loop_mode,
            self.auth_handler.logout,
            self.queue_handler.toggle_autoplay,
            self.lyrics_handler.show_lyrics,
            self.home_handler.show_home,
            self.queue_handler.clear_queue
        )

        if app_icon:
            self.state.window.setWindowIcon(app_icon)

        # Connect signals
        self._connect_signals()

        # Register exit handler
        atexit.register(self.state.save_state)

        # Initial load
        self._initial_load()

        # Show window
        self.state.window.resize(1240, 750)
        self.state.window.show()

        if self.state.login_window:
            self.state.login_window.close()

    def _connect_signals(self):
        # Player signals
        self.state.player.position_changed.connect(self.state.window.update_progress)
        self.state.player.time_changed.connect(self.state.window.update_time)
        self.state.player.current_time_ms.connect(self.lyrics_handler.update_lyrics_highlight)
        self.state.player.song_finished.connect(self.playback_controller.on_song_finished)
        self.state.player.stream_ready.connect(self.playback_controller.on_stream_ready)
        self.state.player.stream_error.connect(self.playback_controller.on_stream_error)

        # Queue manager signals
        self.state.queue_manager.queue_updated.connect(self.queue_handler.on_queue_updated)
        self.state.queue_manager.current_changed.connect(self.queue_handler.on_queue_updated)
        self.state.queue_manager.loop_mode_changed.connect(
            self.state.window.update_loop_button_icon
        )
        self.state.queue_manager.autoplay_mode_changed.connect(
            self.state.window.update_autoplay_button_icon
        )

    def _initial_load(self):
        # Load playlists
        self.state.playlists_cache = self.playlist_handler.get_combined_playlists()
        self.state.window.update_playlists(self.state.playlists_cache)
        self.state.window.update_auth_status(self.state.service.is_authenticated)

        self.state.player.set_volume(50)

        # Load saved state
        self.state.load_state()
        self.queue_handler.on_queue_updated()


# Main entrypoint

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app_icon = qta.icon('fa5s.music', color='#03adb7')
    app.setWindowIcon(app_icon)

    service = YTMusicService(CONFIG_DIR)
    controller = ApplicationController(CONFIG_DIR, service)

    login_window = LoginWindow(service, app_icon, service.is_authenticated)
    controller.state.login_window = login_window

    login_window.login_requested.connect(controller.auth_handler.login)
    login_window.login_success.connect(lambda: controller.start_main_application(app_icon))
    login_window.login_skipped.connect(lambda: controller.start_main_application(app_icon))

    login_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()