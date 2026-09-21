import json
import os
from datetime import datetime


class PlaylistManager:

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.playlists_file = os.path.join(base_dir, "local_playlists.json")
        self.playlists = self._load_playlists()

    def _load_playlists(self):
        if os.path.exists(self.playlists_file):
            try:
                with open(self.playlists_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"[PLAYLISTS] Cargadas {len(data)} playlists locales")
                    return data
            except Exception as e:
                print(f"[PLAYLISTS] Error cargando playlists: {e}")
                return []
        return []

    def _save_playlists(self):
        try:
            with open(self.playlists_file, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=2, ensure_ascii=False)
            print(f"[PLAYLISTS] Guardadas {len(self.playlists)} playlists")
            return True
        except Exception as e:
            print(f"[PLAYLISTS] Error guardando playlists: {e}")
            return False

    def add_playlist(self, title, tracks, source="imported"):
        """
        Args:
            title: Título de la playlist
            tracks: Lista de canciones (formato normalizado con videoId, title, artists)
            source: Origen de la playlist ("imported", "user_created", "ytmusic")

        Returns:
            El ID de la playlist creada o None si falla
        """
        try:
            # Generar un ID único basado en timestamp
            playlist_id = f"local_{int(datetime.now().timestamp() * 1000)}"

            playlist = {
                'playlistId': playlist_id,
                'title': title,
                'source': source,
                'tracks': tracks,
                'created_at': datetime.now().isoformat(),
                'track_count': len(tracks)
            }

            self.playlists.append(playlist)

            if self._save_playlists():
                print(f"[PLAYLISTS] Playlist '{title}' guardada con ID: {playlist_id}")
                return playlist_id
            else:
                # Si falla el guardado, eliminar de memoria
                self.playlists.pop()
                return None

        except Exception as e:
            print(f"[PLAYLISTS] Error añadiendo playlist: {e}")
            return None

    def get_all_playlists(self):
        """Retorna todas las playlists locales"""
        return self.playlists

    def get_playlist(self, playlist_id):
        """Obtiene una playlist específica por ID"""
        for playlist in self.playlists:
            if playlist.get('playlistId') == playlist_id:
                return playlist
        return None

    def delete_playlist(self, playlist_id):
        """Elimina una playlist local"""
        try:
            initial_count = len(self.playlists)
            self.playlists = [p for p in self.playlists if p.get('playlistId') != playlist_id]

            if len(self.playlists) < initial_count:
                self._save_playlists()
                print(f"[PLAYLISTS] Playlist {playlist_id} eliminada")
                return True
            return False
        except Exception as e:
            print(f"[PLAYLISTS] Error eliminando playlist: {e}")
            return False

    def update_playlist_title(self, playlist_id, new_title):
        """Actualiza el título de una playlist"""
        playlist = self.get_playlist(playlist_id)
        if playlist:
            playlist['title'] = new_title
            return self._save_playlists()
        return False

    def merge_with_ytmusic_playlists(self, ytmusic_playlists):
        """
        Combina playlists locales con las de YouTube Music.
        Las playlists de YTMusic se marcan con source='ytmusic'.

        Args:
            ytmusic_playlists: Lista de playlists de YouTube Music

        Returns:
            Lista combinada de playlists
        """
        combined = []

        for playlist in self.playlists:
            tracks = playlist.get('tracks', [])
            # Use first track's thumbnail as playlist cover for local playlists
            thumbs = tracks[0].get('thumbnails', []) if tracks else []
            combined.append({
                'playlistId': playlist['playlistId'],
                'title': playlist['title'],
                'source': playlist.get('source', 'local'),
                'track_count': playlist.get('track_count', len(tracks)),
                'thumbnails': thumbs,
            })

        for playlist in ytmusic_playlists:
            combined.append({
                'playlistId': playlist.get('playlistId'),
                'title': playlist.get('title'),
                'source': 'ytmusic',
                'track_count': playlist.get('count', 0),
                'thumbnails': playlist.get('thumbnails', []),
            })

        return combined