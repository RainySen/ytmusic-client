from ytmusicapi import YTMusic

class YTMusicService:
    def __init__(self):
        self.ytmusic = YTMusic()  # Sin autenticación por ahora

    def search(self, query):
        results = self.ytmusic.search(query, filter="songs", limit=20)
        return results

    def get_stream_url(self, video_id):
        return f"https://music.youtube.com/watch?v={video_id}"
