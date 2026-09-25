from __future__ import annotations

import os
from dataclasses import dataclass

from infra.json_store import read_json

DEFAULT_PROVIDERS = ("betterlyrics", "lrclib", "youtube")


@dataclass(frozen=True)
class LyricsSettings:
    providers: tuple[str, ...] = DEFAULT_PROVIDERS
    better_lyrics_api_key: str = ""


# letras config
def load_lyrics_settings(path: str, environ: dict | None = None) -> LyricsSettings:
    environ = os.environ if environ is None else environ
    data = read_json(path, {})
    data = data if isinstance(data, dict) else {}
    names = data.get("providers")
    providers = tuple(str(n).lower() for n in names) if isinstance(names, list) and names else DEFAULT_PROVIDERS
    key = environ.get("BETTER_LYRICS_API_KEY") or data.get("better_lyrics_api_key") or ""
    return LyricsSettings(providers, str(key))
