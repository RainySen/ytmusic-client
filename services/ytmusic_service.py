from ytmusicapi import YTMusic

class YTMusicService:
    def __init__(self):
        self.ytmusic = YTMusic()  # Sin autenticación

    def search(self, query):
        results = self.ytmusic.search(query, filter="songs", limit=20)
        return results

    def get_stream_url(self, video_id):
        return f"https://music.youtube.com/watch?v={video_id}"

    def get_playlist_songs(self, playlist_id):
        try:
            playlist_data = self.ytmusic.get_playlist(playlistId=playlist_id, limit=None)

            if 'tracks' in playlist_data:
                return playlist_data['tracks']
        except Exception as e:
            print(f"Error al obtener la playlist: {e}")
            return None
