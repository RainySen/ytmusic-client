from __future__ import annotations

import glob
import json
import logging
import os
import sys

log = logging.getLogger(__name__)

SUPPORTED = ("es", "en", "pt")
SOURCE = "es"

_catalogs: dict[str, dict[str, str]] = {}
_language = SOURCE


def locales_dir() -> str:
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, "locales")


# one file per area; a broken file is skipped, never fatal
def load(directory: str) -> dict[str, dict[str, str]]:
    catalogs: dict[str, dict[str, str]] = {}
    for lang in SUPPORTED:
        merged: dict[str, str] = {}
        for path in sorted(glob.glob(os.path.join(directory, lang, "*.json"))):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                log.error("Skipping unreadable locale file %s", path, exc_info=True)
                continue
            if isinstance(data, dict):
                merged.update({str(k): str(v) for k, v in data.items()})
        catalogs[lang] = merged
    return catalogs


def set_language(lang: str, catalogs: dict[str, dict[str, str]] | None = None) -> str:
    global _catalogs, _language
    if catalogs is not None:
        _catalogs = catalogs
    _language = lang if lang in SUPPORTED else SOURCE
    return _language


def language() -> str:
    return _language


# current language -> spanish -> the key itself
def t(key: str, **values) -> str:
    text = _catalogs.get(_language, {}).get(key) or _catalogs.get(SOURCE, {}).get(key) or key
    if not values:
        return text
    try:
        return text.format_map(values)
    except (KeyError, IndexError, ValueError):
        log.warning("Missing values for %s", key)
        return text


def resolve_language(settings, locale_name: str) -> str:
    chosen = getattr(settings, "app_language", "")
    return chosen if chosen in SUPPORTED else system_language(locale_name)


def system_language(locale_name: str) -> str:
    code = locale_name.replace("-", "_").split("_")[0].lower()
    return code if code in SUPPORTED else "en"
