from __future__ import annotations

from domain.settings import Settings
from infra.json_store import read_json, write_json_atomic
from infra.secure_store import protect_text, unprotect_text

SECRET_FIELDS = ("better_lyrics_key",)


class SettingsRepository:
    def __init__(self, path: str):
        self._path = path

    def load(self) -> Settings:
        data = read_json(self._path, default={})
        if isinstance(data, dict):
            data = {k: unprotect_text(v) if k in SECRET_FIELDS and isinstance(v, str) else v for k, v in data.items()}
        return Settings.from_dict(data)

    def save(self, settings: Settings) -> None:
        data = settings.to_dict()
        for field in SECRET_FIELDS:
            data[field] = protect_text(data[field])
        write_json_atomic(self._path, data)
