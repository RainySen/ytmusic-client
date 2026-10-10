from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
from ctypes import wintypes
from typing import Any

from infra.json_store import read_json, write_json_atomic

log = logging.getLogger(__name__)

# dpapi: blob tied to the windows user
MAGIC = b"DPAPI1\n"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def available() -> bool:
    return sys.platform == "win32"


def _call(name: str, data: bytes) -> bytes:
    buffer = ctypes.create_string_buffer(data, len(data))
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    result = _Blob()
    fn = getattr(ctypes.windll.crypt32, name)
    if not fn(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(result)):
        raise OSError(f"{name} failed: {ctypes.GetLastError()}")
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


def protect(data: bytes) -> bytes:
    return _call("CryptProtectData", data)


def unprotect(data: bytes) -> bytes:
    return _call("CryptUnprotectData", data)


# older plaintext files still read, rewritten encrypted on next save
def read_secret_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return default
    except OSError:
        log.warning("Could not read %s", path, exc_info=True)
        return default
    if not raw.startswith(MAGIC):
        return read_json(path, default)
    try:
        return json.loads(unprotect(raw[len(MAGIC):]).decode("utf-8"))
    except Exception:
        log.warning("Could not decrypt %s; it belongs to another Windows user or is damaged", path)
        return default


def write_secret_json(path: str, data: Any) -> bool:
    if not available():
        return write_json_atomic(path, data, indent=4)
    try:
        blob = MAGIC + protect(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    except OSError:
        log.warning("Could not encrypt %s; storing it as plain text", path, exc_info=True)
        return write_json_atomic(path, data, indent=4)
    directory = os.path.dirname(path) or "."
    tmp_path = f"{path}.tmp"
    try:
        os.makedirs(directory, exist_ok=True)
        with open(tmp_path, "wb") as fh:
            fh.write(blob)
        os.replace(tmp_path, path)
        return True
    except OSError:
        log.warning("Could not write %s", path, exc_info=True)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return False


def is_encrypted(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(len(MAGIC)) == MAGIC
    except OSError:
        return False
