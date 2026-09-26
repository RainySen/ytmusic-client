from __future__ import annotations

import logging
import os
import sys

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "YTMusicClient"
BACKGROUND_FLAG = "--background"


# comando de arranque en segundo plano
def launch_command(frozen: bool | None = None, executable: str | None = None, script: str | None = None) -> str:
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = executable or sys.executable
    if frozen:
        return f'"{executable}" {BACKGROUND_FLAG}'
    windowless = os.path.join(os.path.dirname(executable), "pythonw.exe")
    interpreter = windowless if os.path.exists(windowless) else executable
    script = script or os.path.abspath(sys.argv[0])
    return f'"{interpreter}" "{script}" {BACKGROUND_FLAG}'


# inicio con windows registro
class Autostart:
    def __init__(self, key: str = RUN_KEY, name: str = VALUE_NAME):
        self._key = key
        self._name = name

    @property
    def available(self) -> bool:
        return sys.platform == "win32"

    def is_enabled(self) -> bool:
        if not self.available:
            return False
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key) as key:
                value, _ = winreg.QueryValueEx(key, self._name)
        except OSError:
            return False
        return bool(value)

    def set_enabled(self, enabled: bool, command: str | None = None) -> bool:
        if not self.available:
            return False
        import winreg

        try:
            if enabled:
                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, self._key, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, self._name, 0, winreg.REG_SZ, command or launch_command())
            else:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._key, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, self._name)
        except FileNotFoundError:
            return not enabled
        except OSError:
            log.warning("Could not update the startup entry", exc_info=True)
            return False
        return True
