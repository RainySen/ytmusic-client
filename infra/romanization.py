from __future__ import annotations

import logging
from typing import Any, Callable

import requests

from domain.models import Lyrics

log = logging.getLogger(__name__)

USER_AGENT = "YTMusicClient/1.0 (https://github.com/RainySen/ytmusic-client)"
TIMEOUT_S = 8
MAX_LINES = 200
MAX_LINE_CHARS = 500
ATTRIBUTION = "Unison (https://unison.boidu.dev)"

HttpPost = Callable[..., Any]


def _http_post(url: str, json: dict):
    return requests.post(url, json=json, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)


class UnisonRomanizer:
    URL = "https://unison.boidu.dev/translate"

    def __init__(self, target: str = "en", http_post: HttpPost = _http_post):
        self._target = target
        self._post = http_post

    def enrich(self, lyrics: Lyrics) -> Lyrics:
        pending = [(i, line) for i, line in enumerate(lyrics.lines)
                  if line.text.strip() and not line.romanization]
        if not pending or len(lyrics.lines) > MAX_LINES:
            return lyrics
        texts = [line.text[:MAX_LINE_CHARS] for _i, line in pending]
        try:
            response = self._post(self.URL, json={"lines": texts, "to": self._target})
            response.raise_for_status()
            results = (response.json() or {}).get("lines") or []
        except Exception as exc:
            log.info("Unison romanization unavailable: %s", exc)
            return lyrics
        if len(results) != len(pending):
            return lyrics
        lines = list(lyrics.lines)
        for (index, line), result in zip(pending, results):
            romanized = (result or {}).get("romanization") or ""
            if romanized:
                lines[index] = line.__class__(line.text, line.time_ms, line.end_ms, line.words, romanized)
        return Lyrics(tuple(lines), lyrics.synced, lyrics.source)
