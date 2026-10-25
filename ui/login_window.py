import qtawesome as qta
from importlib.util import find_spec

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from core.i18n import t
from ui import theme
from ui.components import dialogs

WINDOW_HEIGHT = 480
WEB_LOGIN_AVAILABLE = find_spec("PySide6.QtWebEngineWidgets") is not None


# built on use: the language is only known after startup
def _manual_instructions() -> str:
    return t("login.manual.instructions")


class LoginWindow(QWidget):
    login_success = Signal()
    login_skipped = Signal()
    closed = Signal()

    def __init__(self, auth, app_icon):
        super().__init__()
        self._auth = auth
        self._app_icon = app_icon
        self._web = None
        self._build()

    def _build(self):
        self.setWindowTitle(t("login.window.title"))
        self.setWindowIcon(self._app_icon)
        self.setFixedSize(400, WINDOW_HEIGHT)
        self.setStyleSheet(f"QWidget {{ background-color: {theme.BG}; }} QLabel {{ background: transparent; }}")

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignCenter)
        self._layout.setSpacing(14)
        self._layout.setContentsMargins(32, 32, 32, 32)

        icon = QLabel()
        icon.setPixmap(self._app_icon.pixmap(96, 96))
        icon.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(icon)

        title = QLabel(t("login.app_name"))
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {theme.TEXT};")
        self._layout.addWidget(title)

        credits_label = QLabel(t("login.credits"))
        credits_label.setAlignment(Qt.AlignCenter)
        credits_label.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        self._layout.addWidget(credits_label)
        self._layout.addStretch(1)

        if self._auth.is_authenticated:
            button = self._make_button(t("login.continue"), "primary")
            button.setDefault(True)
            button.clicked.connect(self.login_skipped)
            self._layout.addWidget(button)
            return

        if WEB_LOGIN_AVAILABLE:
            self._web_button = self._make_button(t("login.google"), "primary")
            self._web_button.setIcon(qta.icon("fa5b.google", color=theme.BG))
            self._web_button.clicked.connect(self._login_with_web)
            self._layout.addWidget(self._web_button)

        self._layout.addSpacing(4)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"color: {theme.BORDER};")
        self._layout.addWidget(separator)

        manual = QPushButton(t("login.manual.button"))
        manual.clicked.connect(self._manual_login)
        manual.setCursor(Qt.PointingHandCursor)
        manual.setStyleSheet(theme.button_qss("text", height=32))
        self._layout.addWidget(manual)

        skip = self._make_button(t("login.skip"), "tonal")
        skip.clicked.connect(self.login_skipped)
        self._layout.addWidget(skip)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

    def _login_with_web(self):
        if self._web is not None:
            self._web.raise_()
            self._web.activateWindow()
            return
        from ui.web_login_window import WebLoginWindow

        self._web = WebLoginWindow()
        self._web.session_captured.connect(self._on_web_session)
        self._web.closed.connect(self._on_web_closed)
        self._web.start()
        self._web.show()

    def _on_web_session(self, cookies, user_agent):
        self._web_button.setEnabled(False)
        self._web_button.setText(t("login.pending"))
        self._auth.login_with_web_session(cookies, user_agent, self._on_web_result)

    def _on_web_closed(self):
        self._web = None

    def _on_web_result(self, ok, error):
        self._web = None
        self._web_button.setEnabled(True)
        self._web_button.setText(t("login.google"))
        self._on_manual_result(ok, error)

    def _manual_login(self):
        text = dialogs.prompt_text(self, t("login.manual.title"), _manual_instructions(), ok=t("login.manual.ok"),
                                   placeholder=t("login.manual.placeholder"),
                                   multiline=True)
        if text:
            self._auth.login_with_text(text, self._on_manual_result)

    def _on_manual_result(self, ok, error):
        if ok:
            self.login_success.emit()
        else:
            dialogs.notify(self, t("login.error.title"), t("login.error.message", error=error))

    @staticmethod
    def _make_button(text, kind):
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet(theme.button_qss(kind))
        return button
