import os
import traceback


class PlaylistController:
    def __init__(self, app_controller):
        self.app = app_controller

    def handle_import_playlist(self, url):
        match = self.app.PLAYLIST_RE.search(url)
        if not match:
            self.app.window.show_import_error(
                "URL inválida. Formato esperado: https://music.youtube.com/playlist?list=PLxxxxxx"
            )
            return

        playlist_id = match.group(1)

        try:
            data = self.app.service.get_playlist_songs(playlist_id)

            if not data:
                self.app.window.show_import_error(
                    "No se pudo acceder a la playlist. Verifica:\n- La URL es correcta\n- La playlist no está privada\n- Tienes conexión a internet"
                )
                return

            if not data.get('tracks'):
                self.app.window.show_import_error("La playlist está vacía o no tiene canciones accesibles.")
                return

            self.app.results_cache = []
            self.app.window.update_results(self.app.results_cache)
            self.app.queue_manager.clear()

            for song in data['tracks']:
                self.app.queue_manager.add_song(song)

            first_song = self.app.queue_manager.jump_to(0)
            if first_song:
                self.app.music_controller.play_song(first_song)
                self.app.music_controller.preload_next_songs(5)

            self.app.window.search_box.clear()
            self.app.last_imported_playlist_data = data
            self.app.window.ask_to_save_playlist(data['title'], self.app.service.is_authenticated)

        except Exception as e:
            traceback.print_exc()
            self.app.window.show_import_error(f"Error al importar:\n{str(e)}")

    def handle_save_imported_playlist(self, save_to_ytmusic=False):
        if not self.app.last_imported_playlist_data:
            print("[SAVE] ️ No hay datos para guardar")
            return

        title = self.app.last_imported_playlist_data['title']
        songs = self.app.last_imported_playlist_data['tracks']

        try:
            if save_to_ytmusic and self.app.service.is_authenticated:
                result = self.app.service.create_playlist(title, "Importada desde YTMusic Client", songs)
                if result:
                    self.app.playlists_cache = self.get_combined_playlists()
                    self.app.window.update_playlists(self.app.playlists_cache)
                    self.app.window.show_save_playlist_success(title, "YouTube Music")
                else:
                    self.app.window.show_save_playlist_error(title)
            else:
                playlists_dir = os.path.dirname(self.app.playlist_manager.playlists_file)
                if not os.path.exists(playlists_dir):
                    os.makedirs(playlists_dir, exist_ok=True)

                result = self.app.playlist_manager.add_playlist(title, songs, "imported")
                if result:
                    self.app.playlists_cache = self.get_combined_playlists()
                    self.app.window.update_playlists(self.app.playlists_cache)
                    self.app.window.show_save_playlist_success(title, "local")
                else:
                    self.app.window.show_save_playlist_error(title)

            self.app.last_imported_playlist_data = None

        except Exception:
            traceback.print_exc()
            self.app.window.show_save_playlist_error(title)

    def save_queue_playlist(self, title, tracks):
        try:
            if not tracks:
                return

            local_ok = self.app.playlist_manager.add_playlist(title, tracks, "user_created")
            if self.app.service.is_authenticated:
                yt_ok = self.app.service.create_playlist(title, "Creada desde YTMusic Client", tracks)
                if local_ok or yt_ok:
                    self.app.playlists_cache = self.get_combined_playlists()
                    self.app.window.update_playlists(self.app.playlists_cache)
                    self.app.window.show_save_playlist_success(title, "local + YouTube Music")
                else:
                    self.app.window.show_save_playlist_error(title)
            else:
                if local_ok:
                    self.app.playlists_cache = self.get_combined_playlists()
                    self.app.window.update_playlists(self.app.playlists_cache)
                    self.app.window.show_save_playlist_success(title, "local")
                else:
                    self.app.window.show_save_playlist_error(title)
        except Exception:
            traceback.print_exc()
            self.app.window.show_save_playlist_error(title)

    def get_combined_playlists(self):
        local = self.app.playlist_manager.get_all_playlists()
        if self.app.service.is_authenticated:
            return self.app.playlist_manager.merge_with_ytmusic_playlists(self.app.service.get_library_playlists())
        result = []
        for p in local:
            tracks = p.get('tracks', [])
            thumbs = tracks[0].get('thumbnails', []) if tracks else []
            result.append({
                'playlistId': p['playlistId'],
                'title': p['title'],
                'source': p.get('source', 'local'),
                'track_count': p.get('track_count', len(tracks)),
                'thumbnails': thumbs,
            })
        return result

    def handle_playlist_selected(self, index):
        if 0 <= index < len(self.app.playlists_cache):
            p = self.app.playlists_cache[index]
            pid = p.get('playlistId')
            src = p.get('source', 'ytmusic')
            if src in ['local', 'imported', 'user_created']:
                data = self.app.playlist_manager.get_playlist(pid)
            else:
                data = self.app.service.get_playlist_songs(pid)

            if data and 'tracks' in data:
                self.app.results_cache = []
                self.app.window.update_results([])
                self.app.queue_manager.clear()
                for s in data['tracks']:
                    self.app.queue_manager.add_song(s)
                self.app.music_controller.play_song(self.app.queue_manager.jump_to(0))
                self.app.music_controller.preload_next_songs(5)
            else:
                print("Error playlist")

    def handle_playlist_selected_by_id(self, playlist_id):
        data = self.app.service.get_playlist_songs(playlist_id)
        if data and data.get('tracks'):
            self.app.queue_manager.clear()
            for s in data['tracks']:
                self.app.queue_manager.add_song(s)
            self.app.music_controller.play_song(self.app.queue_manager.jump_to(0))
            self.app.music_controller.preload_next_songs(5)

    def handle_fetch_and_play_recommendation(self):
        s = self.app.queue_manager.get_current()
        if not s:
            return
        recs = self.app.service.get_song_recommendations(s['videoId'], 10)
        if not recs:
            return
        q_ids = {x.get('videoId') for x in self.app.queue_manager.get_queue()}
        new_recs = [x for x in recs if x.get('videoId') not in q_ids]
        rec = new_recs[0] if new_recs else recs[0]
        if self.app.queue_manager.add_song(rec):
            self.app.music_controller.play_song(rec)
            self.app.music_controller.preload_next_songs(5)
        else:
            self.app.music_controller.play_song(self.app.queue_manager.next())
            self.app.music_controller.preload_next_songs(5)
