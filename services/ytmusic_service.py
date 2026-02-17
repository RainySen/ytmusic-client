from ytmusicapi import YTMusic
import os
import traceback
import json
import re
import hashlib
import time
from datetime import datetime, timedelta


class YTMusicService:
    """Servicio YTMusic - Versión que REALMENTE funciona"""

    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.AUTH_FILE = os.path.join(self.base_dir, "oauth.json")

        from platform_utils import get_cache_dir
        self.CACHE_DIR = os.path.join(get_cache_dir(), "yt-dlp")

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        self._initialize_auth()

    def _initialize_auth(self):
        """Inicializar autenticación"""
        if os.path.exists(self.AUTH_FILE):
            try:
                print(f"[AUTH] 🔑 Cargando oauth.json")
                self.ytmusic = YTMusic(self.AUTH_FILE)
                self.ytmusic.get_library_playlists(limit=1)
                self.is_authenticated = True
                print(f"[AUTH] ✅ Sesión activa")
                return
            except Exception as e:
                print(f"[AUTH] ⚠️ OAuth expiró: {e}")
                try:
                    os.remove(self.AUTH_FILE)
                except:
                    pass

        print(f"[AUTH] 🔓 Sin autenticación")
        self.ytmusic = YTMusic()
        self.is_authenticated = False

    def setup_authentication(self, headers_raw):
        try:
            if not headers_raw or not headers_raw.strip():
                return False

            print("[AUTH] 🔧 Extrayendo cookies del cURL...")

            # Extraer cookie del cURL
            cookie_match = re.search(r"-H\s+['\"]Cookie:\s*([^'\"]+)['\"]", headers_raw)
            if not cookie_match:
                print("[AUTH] ❌ No se encontró Cookie en el cURL")
                return False

            cookie_string = cookie_match.group(1)

            # Parsear cookies individuales
            cookies = {}
            for part in cookie_string.split(';'):
                part = part.strip()
                if '=' in part:
                    key, value = part.split('=', 1)
                    cookies[key.strip()] = value.strip()

            # Verificar cookies críticas
            if 'SAPISID' not in cookies:
                print("[AUTH] ❌ Falta cookie SAPISID")
                return False

            print(f"[AUTH] ✅ Cookies extraídas: {len(cookies)} cookies")

            # Generar SAPISIDHASH (esto es lo que hace ytmusicapi internamente)
            sapisid = cookies['SAPISID']
            origin = "https://music.youtube.com"
            timestamp = str(int(time.time()))

            # Algoritmo SAPISIDHASH
            hash_input = f"{timestamp} {sapisid} {origin}"
            sapisidhash = hashlib.sha1(hash_input.encode()).hexdigest()
            auth_header = f"SAPISIDHASH {timestamp}_{sapisidhash}"

            print("[AUTH] 🔑 SAPISIDHASH generado")

            # Construir headers para ytmusicapi
            auth_data = {
                'Cookie': cookie_string,
                'Authorization': auth_header,
                'X-Goog-AuthUser': '0',
                'x-origin': origin
            }

            # Crear instancia de YTMusic con las headers
            print("[AUTH] 📡 Probando autenticación...")
            self.ytmusic = YTMusic(auth=auth_data)

            # Probar con una petición
            test_result = self.ytmusic.get_library_playlists(limit=1)

            if not isinstance(test_result, list):
                raise Exception("Respuesta inválida")

            print(f"[AUTH] ✅ ¡Funciona! {len(test_result)} playlists")

            # Guardar el auth_data como oauth.json
            with open(self.AUTH_FILE, 'w') as f:
                json.dump(self.ytmusic.auth, f, indent=2)

            print(f"[AUTH] 💾 Guardado en oauth.json")

            self.is_authenticated = True
            self._save_auth_timestamp()

            print(f"[AUTH] 🎉 ¡Listo! Durará semanas")
            return True

        except json.JSONDecodeError:
            print(f"[AUTH] ❌ Las cookies YA EXPIRARON")
            print(f"[AUTH]")
            print(f"[AUTH] Debes ser MÁS RÁPIDO:")
            print(f"[AUTH] 1. Deja esta ventana abierta")
            print(f"[AUTH] 2. Firefox → Biblioteca → Copia cURL")
            print(f"[AUTH] 3. ALT+TAB aquí → Pega → OK")
            print(f"[AUTH] 4. TODO en < 10 segundos")
            return False

        except Exception as e:
            print(f"[AUTH] ❌ Error: {e}")
            traceback.print_exc()
            return False

    def _save_auth_timestamp(self):
        try:
            with open(os.path.join(self.base_dir, "auth_timestamp.json"), 'w') as f:
                json.dump({
                    'authenticated_at': datetime.now().isoformat()
                }, f)
        except:
            pass

    def get_auth_status(self):
        if not self.is_authenticated:
            return {'authenticated': False, 'message': 'No autenticado'}

        try:
            with open(os.path.join(self.base_dir, "auth_timestamp.json")) as f:
                data = json.load(f)
                auth_time = datetime.fromisoformat(data['authenticated_at'])
                days = (datetime.now() - auth_time).days
                return {
                    'authenticated': True,
                    'days_since_auth': days,
                    'message': f'Activo ({days} días)'
                }
        except:
            return {'authenticated': True, 'message': 'Autenticado'}

    def logout(self):
        try:
            if os.path.exists(self.AUTH_FILE):
                os.remove(self.AUTH_FILE)
            self.is_authenticated = False
            self.ytmusic = YTMusic()
            return True
        except:
            return False

    # API methods (sin cambios)

    def get_library_playlists(self):
        if not self.is_authenticated:
            return []
        try:
            return self.ytmusic.get_library_playlists(limit=50)
        except:
            return []

    def get_playlist_songs(self, playlist_id):
        try:
            data = self.ytmusic.get_playlist(playlist_id, limit=None)
            return {
                'title': data.get('title', 'Playlist'),
                'tracks': self.normalize_playlist_tracks(data.get('tracks', []))
            }
        except:
            return None

    def normalize_playlist_tracks(self, tracks):
        result = []
        for t in tracks:
            if t and t.get('videoId'):
                result.append({
                    'videoId': t['videoId'],
                    'title': t.get('title', 'Desconocido'),
                    'artists': t.get('artists', [{'name': 'Desconocido'}])
                })
        return result

    def search(self, query):
        try:
            return self.ytmusic.search(query, filter="songs", limit=30)
        except:
            return []

    def get_stream_url(self, video_id):
        return f"https://music.youtube.com/watch?v={video_id}"

    def get_song_stream_info(self, video_id):
        import yt_dlp
        try:
            opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'cachedir': self.CACHE_DIR,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"https://music.youtube.com/watch?v={video_id}", download=False)
                return info.get('url'), info.get('title', 'Desconocido')
        except:
            return None

    def create_playlist(self, title, description, song_list):
        if not self.is_authenticated:
            return None
        try:
            ids = [s['videoId'] for s in song_list if 'videoId' in s]
            return self.ytmusic.create_playlist(title, description, "PRIVATE", ids)
        except:
            return None

    def get_song_recommendations(self, video_id, limit=5):
        try:
            watch = self.ytmusic.get_watch_playlist(videoId=video_id, limit=limit)
            recs = []
            for t in watch.get('tracks', []):
                if t.get('videoId') != video_id and t.get('videoId'):
                    recs.append({
                        'videoId': t['videoId'],
                        'title': t.get('title', 'Desconocido'),
                        'artists': t.get('artists', [{'name': 'Desconocido'}])
                    })
            return recs
        except:
            return []

    def get_song_lyrics(self, video_id):
        try:
            watch = self.ytmusic.get_watch_playlist(videoId=video_id)
            lid = watch.get('lyrics')
            return self.ytmusic.get_lyrics(browseId=lid) if lid else None
        except:
            return None

    def get_home(self):
        try:
            return self.ytmusic.get_home(limit=20)
        except:
            return []

    def parse_home_section(self, section):
        items = []
        for item in section.get("contents", []):
            if "videoId" in item:
                items.append({"type": "song", "videoId": item.get("videoId"),
                              "title": item.get("title", ""), "artists": item.get("artists", [])})
            elif "playlistId" in item:
                items.append({"type": "playlist", "playlistId": item.get("playlistId"),
                              "title": item.get("title", "")})
            elif "browseId" in item:
                items.append({"type": "album", "browseId": item.get("browseId"),
                              "title": item.get("title", "")})
        return items