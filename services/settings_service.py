from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from domain.settings import Settings
from infra.settings_repository import SettingsRepository


class SettingsService(QObject):
    changed = Signal(object)

    def __init__(self, repo: SettingsRepository, parent: QObject | None = None):
        super().__init__(parent)
        self._repo = repo
        self._settings = repo.load()

    @property
    def settings(self) -> Settings:
        return self._settings

    def update(self, **changes) -> None:
        updated = self._settings.with_changes(**changes)
        if updated == self._settings:
            return
        self._settings = updated
        self._repo.save(updated)
        self.changed.emit(updated)
