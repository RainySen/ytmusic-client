import subprocess
from typing import Callable

from PySide6.QtWidgets import QApplication

from infra.autostart import launch_command


# release first: the new process must not wake this one through the single-instance guard
def restart_app(release: Callable[[], None], popen: Callable = subprocess.Popen) -> None:
    release()
    popen(launch_command(background=False))
    QApplication.quit()
