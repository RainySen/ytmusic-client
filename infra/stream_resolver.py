from __future__ import annotations

import importlib
import logging
import os
import shutil
import threading
import time
from http.cookiejar import Cookie

from domain.stream_cache import StreamInfo, expiry_from_url
from infra.account_only_tracks import AccountOnlyTracks
from infra.secure_store import read_secret_json

log = logging.getLogger(__name__)

ACCOUNT_MARKERS = ("premium", "sign in to confirm", "members only", "join this channel")
JS_RUNTIMES = (("deno", "deno"), ("node", "node"), ("bun", "bun"), ("quickjs", "qjs"))
COOKIE_DOMAIN = ".youtube.com"
COOKIE_TTL_S = 365 * 24 * 3600
NO_RUNTIME_MESSAGE = ("Esta canción es solo para YouTube Music Premium y no se encontró el reproductor necesario "
                      "para usar tu sesión. Reinstala la aplicación o instala Node.js o Deno.")
NO_SESSION_MESSAGE = "Esta canción es solo para YouTube Music Premium. Inicia sesión con una cuenta Premium."


class StreamResolveError(Exception):
    pass


def needs_account(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ACCOUNT_MARKERS)


def available_js_runtimes() -> dict[str, dict]:
    return {name: {} for name, exe in JS_RUNTIMES if shutil.which(exe)}


def session_cookies(cookie_header: str, now: float) -> list[Cookie]:
    cookies = []
    for part in cookie_header.split(";"):
        name, sep, value = part.strip().partition("=")
        if not sep or not name:
            continue
        cookies.append(Cookie(0, name, value, None, False, COOKIE_DOMAIN, True, True, "/", True, True,
                              int(now) + COOKIE_TTL_S, False, None, None, {}))
    return cookies


class YtDlpStreamResolver:
    def __init__(self, cache_dir: str, socket_timeout: int = 10, auth_file: str | None = None,
                 account_only: AccountOnlyTracks | None = None):
        self._cache_dir = cache_dir
        self._socket_timeout = socket_timeout
        self._auth_file = auth_file
        self._local = threading.local()
        self._account_only = account_only if account_only is not None else AccountOnlyTracks()

    def warm_up(self) -> None:
        importlib.import_module("yt_dlp")

    # same runtime everywhere: yt-dlp defaults to deno and caches it as missing
    def _options(self) -> dict:
        return {
            "js_runtimes": available_js_runtimes(),
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
        }

    def _ydl(self):
        ydl = getattr(self._local, "ydl", None)
        if ydl is None:
            import yt_dlp

            ydl = yt_dlp.YoutubeDL(self._options())
            self._local.ydl = ydl
        return ydl

    # premium-only: account cookies plus a js runtime for the player challenge
    def _session_ydl(self, cookie_header: str):
        cached = getattr(self._local, "session", None)
        if cached is not None and cached[0] == cookie_header:
            return cached[1]
        runtimes = available_js_runtimes()
        if not runtimes:
            raise StreamResolveError(NO_RUNTIME_MESSAGE)
        import yt_dlp

        ydl = yt_dlp.YoutubeDL({**self._options(), "js_runtimes": runtimes})
        for cookie in session_cookies(cookie_header, time.time()):
            ydl.cookiejar.set_cookie(cookie)
        self._local.session = (cookie_header, ydl)
        return ydl

    def _cookie_header(self) -> str:
        if not self._auth_file or not os.path.exists(self._auth_file):
            return ""
        data = read_secret_json(self._auth_file)
        return str(data.get("cookie") or data.get("Cookie") or "") if isinstance(data, dict) else ""

    def resolve(self, video_id: str) -> StreamInfo:
        url = f"https://music.youtube.com/watch?v={video_id}"
        if video_id in self._account_only:
            info = self._resolve_with_session(url, None)
        else:
            try:
                info = self._ydl().extract_info(url, download=False)
            except Exception as exc:
                self._local.ydl = None
                if not needs_account(exc):
                    raise StreamResolveError(_short(exc)) from exc
                self._account_only.add(video_id)
                log.info("Remembered %s as account-only", video_id)
                info = self._resolve_with_session(url, exc)
        stream_url = (info or {}).get("url")
        if not stream_url:
            raise StreamResolveError("yt-dlp no devolvió una URL de audio.")
        return StreamInfo(
            video_id=video_id,
            url=stream_url,
            title=info.get("title") or "Título Desconocido",
            expires_at=expiry_from_url(stream_url),
        )

    def _resolve_with_session(self, url: str, first: Exception | None) -> dict:
        cookie_header = self._cookie_header()
        if not cookie_header:
            raise StreamResolveError(NO_SESSION_MESSAGE) from first
        log.info("Account-only stream, retrying with the session: %s", url)
        try:
            return self._session_ydl(cookie_header).extract_info(url, download=False)
        except StreamResolveError:
            raise
        except Exception as exc:
            self._local.session = None
            log.warning("Session retry failed for %s", url, exc_info=True)
            raise StreamResolveError(_short(exc)) from exc


def _short(exc: Exception) -> str:
    text = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
    return text.replace("ERROR: ", "")[:200]
