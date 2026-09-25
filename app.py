import logging
import os
import sys

import qtawesome as qta
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from core.bootstrap import build_services, build_ui
from infra.web_session import configure_web_engine_environment
from core.config import AppPaths
from core.logging_setup import setup_logging
from ui.login_window import LoginWindow

log = logging.getLogger("app")


# entrada app arranque login ui
def main() -> int:
    paths = AppPaths.detect()
    paths.ensure_dirs()
    setup_logging(paths)

    configure_web_engine_environment(os.environ)
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    icon = qta.icon("fa5s.music", color="#03adb7")
    app.setWindowIcon(icon)

    services = build_services(paths)
    state = {"ui": None, "login": None}

    def start_main_application():
        if state["ui"] is not None:
            return
        ui = build_ui(services, icon)
        state["ui"] = ui
        ui.start(services)
        ui.window.resize(1240, 750)
        ui.window.show()
        if state["login"] is not None:
            state["login"].close()
        services.warm_up()

    if services.auth.is_authenticated:
        start_main_application()
    else:
        login = LoginWindow(services.auth, icon)
        login.login_success.connect(start_main_application)
        login.login_skipped.connect(start_main_application)
        login.closed.connect(lambda: app.quit() if state["ui"] is None else None)
        state["login"] = login
        login.show()

    exit_code = app.exec()

    busy = services.shutdown()
    if busy:
        logging.shutdown()
        os._exit(exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
