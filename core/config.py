import glob
import os
import shutil
import sys
from dataclasses import dataclass

APP_NAME = "YTMusic Client"
DATA_DIR_NAME = "data"
LEGACY_DATA = ("oauth.json", "local_playlists.json", "queue_and_cache.json", "lyrics_settings.json",
               "ytmusic-client.log*", "cache", ".yt-dlp-cache")

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
        return AppPaths(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    @property
    def data_dir(self) -> str:
        return os.path.join(self.base_dir, DATA_DIR_NAME)

    def _join(self, *parts: str) -> str:
        return os.path.join(self.data_dir, *parts)

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

    # datos usuario carpeta data migrar
    def ensure_dirs(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        self._migrate_legacy()
        for path in (self.cache_dir, self.thumbnail_cache_dir, self.ytdlp_cache_dir):
            os.makedirs(path, exist_ok=True)

    def _migrate_legacy(self) -> None:
        for pattern in LEGACY_DATA:
            for old in glob.glob(os.path.join(self.base_dir, pattern)):
                new = os.path.join(self.data_dir, os.path.basename(old))
                if not os.path.exists(new):
                    try:
                        shutil.move(old, new)
                    except OSError:
                        pass
