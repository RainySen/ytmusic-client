from ytmusicapi import YTMusic
import os
import traceback
import json

AUTH_FILE = "oauth.json"


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
                            'artists': track.get('artists', [{'name': 'Desconocido'}])
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