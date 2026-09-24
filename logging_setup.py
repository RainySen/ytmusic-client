import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from config import AppPaths

_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


# log archivo
def setup_logging(paths: AppPaths, level: int = logging.INFO) -> None:
    handlers: list[logging.Handler] = []
    try:
        handlers.append(RotatingFileHandler(paths.log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"))
    except OSError:
        pass
    if sys.stderr is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )

    qt_log = logging.getLogger("qt")
    qInstallMessageHandler(lambda mode, _context, message: qt_log.log(_QT_LEVELS.get(mode, logging.INFO), message))

    def log_uncaught(exc_type, exc, tb):
        logging.getLogger("uncaught").critical("Unhandled exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = log_uncaught
