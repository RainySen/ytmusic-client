from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, Signal

log = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
HOTKEY_BASE_ID = 0x5A10
KEYS = {"next": VK_MEDIA_NEXT_TRACK, "previous": VK_MEDIA_PREV_TRACK, "play_pause": VK_MEDIA_PLAY_PAUSE}


# atajos globales de windows
class WindowsHotkeys:
    def register(self, hotkey_id: int, virtual_key: int) -> bool:
        return bool(ctypes.windll.user32.RegisterHotKey(None, hotkey_id, MOD_NOREPEAT, virtual_key))

    def unregister(self, hotkey_id: int) -> None:
        ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, on_hotkey):
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and self._on_hotkey(int(msg.wParam)):
                return True, 0
        return False, 0


# teclas multimedia globales
class MediaKeys(QObject):
    play_pause = Signal()
    next_track = Signal()
    previous_track = Signal()

    def __init__(self, hotkeys=None, parent: QObject | None = None):
        super().__init__(parent)
        self._hotkeys = hotkeys if hotkeys is not None else (WindowsHotkeys() if sys.platform == "win32" else None)
        self._ids: dict[int, str] = {}
        self._filter: _HotkeyFilter | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._ids)

    def set_enabled(self, enabled: bool) -> bool:
        if not enabled:
            self._disable()
            return True
        if self.enabled:
            return True
        return self._enable()

    def _enable(self) -> bool:
        if self._hotkeys is None:
            return False
        for offset, (name, key) in enumerate(KEYS.items()):
            hotkey_id = HOTKEY_BASE_ID + offset
            if self._hotkeys.register(hotkey_id, key):
                self._ids[hotkey_id] = name
            else:
                log.info("Media key %s is already taken by another app", name)
        app = QCoreApplication.instance()
        if self._ids and app is not None:
            self._filter = _HotkeyFilter(self.handle)
            app.installNativeEventFilter(self._filter)
        return bool(self._ids)

    def _disable(self) -> None:
        app = QCoreApplication.instance()
        if self._filter is not None and app is not None:
            app.removeNativeEventFilter(self._filter)
        self._filter = None
        for hotkey_id in self._ids:
            self._hotkeys.unregister(hotkey_id)
        self._ids.clear()

    def handle(self, hotkey_id: int) -> bool:
        name = self._ids.get(hotkey_id)
        if name is None:
            return False
        {"play_pause": self.play_pause, "next": self.next_track, "previous": self.previous_track}[name].emit()
        return True
