from __future__ import annotations

import logging
import os
import shutil

log = logging.getLogger(__name__)


def _tree_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def _empty_directory(path: str) -> None:
    try:
        entries = list(os.scandir(path))
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.remove(entry.path)
        except OSError:
            log.debug("Could not remove %s", entry.path)


# cache regenerable miniaturas y descargas
class CacheStore:
    def __init__(self, thumbnails, directories: list[str] | None = None, files: list[str] | None = None):
        self._thumbnails = thumbnails
        self._directories = directories or []
        self._files = files or []

    def size_bytes(self) -> int:
        total = self._thumbnails.disk_size()
        total += sum(_tree_size(path) for path in self._directories)
        for path in self._files:
            try:
                total += os.path.getsize(path)
            except OSError:
                pass
        return total

    def clear(self) -> int:
        before = self.size_bytes()
        self._thumbnails.clear_disk()
        for path in self._directories:
            _empty_directory(path)
        for path in self._files:
            try:
                os.remove(path)
            except OSError:
                pass
        return max(0, before - self.size_bytes())
