from __future__ import annotations

import importlib
import logging
import threading

from domain.stream_cache import StreamInfo, expiry_from_url

log = logging.getLogger(__name__)


class StreamResolveError(Exception):
    pass


# yt-dlp url audio
class YtDlpStreamResolver:
    def __init__(self, cache_dir: str, socket_timeout: int = 10):
        self._cache_dir = cache_dir
        self._socket_timeout = socket_timeout
        self._local = threading.local()

    def warm_up(self) -> None:
        importlib.import_module("yt_dlp")

    def _ydl(self):
        ydl = getattr(self._local, "ydl", None)
        if ydl is None:
            import yt_dlp

            ydl = yt_dlp.YoutubeDL({
                "format": "bestaudio/best",
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "skip_download": True,
                "socket_timeout": self._socket_timeout,
                "retries": 1,
                "extractor_retries": 1,
                "cachedir": self._cache_dir,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            })
            self._local.ydl = ydl
        return ydl

    def resolve(self, video_id: str) -> StreamInfo:
        url = f"https://music.youtube.com/watch?v={video_id}"
        try:
            info = self._ydl().extract_info(url, download=False)
        except Exception as exc:
            self._local.ydl = None
            raise StreamResolveError(_short(exc)) from exc
        stream_url = (info or {}).get("url")
        if not stream_url:
            raise StreamResolveError("yt-dlp no devolvió una URL de audio.")
        return StreamInfo(
            video_id=video_id,
            url=stream_url,
            title=info.get("title") or "Título Desconocido",
            expires_at=expiry_from_url(stream_url),
        )


def _short(exc: Exception) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return text.replace("ERROR: ", "")[:200]
