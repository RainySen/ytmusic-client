from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from typing import Any

log = logging.getLogger(__name__)
_write_lock = threading.Lock()


# leer json
def read_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        log.warning("Could not read %s", path, exc_info=True)
        return default


# guardar json atomico
def write_json_atomic(path: str, data: Any, indent: int | None = 2) -> bool:
    directory = os.path.dirname(path) or "."
    tmp_path = None
    try:
        with _write_lock:
            os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=indent, ensure_ascii=False)
            os.replace(tmp_path, path)
            tmp_path = None
        return True
    except (OSError, TypeError, ValueError):
        log.error("Could not write %s", path, exc_info=True)
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
