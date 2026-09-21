import json
import os
import re

from core.music_controller import MusicController
from core.playlist_controller import PlaylistController


class AppController:
    def __init__(self, base_dir, service):
        self.base_dir = base_dir
        self.service = service
        self.player = None
        self.queue_manager = None
        self.playlist_manager = None
        self.window = None
        self.login_window = None

        self.results_cache = []
        self.playlists_cache = []
        self.last_imported_playlist_data = None
        self.PLAYLIST_RE = re.compile(r"(?:list=)([a-zA-Z0-9\-_]+)")
        self.STATE_FILE = os.path.join(base_dir, "queue_and_cache.json")

        self.current_lyrics_lines = []
        self.lyrics_active = False
        self.last_highlighted_index = -1

        self.music_controller = MusicController(self)
        self.playlist_controller = PlaylistController(self)

    def bind_runtime(self, player, queue_manager, playlist_manager, window, login_window=None):
        self.player = player
        self.queue_manager = queue_manager
        self.playlist_manager = playlist_manager
        self.window = window
        self.login_window = login_window

    def save_state_on_exit(self):
        print("[STATE] Guardando estado...")
        try:
            if self.queue_manager and self.player:
                queue = self.queue_manager.get_queue()
                current_index = self.queue_manager.get_current_index()
                stream_cache = self.player.get_stream_cache_for_saving()
                state_data = {
                    "queue": queue,
                    "current_index": current_index,
                    "stream_cache": stream_cache,
                }
                with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[STATE] Error: {e}")

    def handle_result_highlighted(self, index):
        if 0 <= index < len(self.results_cache):
            song = self.results_cache[index]
            if "videoId" in song:
                self.player.preload_stream(song["videoId"])

    def handle_queue_item_moved(self, src, dst):
        self.queue_manager.move_song(src, dst)

    def handle_toggle_loop(self):
        self.queue_manager.toggle_loop_mode()

    def handle_search(self, query):
        self.results_cache = self.service.search(query)
        self.window.update_results(self.results_cache)

    def handle_import_playlist(self, url):
        self.playlist_controller.handle_import_playlist(url)

    def handle_save_imported_playlist(self, save_to_ytmusic=False):
        self.playlist_controller.handle_save_imported_playlist(save_to_ytmusic)

    def handle_song_selected(self, index):
        if 0 <= index < len(self.results_cache):
            song = self.results_cache[index]
            if song.get("videoId"):
                self.queue_manager.clear_radio_mode()
                self.start_radio_from_song(song)
                return
            self.music_controller.play_song(self.queue_manager.play_now(song))
            self.music_controller.preload_next_songs(5)

    def start_radio_from_song(self, song, max_recommendations=4):
        if not song or not song.get("videoId"):
            return

        self.queue_manager.clear_radio_mode()
        recommendations = self.service.get_song_recommendations(song["videoId"], max_recommendations)

        self.queue_manager.set_radio_queue(song, recommendations)

        for item in self.queue_manager.get_queue()[1:4]:
            if item.get("videoId"):
                self.player.preload_stream(item["videoId"])

        current = self.queue_manager.get_current()
        if current:
            self.music_controller.play_song(current)
            self.music_controller.preload_next_songs(min(3, max(0, len(self.queue_manager.get_queue()) - 1)))

        self.queue_manager.autoplay_enabled = True
        self.queue_manager.autoplay_mode_changed.emit(True)

    def handle_add_to_queue(self, index):
        if 0 <= index < len(self.results_cache):
            s = self.results_cache[index]
            self.queue_manager.clear_radio_mode()
            if self.queue_manager.add_song(s):
                self.music_controller.play_song(s)
                self.music_controller.preload_next_songs(5)
            else:
                self.player.preload_stream(s.get("videoId"))

    def handle_add_next(self, index):
        if 0 <= index < len(self.results_cache):
            s = self.results_cache[index]
            self.queue_manager.clear_radio_mode()
            if self.queue_manager.add_next(s):
                self.music_controller.play_song(s)
                self.music_controller.preload_next_songs(5)
            else:
                self.player.preload_stream(s.get("videoId"))

    def handle_clear_queue(self):
        self.queue_manager.clear()

    def handle_save_queue_playlist(self, title=None):
        if not self.queue_manager:
            return

        queue = self.queue_manager.get_queue()
        if not queue:
            self.window.show_save_playlist_error("La cola está vacía")
            return

        playlist_title = title or "Mi Cola"
        tracks = [song for song in queue if isinstance(song, dict) and song.get("videoId")]
        if not tracks:
            self.window.show_save_playlist_error("No hay canciones válidas para guardar")
            return

        self.playlist_controller.save_queue_playlist(playlist_title, tracks)

    def handle_toggle_play(self):
        self.music_controller.handle_toggle_play()

    def handle_volume_change(self, val):
        self.music_controller.handle_volume_change(val)

    def handle_seek(self, pos):
        self.music_controller.handle_seek(pos)

    def handle_next(self):
        self.music_controller.handle_next()

    def handle_previous(self):
        self.music_controller.handle_previous()

    def handle_remove_from_queue(self, idx):
        self.music_controller.handle_remove_from_queue(idx)

    def handle_queue_item_selected(self, idx):
        self.music_controller.handle_queue_item_selected(idx)

    def on_song_finished(self):
        if self.queue_manager.get_loop_mode() == self.queue_manager.LOOP_SONG:
            s = self.queue_manager.get_current()
            if s:
                self.music_controller.play_song(s)
        else:
            if self.queue_manager.should_autoplay():
                current_song = self.queue_manager.get_current()
                if self.queue_manager.radio_mode and current_song:
                    next_song = self.queue_manager.next()
                    if next_song:
                        self.music_controller.play_song(next_song)
                        self.music_controller.preload_next_songs(3)
                        if self.queue_manager.get_current_index() >= len(self.queue_manager.get_queue()) - 2:
                            recommendations = self.service.get_song_recommendations(current_song["videoId"], 3)
                            self.queue_manager.append_radio_recommendations(current_song, recommendations)
                            for item in self.queue_manager.get_queue()[self.queue_manager.get_current_index() + 1:]:
                                if item.get("videoId"):
                                    self.player.preload_stream(item["videoId"])
                        return
                self.playlist_controller.handle_fetch_and_play_recommendation()
            else:
                s = self.queue_manager.next()
                if s:
                    self.music_controller.play_song(s)
                    self.music_controller.preload_next_songs(5)
                else:
                    self.window.update_song_info("Cola terminada")
                    self.window.update_play_button_icon(False)

    def on_queue_updated(self):
        self.window.update_queue(self.queue_manager.get_queue(), self.queue_manager.get_current_index())

    def handle_login(self, headers):
        if self.service.setup_authentication(headers):
            self.window.show_auth_success()
            self.playlists_cache = self.playlist_controller.get_combined_playlists()
            self.window.update_playlists(self.playlists_cache)
            self.window.update_auth_status(True)
        else:
            self.window.show_auth_error()
            self.window.update_auth_status(False)

    def handle_logout(self):
        if self.service.logout():
            self.playlists_cache = self.playlist_controller.get_combined_playlists()
            self.window.update_playlists(self.playlists_cache)
            self.window.update_auth_status(False)

    def handle_playlist_selected(self, index):
        self.playlist_controller.handle_playlist_selected(index)

    def handle_toggle_autoplay(self):
        self.queue_manager.toggle_autoplay()

    def handle_show_lyrics(self):
        self.music_controller.handle_show_lyrics()

    def on_time_ms_updated(self, current_ms):
        self.music_controller.on_time_ms_updated(current_ms)

    def get_combined_playlists(self):
        return self.playlist_controller.get_combined_playlists()

    def initial_load(self):
        self.playlists_cache = self.get_combined_playlists()
        self.window.update_playlists(self.playlists_cache)
        self.window.update_auth_status(self.service.is_authenticated)
        if os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                self.player.set_stream_cache(d.get("stream_cache", {}))
                self.queue_manager.set_queue_state(d.get("queue", []), d.get("current_index", -1))
                self.on_queue_updated()
                idx = self.queue_manager.get_current_index()
                if idx >= 0:
                    self.window.queue_list.setCurrentRow(idx)
                    s = self.queue_manager.get_current()
                    if s:
                        self.window.update_song_info(f"{s['title']} - {s['artists'][0]['name']}")
            except Exception:
                pass

    def handle_home(self):
        home_raw = self.service.get_home()
        parsed_sections = []

        for section in home_raw:
            title = section.get("title", "Sección")
            content = self.service.parse_home_section(section)
            if content:
                parsed_sections.append((title, content))

        self.window.show_home(parsed_sections)

    def on_stream_ready(self, video_id, title):
        self.music_controller.on_stream_ready(video_id, title)

    def on_stream_error(self, msg):
        self.music_controller.on_stream_error(msg)

    def handle_fetch_and_play_recommendation(self):
        self.playlist_controller.handle_fetch_and_play_recommendation()
