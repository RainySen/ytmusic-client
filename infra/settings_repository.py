from __future__ import annotations

from domain.settings import Settings
from infra.json_store import read_json, write_json_atomic


# ajustes json
class SettingsRepository:
    def __init__(self, path: str):
        self._path = path

    def load(self) -> Settings:
        return Settings.from_dict(read_json(self._path, default={}))

    def save(self, settings: Settings) -> None:
        write_json_atomic(self._path, settings.to_dict())
