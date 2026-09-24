from __future__ import annotations

import time
from hashlib import sha1

YTM_ORIGIN = "https://music.youtube.com"
SUPPORTED_BROWSERS = ["firefox", "chrome", "edge", "brave", "chromium", "opera", "vivaldi", "whale"]
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class BrowserSessionError(Exception):
    pass


class _SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def _read_cookies(browser: str) -> dict[str, str]:
    import yt_dlp

    ydl = yt_dlp.YoutubeDL({
        "quiet": True,
        "no_warnings": True,
        "cookiesfrombrowser": (browser,),
        "logger": _SilentLogger(),
    })
    return {
        c.name: c.value
        for c in ydl.cookiejar
        if "youtube" in (c.domain or "") or "google" in (c.domain or "")
    }


def session_id(cookies: dict[str, str]) -> str:
    return cookies.get("__Secure-3PAPISID") or cookies.get("SAPISID", "")


def parse_cookie_string(value: str) -> dict[str, str]:
    cookies = {}
    for pair in value.split(";"):
        name, sep, val = pair.strip().partition("=")
        if sep and name:
            cookies[name] = val
    return cookies


# login cabeceras sesion
def headers_from_cookies(cookies: dict[str, str], *, user_agent: str | None = None, authuser: str = "0") -> dict[str, str]:
    sapisid = session_id(cookies)
    timestamp = str(int(time.time()))
    digest = sha1(f"{timestamp} {sapisid} {YTM_ORIGIN}".encode()).hexdigest()
    return {
        "cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
        "x-goog-authuser": authuser,
        "authorization": f"SAPISIDHASH {timestamp}_{digest}",
        "user-agent": user_agent or _USER_AGENT,
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "content-type": "application/json",
        "content-encoding": "gzip",
        "origin": YTM_ORIGIN,
    }


# login detectar navegador
def has_youtube_session(browser: str) -> bool:
    try:
        return bool(session_id(_read_cookies(browser)))
    except Exception:
        return False


# login cookies navegador
def build_headers(browser: str) -> dict[str, str]:
    try:
        cookies = _read_cookies(browser)
    except Exception as exc:
        raise BrowserSessionError(str(exc)) from exc
    if not session_id(cookies):
        raise BrowserSessionError(f"No se encontró sesión de YouTube en {browser}.")
    return headers_from_cookies(cookies)
