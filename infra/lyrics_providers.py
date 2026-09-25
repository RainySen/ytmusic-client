from __future__ import annotations

import logging
from typing import Any, Callable, Protocol

import requests

from domain.lyrics_parsing import parse_lrc, parse_ttml, plain_lyrics
from domain.models import Lyrics, LyricsQuery, clean_title, parse_lyrics
from infra.ytmusic_gateway import YTMusicGateway

log = logging.getLogger(__name__)

USER_AGENT = "YTMusicClient/1.0 (https://github.com/RainySen/ytmusic-client)"
TIMEOUT_S = 6
DURATION_TOLERANCE_S = 3

HttpGet = Callable[..., Any]


class LyricsProvider(Protocol):
    name: str

    def fetch(self, query: LyricsQuery) -> Lyrics | None: ...


def _http_get(url: str, params: dict | None = None, headers: dict | None = None):
    return requests.get(url, params=params, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=TIMEOUT_S)


# letras better lyrics ttml
class BetterLyricsProvider:
    name = "Better Lyrics"
    URL = "https://api.betterlyrics.org/getLyrics"

    def __init__(self, api_key: str = "", http_get: HttpGet = _http_get):
        self._api_key = api_key.strip()
        self._get = http_get

    def fetch(self, query: LyricsQuery) -> Lyrics | None:
        if not query.title or not query.artist:
            return None
        params = {"s": clean_title(query.title), "a": query.artist, "al": query.album, "d": query.duration or ""}
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        response = self._get(self.URL, params=params, headers=headers)
        if response.status_code in (401, 403, 404, 422):
            return None
        response.raise_for_status()
        return parse_ttml((response.json() or {}).get("ttml"), self.name)


# letras lrclib lrc
class LrcLibProvider:
    name = "LRCLIB"
    BASE = "https://lrclib.net/api"

    def __init__(self, http_get: HttpGet = _http_get):
        self._get = http_get

    def fetch(self, query: LyricsQuery) -> Lyrics | None:
        if not query.title or not query.artist:
            return None
        if query.duration and query.album:
            response = self._get(f"{self.BASE}/get", params={
                "artist_name": query.artist, "track_name": clean_title(query.title),
                "album_name": query.album, "duration": query.duration})
            if response.status_code != 404:
                response.raise_for_status()
                found = self._lyrics_of(response.json())
                if found:
                    return found
        return self._search(query)

    def _search(self, query: LyricsQuery) -> Lyrics | None:
        response = self._get(f"{self.BASE}/search", params={
            "track_name": clean_title(query.title), "artist_name": query.artist})
        if response.status_code == 404:
            return None
        response.raise_for_status()
        candidates = [c for c in response.json() or [] if isinstance(c, dict) and not c.get("instrumental")]
        if query.duration:
            candidates = [c for c in candidates
                          if abs((c.get("duration") or 0) - query.duration) <= DURATION_TOLERANCE_S]
        candidates.sort(key=lambda c: (not c.get("syncedLyrics"),
                                       abs((c.get("duration") or 0) - query.duration) if query.duration else 0))
        for candidate in candidates:
            found = self._lyrics_of(candidate)
            if found:
                return found
        return None

    def _lyrics_of(self, data: dict) -> Lyrics | None:
        if not isinstance(data, dict) or data.get("instrumental"):
            return None
        return parse_lrc(data.get("syncedLyrics"), self.name) or plain_lyrics(data.get("plainLyrics"), self.name)


# letras youtube
class YouTubeMusicProvider:
    name = "YouTube Music"

    def __init__(self, gateway: YTMusicGateway):
        self._gateway = gateway

    def fetch(self, query: LyricsQuery) -> Lyrics | None:
        browse_id = self._gateway.get_lyrics_browse_id(query.video_id)
        if not browse_id:
            return None
        found = parse_lyrics(self._gateway.get_lyrics(browse_id))
        if found is None:
            return None
        return Lyrics(found.lines, found.synced, self.name)
