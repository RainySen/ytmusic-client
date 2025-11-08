from ytmusicapi import YTMusic
import os
import traceback
import json

AUTH_FILE = "oauth.json"


class YTMusicService:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.AUTH_FILE = os.path.join(self.base_dir, "oauth.json")
        self.CACHE_DIR = os.path.join(self.base_dir, ".yt-dlp-cache")

        # Crear directorio de caché para yt-dlp si no existe
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        # Crear directorio de caché para yt-dlp si no existe

        if os.path.exists(self.AUTH_FILE):
            try:
                self.ytmusic = YTMusic(self.AUTH_FILE)
                self.is_authenticated = True
            except Exception:
                self.ytmusic = YTMusic()
                self.is_authenticated = False
        else:
            self.ytmusic = YTMusic()
            self.is_authenticated = False

    def setup_authentication(self, headers_raw):
        try:
            if not headers_raw or not headers_raw.strip():
                print("Error: Las cabeceras extraídas están vacías.")
                return False
            auth_headers = {}
            for line in headers_raw.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    auth_headers[key.strip()] = value.strip()
            if 'Cookie' not in auth_headers and 'cookie' not in auth_headers:
                print("Error: No se encontró la 'Cookie' en las cabeceras.")
                return False
            self.ytmusic = YTMusic(auth=auth_headers)
            self.ytmusic.get_library_playlists(limit=1)
            with open(self.AUTH_FILE, 'w') as f:
                json.dump(auth_headers, f, indent=4)
            self.is_authenticated = True
            return True
        except Exception:
            print("Error durante la autenticación:")
            traceback.print_exc()
            if os.path.exists(self.AUTH_FILE):
                os.remove(self.AUTH_FILE)
            self.is_authenticated = False
            return False

    def logout(self):
        """Cierra la sesión eliminando el archivo de autenticación."""
        try:
            if os.path.exists(self.AUTH_FILE):
                os.remove(self.AUTH_FILE)
            self.is_authenticated = False
            self.ytmusic = YTMusic() # Reinicializa la API sin autenticación
            print("[AUTH] Sesión cerrada.")
            return True
        except Exception as e:
            print(f"[AUTH] Error al cerrar sesión: {e}")
            return False

    def get_library_playlists(self):
        if not self.is_authenticated:
            return []
        try:
            return self.ytmusic.get_library_playlists(limit=50)
        except Exception as e:
            print(f"Error obteniendo playlists: {e}")
            return []

    def get_playlist_songs(self, playlist_id):
        try:
            print("\n" + "=" * 20 + " INICIO DEPURACIÓN DE PLAYLIST " + "=" * 20)
            print(f"[DEBUG] Solicitando canciones para la playlist con ID: {playlist_id}")

            playlist_data = self.ytmusic.get_playlist(playlist_id, limit=None)

            if 'tracks' in playlist_data and playlist_data['tracks']:
                print(f"[DEBUG] Se encontraron {len(playlist_data['tracks'])} canciones en la respuesta.")
            else:
                print("[DEBUG] ¡ALERTA! La respuesta de la API no contiene la clave 'tracks' o está vacía.")

            print("=" * 22 + " FIN DEPURACIÓN DE PLAYLIST " + "=" * 23 + "\n")

            return {
                'title': playlist_data.get('title', 'Playlist Importada'),
                'tracks': self.normalize_playlist_tracks(playlist_data.get('tracks', []))
            }

        except Exception as e:
            print(f"Error obteniendo canciones de la playlist: {e}")
            traceback.print_exc()
            return None

    def normalize_playlist_tracks(self, tracks):
        normalized_songs = []
        for track in tracks:
            if not track or not track.get('videoId'):
                continue
            normalized_songs.append({
                'videoId': track['videoId'],
                'title': track.get('title', 'Título Desconocido'),
                'artists': track.get('artists', [{'name': 'Desconocido'}])
            })
        return normalized_songs

    def search(self, query):
        return self.ytmusic.search(query, filter="songs", limit=30)

    def get_stream_url(self, video_id):
        return f"https://music.youtube.com/watch?v={video_id}"

    def get_song_stream_info(self, video_id):
        import yt_dlp

        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'socket_timeout': 8,
                'retries': 1,
                'fragment_retries': 1,
                'file_access_retries': 1,
                'extractor_retries': 1,
                'cachedir': self.CACHE_DIR,
                'nocheckcertificate': True,
                'youtube_include_dash_manifest': False,
                'youtube_include_hls_manifest': False,
            }

            url = f"https://music.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                title = info.get('title', 'Título Desconocido')

                if stream_url:
                    print(f"[YT-DLP OPTIMIZADO] ✓ Stream obtenido: {title}")
                    return stream_url, title
                else:
                    print(f"[ERROR] No se encontró URL de stream para {video_id}")
                    return None

        except Exception as e:
            print(f"[ERROR] Error obteniendo stream para {video_id}: {e}")
            traceback.print_exc()
            return None

    def create_playlist(self, title, description, song_list):
        if not self.is_authenticated:
            print("Intento de crear playlist sin autenticación.")
            return None
        try:
            video_ids = [song['videoId'] for song in song_list if 'videoId' in song]

            playlist_id = self.ytmusic.create_playlist(
                title=title,
                description=description,
                privacy_status="PRIVATE",
                video_ids=video_ids
            )
            return playlist_id
        except Exception as e:
            print(f"Error al crear la playlist en la biblioteca: {e}")
            traceback.print_exc()
            return None