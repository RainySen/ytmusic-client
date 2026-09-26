import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    yield app


@pytest.fixture
def wait_until(qapp):
    def _wait(predicate, timeout_ms=3000):
        loop = QEventLoop()
        deadline = QTimer()
        deadline.setSingleShot(True)
        deadline.timeout.connect(loop.quit)
        poll = QTimer()
        poll.timeout.connect(lambda: loop.quit() if predicate() else None)
        deadline.start(timeout_ms)
        poll.start(5)
        if not predicate():
            loop.exec()
        deadline.stop()
        poll.stop()
        return predicate()
    return _wait


@pytest.fixture(autouse=True)
def no_real_quit(monkeypatch):
    monkeypatch.setattr(QApplication, "quit", staticmethod(lambda: None))


@pytest.fixture(autouse=True)
def close_leftover_windows(request):
    yield
    if "qapp" in request.fixturenames:
        for widget in QApplication.topLevelWidgets():
            widget.close()
        QApplication.processEvents()
