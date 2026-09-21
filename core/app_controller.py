import json
import os
import re

from PySide6.QtCore import QTimer

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
        if not (self.queue_manager and self.player):
            return
        try:
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
            log_path = os.path.join(self.base_dir, "state_error.log")
            try:
                with open(log_path, 'a', encoding='utf-8') as lf:
                    import traceback
                    lf.write(f"\n--- save_state_on_exit error ---\n{traceback.format_exc()}\n")
            except Exception:
                pass

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
            if song.get("playlistId"):
                self.playlist_controller.handle_playlist_selected_by_id(song['playlistId'])
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

        if recommendations:
            self.window.show_similar_songs(recommendations)

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
            return

        queue = self.queue_manager.get_queue()
        current_index = self.queue_manager.get_current_index()
        songs_remaining = len(queue) - current_index - 1

        # Auto-extend queue when ≤ 1 song remains after current
        if songs_remaining <= 1:
            self._extend_queue_async()

        next_song = self.queue_manager.next()
        if next_song:
            self.music_controller.play_song(next_song)
            self.music_controller.preload_next_songs(3)
        else:
            # Queue was empty — wait for _extend_queue_async to finish
            self.window.update_play_button_icon(False)

    def _extend_queue_async(self):
        """Fetch a recommendation based on the last song and append to queue."""
        import threading
        from PySide6.QtCore import QTimer

        queue = self.queue_manager.get_queue()
        seed = queue[-1] if queue else self.queue_manager.get_current()
        if not seed or not seed.get("videoId"):
            return

        def _worker():
            try:
                recs = self.service.get_song_recommendations(seed["videoId"], 2)
                if not recs:
                    return
                existing_ids = {s.get("videoId") for s in self.queue_manager.get_queue()}
                for rec in recs:
                    if rec.get("videoId") and rec["videoId"] not in existing_ids:
                        def _append(r=rec):
                            try:
                                self.queue_manager.add_song(r)
                                if not self.player.is_playing:
                                    s = self.queue_manager.next()
                                    if s:
                                        self.music_controller.play_song(s)
                            except RuntimeError:
                                pass
                        try:
                            QTimer.singleShot(0, _append)
                        except RuntimeError:
                            pass
                        break
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def on_queue_updated(self):
        self.window.update_queue(self.queue_manager.get_queue(), self.queue_manager.get_current_index())

    def handle_login(self):
        from ui.login_window import LoginWindow
        dlg = LoginWindow(self.service, self.window.app_icon, False)
        dlg.login_success.connect(lambda: self._on_login_success(dlg))
        dlg.login_skipped.connect(dlg.close)
        dlg.show()

    def _on_login_success(self, dlg=None):
        if dlg:
            try:
                dlg.close()
            except Exception:
                pass
        self.playlists_cache = self.playlist_controller.get_combined_playlists()
        self.window.update_playlists(self.playlists_cache)
        self.window.update_auth_status(True)
        self.window.show_auth_success()

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
                    s = self.queue_manager.get_current()
                    if s:
                        self.window.update_song_info(f"{s['title']} - {s['artists'][0]['name']}")
            except Exception:
                pass
        QTimer.singleShot(200, self.handle_home)

    def handle_home(self):
        home_raw = self.service.get_home()
        parsed_sections = []

        for section in home_raw:
            title = section.get("title", "Sección")
            content = self.service.parse_home_section(section)
            if content:
                parsed_sections.append((title, content))

        self.window.show_home(parsed_sections)

    def handle_home_item_selected(self, item):
        if item.get('videoId'):
            self.start_radio_from_song(item)
        elif item.get('playlistId'):
            self.playlist_controller.handle_playlist_selected_by_id(item['playlistId'])

    def handle_show_library(self):
        self.window.show_library_browser()
        self._load_library_playlists()

    def handle_library_chip_selected(self, chip):
        if chip == "Playlists":
            self._load_library_playlists()
        elif chip == "Canciones":
            self._load_library_songs()
        elif chip == "Artistas":
            self._load_library_artists()

    def handle_library_playlist_selected(self, playlist):
        pid = playlist.get('playlistId')
        src = playlist.get('source', 'ytmusic')
        if src in ('local', 'imported', 'user_created'):
            data = self.playlist_manager.get_playlist(pid)
        else:
            data = self.service.get_playlist_songs(pid)
        if data and 'tracks' in data:
            self.queue_manager.clear()
            for s in data['tracks']:
                self.queue_manager.add_song(s)
            self.music_controller.play_song(self.queue_manager.jump_to(0))
            self.music_controller.preload_next_songs(5)

    def handle_library_song_selected(self, song):
        if song.get('videoId'):
            self.start_radio_from_song(song)

    def handle_similar_filter(self, chip):
        current = self.queue_manager.get_current()
        if not current:
            return
        title = current.get('title', '')
        artists = current.get('artists', [{}])
        artist = artists[0].get('name', '') if artists else ''
        query_base = f"{title} {artist}".strip()

        if chip == "Canciones":
            songs = self.service.get_song_recommendations(current.get('videoId', ''), 12) or []
            self.window.show_similar_songs(songs)
        elif chip == "Mixes":
            raw = self.service.search(f"{query_base} mix", filter="playlists") or []
            items = [self._normalize_pl(r) for r in raw if self._pl_id(r)]
            self.window.show_similar_songs(items[:12])
        elif chip == "Playlists":
            raw = self.service.search(f"playlist {query_base}", filter="playlists") or []
            items = [self._normalize_pl(r) for r in raw if self._pl_id(r)]
            self.window.show_similar_songs(items[:12])

    def _load_library_playlists(self):
        playlists = self.playlist_controller.get_combined_playlists()
        self.window.library_browser.show_playlists(playlists, self.window.thumbnail_cache)

    def _load_library_songs(self):
        songs = self.service.get_library_songs()
        if not songs:
            songs = self._get_local_songs()
        self.window.library_browser.show_songs(songs, self.window.thumbnail_cache)

    def _load_library_artists(self):
        artists = self._get_local_artists()
        self.window.library_browser.show_artists(artists, self.window.thumbnail_cache)

    def _get_local_songs(self):
        seen = set()
        songs = []
        for p in self.playlist_manager.get_all_playlists():
            for t in p.get('tracks', []):
                vid = t.get('videoId')
                if vid and vid not in seen:
                    seen.add(vid)
                    songs.append(t)
        return songs

    def _get_local_artists(self):
        artist_map = {}
        for p in self.playlist_manager.get_all_playlists():
            for t in p.get('tracks', []):
                for a in t.get('artists', []):
                    name = a.get('name', '')
                    if name:
                        if name not in artist_map:
                            artist_map[name] = {
                                'name': name, 'count': 0,
                                'thumbnails': t.get('thumbnails', [])
                            }
                        artist_map[name]['count'] += 1
        return sorted(artist_map.values(), key=lambda x: -x['count'])

    def handle_mood_selected(self, mood):
        if mood == "Todos":
            self.handle_home()
            return

        sections = []

        # Songs section — compact grid
        songs_raw = self.service.search(f"{mood} canciones", filter="songs")
        songs = [
            {
                'type': 'song',
                'videoId': s.get('videoId', ''),
                'title': s.get('title', ''),
                'artists': s.get('artists', []),
                'thumbnails': s.get('thumbnails', []),
            }
            for s in (songs_raw or []) if s.get('videoId')
        ]
        if songs:
            sections.append((f"Canciones — {mood}", songs[:12]))

        # Mixes section — cards
        mixes_raw = self.service.search(f"{mood} mix", filter="playlists")
        mixes = [self._normalize_pl(r) for r in (mixes_raw or []) if self._pl_id(r)]
        if mixes:
            sections.append(("Mixes para ti", mixes[:10]))

        # Playlists section — cards
        playlists_raw = self.service.search(f"playlist {mood}", filter="playlists")
        playlists = [self._normalize_pl(r) for r in (playlists_raw or []) if self._pl_id(r)]
        if playlists:
            sections.append((f"Playlists • {mood}", playlists[:10]))

        self.window.show_home(sections)

    def _pl_id(self, r):
        pid = r.get('playlistId', '')
        if not pid:
            bid = r.get('browseId', '')
            pid = bid[2:] if bid.startswith('VL') else bid
        return pid

    def _normalize_pl(self, r):
        return {
            'type': 'playlist',
            'playlistId': self._pl_id(r),
            'title': r.get('title', ''),
            'thumbnails': r.get('thumbnails', []),
        }

    def on_stream_ready(self, video_id, title):
        self.music_controller.on_stream_ready(video_id, title)

    def on_stream_error(self, msg):
        self.music_controller.on_stream_error(msg)

    def handle_fetch_and_play_recommendation(self):
        self.playlist_controller.handle_fetch_and_play_recommendation()
