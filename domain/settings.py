from __future__ import annotations

from dataclasses import dataclass, replace

RADIO_SIZE_OPTIONS = (5, 10, 15, 25, 50, 75, 100, 150, 200, 300, 500, 1000, 0)
DEFAULT_RADIO_SIZE = 50
FREE_MEMORY_OPTIONS = (10, 20, 60, 180)
DEFAULT_FREE_MEMORY_S = 20
CONTENT_LANGUAGES = {
    "es": "Español", "en": "English", "pt": "Português", "fr": "Français", "de": "Deutsch", "it": "Italiano",
    "nl": "Nederlands", "cs": "Čeština", "tr": "Türkçe", "ru": "Русский", "ar": "العربية", "hi": "हिन्दी",
    "ur": "اردو", "ja": "日本語", "ko": "한국어", "zh_CN": "中文 (简体)", "zh_TW": "中文 (繁體)",
}
DEFAULT_CONTENT_LANGUAGE = "es"
LYRICS_PROVIDER_NAMES = ("betterlyrics", "lrclib", "youtube")
THUMBNAIL_QUALITY_OPTIONS = ("low", "auto", "high")
DEFAULT_THUMBNAIL_QUALITY = "auto"
THUMBNAIL_CACHE_OPTIONS = (100, 200, 400, 800)
DEFAULT_THUMBNAIL_CACHE = 400


def _flag(data: dict, name: str, default: bool) -> bool:
    value = data.get(name)
    return value if isinstance(value, bool) else default


def _choice(data: dict, name: str, options: tuple, default: int) -> int:
    value = data.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) and value in options else default


def _coordinate(data: dict, name: str) -> int | None:
    value = data.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _language(data: dict) -> str:
    value = data.get("content_language")
    return value if isinstance(value, str) and value in CONTENT_LANGUAGES else DEFAULT_CONTENT_LANGUAGE


def _providers(data: dict) -> tuple[str, ...]:
    value = data.get("lyrics_providers")
    if not isinstance(value, (list, tuple)):
        return LYRICS_PROVIDER_NAMES
    names = [str(name).lower() for name in value]
    return tuple(dict.fromkeys(name for name in names if name in LYRICS_PROVIDER_NAMES))


def _text(data: dict, name: str) -> str:
    value = data.get(name)
    return value.strip() if isinstance(value, str) else ""


def _quality(data: dict) -> str:
    value = data.get("thumbnail_quality")
    return value if value in THUMBNAIL_QUALITY_OPTIONS else DEFAULT_THUMBNAIL_QUALITY


@dataclass(frozen=True)
class Settings:
    background_on_close: bool = True
    mini_player: bool = True
    mini_x: int | None = None
    mini_y: int | None = None
    auto_queue: bool = True
    radio_size: int = DEFAULT_RADIO_SIZE
    free_memory: bool = True
    free_memory_seconds: int = DEFAULT_FREE_MEMORY_S
    remember_volume: bool = True
    volume: int = 100
    restore_queue: bool = True
    start_with_windows: bool = False
    content_language: str = DEFAULT_CONTENT_LANGUAGE
    lyrics_providers: tuple[str, ...] = LYRICS_PROVIDER_NAMES
    better_lyrics_key: str = ""
    media_keys: bool = True
    notifications: bool = True
    thumbnail_quality: str = DEFAULT_THUMBNAIL_QUALITY
    thumbnail_cache_limit: int = DEFAULT_THUMBNAIL_CACHE
    romanized_lyrics: bool = True

    def with_changes(self, **changes) -> "Settings":
        unknown = set(changes) - set(self.__dataclass_fields__)
        if unknown:
            raise KeyError(f"Ajuste desconocido: {', '.join(sorted(unknown))}")
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @staticmethod
    def from_dict(data) -> "Settings":
        if not isinstance(data, dict):
            return Settings()
        volume = data.get("volume")
        volume = volume if isinstance(volume, int) and not isinstance(volume, bool) and 0 <= volume <= 100 else 100
        return Settings(
            background_on_close=_flag(data, "background_on_close", True),
            mini_player=_flag(data, "mini_player", True),
            mini_x=_coordinate(data, "mini_x"),
            mini_y=_coordinate(data, "mini_y"),
            auto_queue=_flag(data, "auto_queue", True),
            radio_size=_choice(data, "radio_size", RADIO_SIZE_OPTIONS, DEFAULT_RADIO_SIZE),
            free_memory=_flag(data, "free_memory", True),
            free_memory_seconds=_choice(data, "free_memory_seconds", FREE_MEMORY_OPTIONS, DEFAULT_FREE_MEMORY_S),
            remember_volume=_flag(data, "remember_volume", True),
            volume=volume,
            restore_queue=_flag(data, "restore_queue", True),
            start_with_windows=_flag(data, "start_with_windows", False),
            content_language=_language(data),
            lyrics_providers=_providers(data),
            better_lyrics_key=_text(data, "better_lyrics_key"),
            media_keys=_flag(data, "media_keys", True),
            notifications=_flag(data, "notifications", True),
            thumbnail_quality=_quality(data),
            thumbnail_cache_limit=_choice(data, "thumbnail_cache_limit", THUMBNAIL_CACHE_OPTIONS, DEFAULT_THUMBNAIL_CACHE),
            romanized_lyrics=_flag(data, "romanized_lyrics", True),
        )
