import vlc
import yt_dlp

class Player:
    def __init__(self):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.is_playing = False

    def get_audio_url(self, url):
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"], info["title"]

    def play(self, url):
        stream_url, title = self.get_audio_url(url)
        media = self.instance.media_new(stream_url)
        self.player.set_media(media)
        self.player.play()
        self.is_playing = True
        return title

    def toggle_play(self):
        self.player.pause()
        self.is_playing = not self.is_playing

    def set_volume(self, volume):
        self.player.audio_set_volume(volume)
