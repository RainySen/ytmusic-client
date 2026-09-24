import os
import sys
from dataclasses import dataclass

APP_NAME = "YTMusic Client"

NETWORK_CACHING_MS = 3000
RADIO_QUEUE_LIMIT = 6
RADIO_FETCH = 10
EXTEND_BATCH = 2
HOVER_PREFETCH_MS = 350
PREFETCH_AHEAD = 3
STREAM_EXPIRY_MARGIN_S = 120
CONTENT_LANGUAGE = "es"
HOME_SECTIONS = 20
QUEUE_HISTORY_LIMIT = 50
MAX_CONSECUTIVE_PLAY_FAILURES = 3


# rutas archivos cache
@dataclass(frozen=True)
class AppPaths:
    base_dir: str

    @staticmethod
    def detect() -> "AppPaths":
        if getattr(sys, "frozen", False):
            return AppPaths(os.path.dirname(sys.executable))
        return AppPaths(os.path.dirname(os.path.abspath(__file__)))

    def _join(self, *parts: str) -> str:
        return os.path.join(self.base_dir, *parts)

    @property
    def auth_file(self) -> str:
        return self._join("oauth.json")

    @property
    def session_file(self) -> str:
        return self._join("queue_and_cache.json")

    @property
    def playlists_file(self) -> str:
        return self._join("local_playlists.json")

    @property
    def lyrics_settings_file(self) -> str:
        return self._join("lyrics_settings.json")

    @property
    def cache_dir(self) -> str:
        return self._join("cache")

    @property
    def thumbnail_cache_dir(self) -> str:
        return os.path.join(self.cache_dir, "thumbnails")

    @property
    def home_cache_file(self) -> str:
        return os.path.join(self.cache_dir, "home.json")

    @property
    def recent_playlists_file(self) -> str:
        return os.path.join(self.cache_dir, "recent_playlists.json")

    @property
    def ytdlp_cache_dir(self) -> str:
        return self._join(".yt-dlp-cache")

    @property
    def log_file(self) -> str:
        return self._join("ytmusic-client.log")

    def ensure_dirs(self) -> None:
        for path in (self.cache_dir, self.thumbnail_cache_dir, self.ytdlp_cache_dir):
            os.makedirs(path, exist_ok=True)
