from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from domain.models import Lyrics, lyrics_query
from infra.concurrency import TaskRunner
from infra.lyrics_providers import LyricsProvider
from infra.romanization import UnisonRomanizer
from infra.ttl_cache import TTLCache

log = logging.getLogger(__name__)

LYRICS_TTL = 3600
PROVIDER_COOLDOWN_S = 60
_NOT_FOUND = object()


class LyricsService:
    def __init__(self, providers: list[LyricsProvider], runner: TaskRunner,
                 clock: Callable[[], float] = time.monotonic, romanizer: UnisonRomanizer | None = None,
                 romanize: bool = True):
        self._providers = list(providers)
        self._runner = runner
        self._clock = clock
        self._romanizer = romanizer
        self._romanize = romanize
        self._cache = TTLCache()
        self._cooldown: dict[str, float] = {}
        self._lock = threading.Lock()

    def set_providers(self, providers: list[LyricsProvider]) -> None:
        with self._lock:
            self._providers = list(providers)
            self._cooldown.clear()
        self._cache.clear()

    def set_romanize(self, enabled: bool) -> None:
        if enabled != self._romanize:
            self._romanize = enabled
            self._cache.clear()

    def fetch(self, song: dict, on_done: Callable[[Lyrics | None], None],
              on_error: Callable[[Exception], None] | None = None) -> None:
        query = lyrics_query(song)
        cached = self._cache.get(query.video_id, default=None)
        if cached is not None:
            on_done(None if cached is _NOT_FOUND else cached)
            return

        def ok(result: tuple[Lyrics | None, bool]) -> None:
            lyrics, complete = result
            if complete or (lyrics is not None and lyrics.synced):
                self._cache.set(query.video_id, lyrics if lyrics is not None else _NOT_FOUND, LYRICS_TTL)
            on_done(lyrics)

        self._runner.submit(lambda: self._search(query), ok, on_error, key="lyrics")

    # incomplete if a provider failed; not cached
    def _search(self, query) -> tuple[Lyrics | None, bool]:
        fallback: Lyrics | None = None
        complete = True
        for provider in list(self._providers):
            if self._cooling_down(provider.name):
                complete = False
                continue
            try:
                found = provider.fetch(query)
            except Exception as exc:
                log.warning("Lyrics provider %s failed: %s", provider.name, exc)
                with self._lock:
                    self._cooldown[provider.name] = self._clock() + PROVIDER_COOLDOWN_S
                complete = False
                continue
            if found is None:
                continue
            if found.synced:
                return self._romanized(found), True
            fallback = fallback or found
        return self._romanized(fallback) if fallback else fallback, complete

    def _romanized(self, lyrics: Lyrics) -> Lyrics:
        if not self._romanize or self._romanizer is None:
            return lyrics
        try:
            return self._romanizer.enrich(lyrics)
        except Exception:
            log.warning("Romanization failed", exc_info=True)
            return lyrics

    def _cooling_down(self, name: str) -> bool:
        with self._lock:
            return self._cooldown.get(name, 0) > self._clock()
