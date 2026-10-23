from __future__ import annotations

import logging
from typing import Callable

import requests

from domain.versions import is_newer, version_label
from infra.concurrency import TaskRunner
from services.settings_service import SettingsService

log = logging.getLogger(__name__)

RELEASES_URL = "https://api.github.com/repos/RainySen/ytmusic-client/releases/latest"
RELEASES_PAGE = "https://github.com/RainySen/ytmusic-client/releases/"

Available = Callable[[str, str], None]


class UpdateService:
    def __init__(self, runner: TaskRunner, settings: SettingsService, current: str):
        self._runner = runner
        self._settings = settings
        self._current = current

    def check(self, on_available: Available) -> None:
        def work() -> tuple[str, str]:
            response = requests.get(RELEASES_URL, timeout=10, headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            data = response.json()
            return str(data.get("tag_name") or ""), str(data.get("html_url") or "")

        def done(release: tuple[str, str]) -> None:
            tag, url = release
            version = version_label(tag)
            # only this project's release pages are ever opened
            if (url.startswith(RELEASES_PAGE) and is_newer(tag, self._current)
                    and version != self._settings.settings.announced_version):
                on_available(version, url)

        self._runner.submit(work, done, lambda exc: log.info("Update check skipped: %s", exc), key="update-check")

    # notice is optional: shown once per version
    def dismiss(self, version: str) -> None:
        self._settings.update(announced_version=version)
