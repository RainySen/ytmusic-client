from ytmusicapi import YTMusic
import os
import traceback
import json
import re
import hashlib
import time
from datetime import datetime


class YTMusicService:

    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.AUTH_FILE = os.path.join(self.base_dir, "oauth.json")

        from platform_utils import get_cache_dir
        self.CACHE_DIR = os.path.join(get_cache_dir(), "yt-dlp")

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        self._initialize_auth()

    def _make_sapisidhash(self, cookie):
        sapisid_match = re.search(r'SAPISID=([^;]+)', cookie)
        if not sapisid_match:
            return None
        sapisid = sapisid_match.group(1).strip()
        origin = "https://music.youtube.com"
        ts = str(int(time.time()))
        digest = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
        return f"SAPISIDHASH {ts}_{digest}"

    def _build_auth_headers(self, raw_headers):
        auth_headers = {}
        for match in re.finditer(r"-H\s+'([^:]+?):\s*(.*?)'", raw_headers, re.DOTALL):
            auth_headers[match.group(1).strip()] = match.group(2).strip()
        if not auth_headers:
            for match in re.finditer(r'-H\s+"([^:]+?):\s*(.*?)"', raw_headers, re.DOTALL):
                auth_headers[match.group(1).strip()] = match.group(2).strip()

        # Remove Accept-Encoding to avoid decompression issues
        auth_headers.pop('Accept-Encoding', None)
        auth_headers.pop('accept-encoding', None)

        cookie = auth_headers.get('Cookie') or auth_headers.get('cookie', '')
        sapisidhash = self._make_sapisidhash(cookie)
        if sapisidhash:
            auth_headers['Authorization'] = sapisidhash

        return auth_headers

    def _initialize_auth(self):
        if os.path.exists(self.AUTH_FILE):
            try:
                print("[AUTH] Cargando sesion guardada...")
                with open(self.AUTH_FILE, "r") as f:
                    auth_headers = json.load(f)

                cookie = auth_headers.get("Cookie") or auth_headers.get("cookie", "")
                sapisidhash = self._make_sapisidhash(cookie)
                if not sapisidhash:
                    raise Exception("SAPISID no encontrada")

                # Remove Accept-Encoding if present
                auth_headers.pop('Accept-Encoding', None)
                auth_headers.pop('accept-encoding', None)
                auth_headers["Authorization"] = sapisidhash

                self.ytmusic = YTMusic(auth=auth_headers)

                # Test authentication — two-step validation.
                # Step 1: library playlists (fast, but can return [] for expired cookies)
                print("[AUTH] Probando conexion...")
                playlists = self.ytmusic.get_library_playlists(limit=1)

                # Step 2: if library is empty, verify with get_home().
                # An authenticated user ALWAYS gets a non-empty home feed.
                # An expired/invalid session returns [] from home too.
                if not playlists:
                    print("[AUTH] Biblioteca vacia, verificando con home feed...")
                    home_check = self.ytmusic.get_home(limit=3)
                    if not home_check:
                        raise Exception(
                            "Sesion expirada: biblioteca y home vacios. "
                            "Las cookies del navegador han expirado."
                        )

                self.is_authenticated = True
                print(f"[AUTH] OK - Sesion restaurada ({len(playlists)} playlists detectadas)")
                return

            except Exception as e:
                print(f"[AUTH] Fallo al restaurar sesion: {e}")
                traceback.print_exc()
                try:
                    os.remove(self.AUTH_FILE)
                except:
                    pass

        print("[AUTH] Sin autenticacion - modo invitado")
        self.ytmusic = YTMusic()
        self.is_authenticated = False

    def setup_authentication(self, headers_raw):
        try:
            if not headers_raw or not headers_raw.strip():
                print("[AUTH] Error: cURL vacio")
                return False

            auth_headers = self._build_auth_headers(headers_raw)

            cookie = auth_headers.get('Cookie') or auth_headers.get('cookie', '')
            if not cookie:
                print("[AUTH] Error: Cookie no encontrada")
                return False

            print(f"[AUTH] Headers extraidas: {list(auth_headers.keys())}")
            print("[AUTH] Autenticando con YouTube...")

            self.ytmusic = YTMusic(auth=auth_headers)
            result = self.ytmusic.get_library_playlists(limit=1)

            if not isinstance(result, list):
                raise Exception(f"Respuesta invalida: {type(result)}")

            # Save headers without Authorization (regenerated on startup)
            to_save = {k: v for k, v in auth_headers.items()
                       if k.lower() not in ("authorization", "accept-encoding")}
            with open(self.AUTH_FILE, 'w') as f:
                json.dump(to_save, f, indent=4)

            self.is_authenticated = True
            self._save_auth_timestamp()
            print(f"[AUTH] OK - Autenticado exitosamente ({len(result)} playlists)")
            return True

        except Exception as e:
            print(f"[AUTH] Error durante autenticacion: {e}")
            traceback.print_exc()
            if os.path.exists(self.AUTH_FILE):
                os.remove(self.AUTH_FILE)
            self.is_authenticated = False
            return False

    def _save_auth_timestamp(self):
        try:
            with open(os.path.join(self.base_dir, "auth_timestamp.json"), 'w') as f:
                json.dump({'authenticated_at': datetime.now().isoformat()}, f)
        except:
            pass

    def get_auth_status(self):
        if not self.is_authenticated:
            return {'authenticated': False, 'message': 'No autenticado'}
        try:
            with open(os.path.join(self.base_dir, "auth_timestamp.json")) as f:
                data = json.load(f)
                days = (datetime.now() - datetime.fromisoformat(data['authenticated_at'])).days
                return {'authenticated': True, 'days_since_auth': days, 'message': f'Activo ({days} dias)'}
        except:
            return {'authenticated': True, 'message': 'Autenticado'}

    def logout(self):
        try:
            files_to_remove = [
                self.AUTH_FILE,
                os.path.join(self.base_dir, "auth_timestamp.json")
            ]
            for f in files_to_remove:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"[AUTH] Eliminado: {f}")

            self.is_authenticated = False
            self.ytmusic = YTMusic()
            print("[AUTH] Sesion cerrada")
            return True
        except Exception as e:
            print(f"[AUTH] Error al cerrar sesion: {e}")
            return False

    def get_library_playlists(self):
        if not self.is_authenticated:
            print("[PLAYLISTS] No autenticado - retornando lista vacia")
            return []
        try:
            print("[PLAYLISTS] Obteniendo playlists de YTMusic...")
            playlists = self.ytmusic.get_library_playlists(limit=50)
            print(f"[PLAYLISTS] OK - {len(playlists)} playlists obtenidas")
            return playlists
        except Exception as e:
            print(f"[PLAYLISTS] Error: {e}")
            traceback.print_exc()
            return []

    def get_playlist_songs(self, playlist_id):
        try:
            data = self.ytmusic.get_playlist(playlist_id, limit=None)
            return {'title': data.get('title', 'Playlist'),
                    'tracks': self.normalize_playlist_tracks(data.get('tracks', []))}
        except Exception as e:
            print(f"[PLAYLIST] Error: {e}")
            traceback.print_exc()
            return None

    def normalize_playlist_tracks(self, tracks):
        return [{'videoId': t['videoId'], 'title': t.get('title', ''),
                 'artists': t.get('artists', [{'name': ''}])}
                for t in tracks if t and t.get('videoId')]

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
            with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': True,
                                   'no_warnings': True, 'skip_download': True,
                                   'cachedir': self.CACHE_DIR}) as ydl:
                info = ydl.extract_info(f"https://music.youtube.com/watch?v={video_id}", download=False)
                return info.get('url'), info.get('title', '')
        except:
            traceback.print_exc()
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
            return [{'videoId': t['videoId'], 'title': t.get('title', ''),
                     'artists': t.get('artists', [{'name': ''}])}
                    for t in watch.get('tracks', [])
                    if t.get('videoId') and t.get('videoId') != video_id]
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
        if not self.is_authenticated:
            print("[HOME] Modo invitado - Obteniendo éxitos globales...")
            try:
                charts = self.ytmusic.get_charts(country='ZZ')
                print(f"[HOME] Charts keys: {list(charts.keys())}")

                sections = []

                def _extract_items(raw):
                    """Normaliza items de charts al formato de sección estándar."""
                    if isinstance(raw, dict):
                        return raw.get('items', [])
                    if isinstance(raw, list):
                        return raw
                    return []

                for key, label in [
                    ('videos',   'Vídeos en Tendencia'),
                    ('trending', 'Tendencias'),
                    ('songs',    'Canciones Populares'),
                ]:
                    if key in charts:
                        extracted = _extract_items(charts[key])
                        if extracted:
                            sections.append({'title': label, 'contents': extracted})
                            print(f"[HOME] Sección '{label}': {len(extracted)} items")

                return sections

            except Exception as e:
                print(f"[HOME] Error en modo invitado: {e}")
                traceback.print_exc()
                return []

        try:
            print("[HOME] Obteniendo feed de YTMusic...")
            home = self.ytmusic.get_home(limit=20)

            # If authenticated but home returned empty, session likely expired silently
            if not home:
                print("[HOME] ADVERTENCIA: home vacio con sesion activa - sesion posiblemente expirada")
                self.is_authenticated = False
                return []

            print(f"[HOME] OK - {len(home)} secciones obtenidas")
            return home
        except Exception as e:
            print(f"[HOME] Error: {e}")
            traceback.print_exc()
            # Mark as unauthenticated if the request fails
            self.is_authenticated = False
            return []

    def parse_home_section(self, section):
        items = []
        contents = section.get("contents", [])
        print(f"[HOME] Parseando sección '{section.get('title', '?')}' con {len(contents)} items")

        for item in contents:
            if not item or not isinstance(item, dict):
                continue

            title = item.get("title", "") or ""

            # Songs / videos
            if "videoId" in item and item["videoId"]:
                artists = item.get("artists") or item.get("author") or []
                if isinstance(artists, str):
                    artists = [{"name": artists}]
                items.append({
                    "type": "song",
                    "videoId": item["videoId"],
                    "title": title,
                    "artists": artists,
                    "thumbnails": item.get("thumbnails", []),
                })

            # Playlists / mixes / radios
            elif "playlistId" in item and item["playlistId"]:
                items.append({
                    "type": "playlist",
                    "playlistId": item["playlistId"],
                    "title": title,
                    "thumbnails": item.get("thumbnails", []),
                })

            # Albums / artists via browseId
            elif "browseId" in item and item["browseId"]:
                # Distinguish artist vs album by browseId prefix
                browse_id = item["browseId"]
                item_type = "artist" if browse_id.startswith("UC") else "album"
                items.append({
                    "type": item_type,
                    "browseId": browse_id,
                    "title": title,
                    "thumbnails": item.get("thumbnails", []),
                })

            # Fallback: keep items that at least have a title so sections aren't empty
            elif title:
                print(f"[HOME]   Item sin ID conocido: '{title}' keys={list(item.keys())}")
                items.append({
                    "type": "unknown",
                    "title": title,
                    "thumbnails": item.get("thumbnails", []),
                })

        print(f"[HOME]   → {len(items)} items parseados")
        return items