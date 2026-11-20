from __future__ import annotations

import importlib.util
import logging
from dataclasses import replace
from typing import Callable

from domain.models import Lyrics

log = logging.getLogger(__name__)

# optional: the option shows up only when sen-romanizer is installed
LIBRARY = "sen_romanizer"


def available() -> bool:
    return importlib.util.find_spec(LIBRARY) is not None


class LocalRomanizer:
    def __init__(self, romanize: Callable[..., str], detect: Callable[[list[str]], str | None] | None = None):
        self._romanize = romanize
        self._detect = detect

    def enrich(self, lyrics: Lyrics) -> Lyrics:
        lines = []
        try:
            # the whole song picks the language: kanji-only lines of a japanese song are not chinese
            lang = self._detect([line.text for line in lyrics.lines]) if self._detect else None
            for line in lyrics.lines:
                roman = "" if line.romanization or not line.text.strip() else self._romanize(line.text, lang)
                # latin lines come back empty; identical text adds nothing under the line
                lines.append(replace(line, romanization=roman) if roman and roman != line.text else line)
        except Exception:
            log.warning("Romanization failed", exc_info=True)
            return lyrics
        return Lyrics(tuple(lines), lyrics.synced, lyrics.source)


def load_romanizer() -> LocalRomanizer | None:
    if not available():
        return None
    from sen_romanizer import detect_language, romanize
    return LocalRomanizer(romanize, detect_language)
