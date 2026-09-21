from ytmusicapi import YTMusic
import os
import traceback
import json
import time
from hashlib import sha1

AUTH_FILE = "oauth.json"

_YTM_DOMAIN = "https://music.youtube.com"
_BROWSERS = ["firefox", "chrome", "edge", "brave", "chromium", "opera", "vivaldi", "whale"]


class YTMusicService:
    def __init__(self, base_dir="."):
        self.base_dir = base_dir
        self.AUTH_FILE = os.path.join(self.base_dir, "oauth.json")
        self.CACHE_DIR = os.path.join(self.base_dir, ".yt-dlp-cache")

        os.makedirs(self.CACHE_DIR, exist_ok=True)

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

    # ── Browser-cookie login ───────────────────────────────────────

    @staticmethod
    def detect_available_browsers() -> list[str]:
        """Return browsers that have a valid YouTube session (no crash, SAPISID present)."""
        import yt_dlp as _ydlp
        import io, sys
        available = []
        for browser in _BROWSERS:
            try:
                # Suppress yt-dlp's stderr noise for browsers that fail
                devnull = open(os.devnull, "w")
                ydl = _ydlp.YoutubeDL({
                    "quiet": True, "no_warnings": True,
                    "cookiesfrombrowser": (browser,),
                    "logger": type("_L", (), {
                        "debug": lambda s, m: None,
                        "warning": lambda s, m: None,
                        "error": lambda s, m: None,
                    })(),
                })
                jar = ydl.cookiejar
                cookies = {c.name: c.value for c in jar
                           if "youtube" in (c.domain or "") or "google" in (c.domain or "")}
                if cookies.get("SAPISID") or cookies.get("__Secure-3PAPISID"):
                    available.append(browser)
            except Exception:
                pass
        return available

    def login_from_browser(self, browser: str) -> tuple[bool, str]:
        """Authenticate using cookies extracted from the given browser. Returns (ok, error_msg)."""
        try:
            import yt_dlp as _ydlp
            ydl = _ydlp.YoutubeDL({"quiet": True, "no_warnings": True, "cookiesfrombrowser": (browser,)})
            jar = ydl.cookiejar

            cookies = {c.name: c.value for c in jar
                       if "youtube" in (c.domain or "") or "google" in (c.domain or "")}

            sapisid = cookies.get("__Secure-3PAPISID") or cookies.get("SAPISID", "")
            if not sapisid:
                return False, f"No se encontró sesión de YouTube en {browser}."

            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            ts = str(int(time.time()))
            h = sha1()
            h.update(f"{ts} {sapisid} {_YTM_DOMAIN}".encode())
            auth_header = f"SAPISIDHASH {ts}_{h.hexdigest()}"

            headers = {
                "cookie": cookie_str,
                "x-goog-authuser": "0",
                "authorization": auth_header,
                "user-agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
                ),
                "accept": "*/*",
                "accept-encoding": "gzip, deflate",
                "content-type": "application/json",
                "content-encoding": "gzip",
                "origin": _YTM_DOMAIN,
            }

            self.ytmusic = YTMusic(auth=headers)
            self.ytmusic.get_library_playlists(limit=1)
            with open(self.AUTH_FILE, "w", encoding="utf-8") as f:
                json.dump(headers, f, indent=4)
            self.is_authenticated = True
            return True, ""
        except Exception as e:
            self.is_authenticated = False
            return False, str(e)

    def setup_authentication(self, headers_raw):
        try:
            if not headers_raw or not headers_raw.strip():
                return False
            auth_headers = {}
            for line in headers_raw.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    auth_headers[key.strip()] = value.strip()
            if 'Cookie' not in auth_headers and 'cookie' not in auth_headers:
                return False
            self.ytmusic = YTMusic(auth=auth_headers)
            self.ytmusic.get_library_playlists(limit=1)
            with open(self.AUTH_FILE, 'w') as f:
                json.dump(auth_headers, f, indent=4)
            self.is_authenticated = True
            return True
        except Exception:
            traceback.print_exc()
            if os.path.exists(self.AUTH_FILE):
                os.remove(self.AUTH_FILE)
            self.is_authenticated = False
            return False

    def logout(self):
        try:
            if os.path.exists(self.AUTH_FILE):
                os.remove(self.AUTH_FILE)
            self.is_authenticated = False
            self.ytmusic = YTMusic()
            return True
        except Exception:
            return False

    def get_library_playlists(self):
        if not self.is_authenticated:
            return []
        try:
            return self.ytmusic.get_library_playlists(limit=50)
        except Exception:
            return []

    def get_playlist_songs(self, playlist_id):
        try:
            playlist_data = self.ytmusic.get_playlist(playlist_id, limit=None)
            return {
                'title': playlist_data.get('title', 'Playlist Importada'),
                'tracks': self.normalize_playlist_tracks(playlist_data.get('tracks', []))
            }
        except Exception:
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
                'artists': track.get('artists', [{'name': 'Desconocido'}]),
                'thumbnails': track.get('thumbnails', []),
            })
        return normalized_songs

    def search(self, query, filter="songs"):
        return self.ytmusic.search(query, filter=filter, limit=30)

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
                'socket_timeout': 15,
                'retries': 1,
                'fragment_retries': 1,
                'file_access_retries': 1,
                'extractor_retries': 1,
                'cachedir': self.CACHE_DIR,
                'nocheckcertificate': True,
                'youtube_include_dash_manifest': False,
                'youtube_include_hls_manifest': False,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            }
            url = f"https://music.youtube.com/watch?v={video_id}"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                title = info.get('title', 'Título Desconocido')
                if stream_url:
                    return stream_url, title
                return None
        except Exception:
            traceback.print_exc()
            return None

    def create_playlist(self, title, description, song_list):
        if not self.is_authenticated:
            return None
        try:
            video_ids = [song['videoId'] for song in song_list if 'videoId' in song]
            playlist_id = self.ytmusic.create_playlist(
                title=title, description=description, privacy_status="PRIVATE", video_ids=video_ids
            )
            return playlist_id
        except Exception:
            traceback.print_exc()
            return None

    def get_song_recommendations(self, video_id, limit=5):
        try:
            watch_playlist = self.ytmusic.get_watch_playlist(videoId=video_id, limit=limit)
            if 'tracks' in watch_playlist and watch_playlist['tracks']:
                recommendations = []
                for track in watch_playlist['tracks']:
                    if track.get('videoId') == video_id: continue
                    if track.get('videoId'):
                        recommendations.append({
                            'videoId': track['videoId'],
                            'title': track.get('title', 'Título Desconocido'),
                            'artists': track.get('artists', [{'name': 'Desconocido'}]),
                            'thumbnails': track.get('thumbnails', []),
                        })
                return recommendations
            return []
        except Exception:
            return []

    def get_song_lyrics(self, video_id):
        """
        Obtiene la letra de una canción.
        """
        if not video_id:
            return None
        try:
            watch_data = self.ytmusic.get_watch_playlist(videoId=video_id)
            lyrics_browse_id = watch_data.get('lyrics')

            if not lyrics_browse_id:
                return None

            lyrics_data = self.ytmusic.get_lyrics(browseId=lyrics_browse_id)
            return lyrics_data

        except Exception:
            traceback.print_exc()
            return None

    def get_library_songs(self, limit=50):
        if not self.is_authenticated:
            return []
        try:
            tracks = self.ytmusic.get_library_songs(limit=limit)
            return self.normalize_playlist_tracks(tracks)
        except Exception:
            return []

    def get_library_artists(self, limit=50):
        if not self.is_authenticated:
            return []
        try:
            return self.ytmusic.get_library_artists(limit=limit)
        except Exception:
            return []

    def get_home(self):
        try:
            return self.ytmusic.get_home(limit=20)
        except Exception:
            return []

    def parse_home_section(self, section):
        items = []
        for item in section.get("contents", []):
            thumbs = item.get("thumbnails", [])
            if "videoId" in item:
                items.append({
                    "type": "song",
                    "videoId": item.get("videoId"),
                    "title": item.get("title", "Sin título"),
                    "artists": item.get("artists", []),
                    "thumbnails": thumbs,
                })
            elif "playlistId" in item:
                items.append({
                    "type": "playlist",
                    "playlistId": item.get("playlistId"),
                    "title": item.get("title", "Playlist"),
                    "thumbnails": thumbs,
                })
            elif "browseId" in item:
                items.append({
                    "type": "album",
                    "browseId": item.get("browseId"),
                    "title": item.get("title", "Álbum"),
                    "thumbnails": thumbs,
                })
        return items
