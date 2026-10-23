import os
import subprocess
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def reveal_file(path: str) -> None:
    if sys.platform == "win32" and os.path.exists(path):
        subprocess.Popen(f'explorer /select,"{path}"')
        return
    QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))
