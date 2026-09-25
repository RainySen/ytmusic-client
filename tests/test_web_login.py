import pytest
from PySide6.QtCore import QUrl
from PySide6.QtNetwork import QNetworkCookie
from PySide6.QtTest import QSignalSpy, QTest

from infra.concurrency import TaskRunner
from infra.session_import import NO_SESSION, SessionImportError, cookies_to_headers
from infra.web_session import (
    ENGINE_FLAGS_VAR, NO_CLIENT_HINTS, WebSessionCookies, configure_web_engine_environment, firefox_disguise_script,
    google_login_user_agent,
)
from services.auth_service import AuthService
from ui.login_window import WEB_LOGIN_AVAILABLE, LoginWindow

needs_webengine = pytest.mark.skipif(not WEB_LOGIN_AVAILABLE, reason="QtWebEngine not installed")


def test_only_youtube_cookies_are_kept():
    cookies = WebSessionCookies()
    cookies.add(".youtube.com", "SID", "1")
    cookies.add("music.youtube.com", "YSC", "2")
    cookies.add("youtube.com", "PREF", "3")
    cookies.add(".google.com", "NID", "google")
    cookies.add(".notyoutube.com", "evil", "x")
    cookies.add("youtube.com.example.org", "evil2", "x")
    assert cookies.snapshot() == {"SID": "1", "YSC": "2", "PREF": "3"}


def test_session_needs_the_signing_cookie():
    cookies = WebSessionCookies()
    cookies.add(".youtube.com", "SID", "1")
    assert not cookies.has_session()
    cookies.add(".youtube.com", "SAPISID", "k")
    assert cookies.has_session()
    plain = WebSessionCookies()
    plain.add(".youtube.com", "__Secure-3PAPISID", "k")
    assert plain.has_session()
    plain.add(".google.com", "SAPISID", "other")
    other = WebSessionCookies()
    other.add(".google.com", "SAPISID", "k")
    assert not other.has_session()


def test_removed_cookies_disappear_and_snapshots_are_copies():
    cookies = WebSessionCookies()
    cookies.add(".youtube.com", "SAPISID", "k")
    copy = cookies.snapshot()
    copy["injected"] = "x"
    assert "injected" not in cookies.snapshot()
    cookies.remove(".youtube.com", "SAPISID")
    cookies.remove(".google.com", "SAPISID")
    cookies.remove(".youtube.com", "never-there")
    assert not cookies.has_session()


def test_login_user_agent_is_firefox_for_every_platform():
    windows = google_login_user_agent("win32")
    assert windows == "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0"
    assert "Macintosh" in google_login_user_agent("darwin") and "X11; Linux" in google_login_user_agent("linux2")
    assert google_login_user_agent("freebsd") == windows
    for agent in (windows, google_login_user_agent("darwin"), google_login_user_agent("linux")):
        assert "Chrome" not in agent and "QtWebEngine" not in agent and "Gecko/20100101 Firefox/" in agent


def test_disguise_script_hides_chromium_traits_matching_the_platform():
    windows = firefox_disguise_script("win32")
    for trait in ("userAgentData", "'vendor', ''", "productSub", "buildID", "webdriver", "window, 'chrome'", "window, 'PublicKeyCredential'"):
        assert trait in windows
    assert "'oscpu', 'Windows NT 10.0; Win64; x64'" in windows and "'platform', 'Win32'" in windows
    assert "'platform', 'MacIntel'" in firefox_disguise_script("darwin")
    assert "'oscpu', 'Linux x86_64'" in firefox_disguise_script("linux")


def test_client_hints_are_disabled_once_and_existing_flags_are_kept():
    environ = {}
    configure_web_engine_environment(environ)
    assert environ[ENGINE_FLAGS_VAR] == NO_CLIENT_HINTS
    configure_web_engine_environment(environ)
    assert environ[ENGINE_FLAGS_VAR] == NO_CLIENT_HINTS
    other = {ENGINE_FLAGS_VAR: "--disable-gpu"}
    configure_web_engine_environment(other)
    assert other[ENGINE_FLAGS_VAR] == "--disable-gpu " + NO_CLIENT_HINTS


def test_cookie_map_becomes_headers_with_the_browsers_identity():
    headers = cookies_to_headers({"SID": "1", "SAPISID": "k"}, user_agent="UA/1", authuser="2")
    assert headers["user-agent"] == "UA/1" and headers["x-goog-authuser"] == "2"
    assert headers["cookie"] == "SID=1; SAPISID=k" and headers["authorization"].startswith("SAPISIDHASH ")
    with pytest.raises(SessionImportError) as error:
        cookies_to_headers({"SID": "1"})
    assert str(error.value) == NO_SESSION


class FakeGateway:
    def __init__(self):
        self.received = []
        self.is_authenticated = False

    def authenticate(self, headers):
        self.received.append(headers)


def test_auth_service_signs_in_with_a_web_session(qapp, wait_until):
    runner = TaskRunner("web-auth", 2)
    gateway = FakeGateway()
    service = AuthService(gateway, runner)
    seen = []
    service.login_with_web_session({"SID": "1", "__Secure-3PAPISID": "k"}, "UA/2", lambda ok, error: seen.append((ok, error)))
    assert wait_until(lambda: seen)
    assert seen == [(True, "")] and gateway.received[0]["user-agent"] == "UA/2"
    bad = []
    service.login_with_web_session({"SID": "1"}, "UA/2", lambda ok, error: bad.append((ok, error)))
    assert wait_until(lambda: bad)
    assert bad == [(False, NO_SESSION)] and len(gateway.received) == 1
    runner.shutdown()


def cookie(domain, name, value):
    made = QNetworkCookie(name.encode(), value.encode())
    made.setDomain(domain)
    return made


@pytest.fixture
def web(qapp):
    if not WEB_LOGIN_AVAILABLE:
        pytest.skip("QtWebEngine not installed")
    from ui.web_login_window import WebLoginWindow

    window = WebLoginWindow()
    yield window
    window.close()
    QTest.qWait(200)


@needs_webengine
def test_window_captures_the_session_once_signed_in_on_music(web):
    spy = QSignalSpy(web.session_captured)
    web._on_url(QUrl("https://accounts.google.com/v3/signin/identifier"))
    web._on_cookie_added(cookie(".youtube.com", "SAPISID", "k"))
    QTest.qWait(1500)
    assert spy.count() == 0
    web._on_cookie_added(cookie(".google.com", "NID", "n"))
    web._on_url(QUrl("https://music.youtube.com/"))
    QTest.qWait(1600)
    assert spy.count() == 1
    captured, user_agent = spy.at(0)
    assert captured == {"SAPISID": "k"} and user_agent == google_login_user_agent()
    assert web._done and not web.isVisible()


@needs_webengine
def test_window_waits_for_the_signing_cookie_and_reports_it_only_once(web):
    spy = QSignalSpy(web.session_captured)
    web._on_url(QUrl("https://music.youtube.com/"))
    web._on_cookie_added(cookie(".youtube.com", "SID", "1"))
    QTest.qWait(1600)
    assert spy.count() == 0
    web._on_cookie_added(cookie(".youtube.com", "__Secure-3PAPISID", "k"))
    QTest.qWait(1600)
    assert spy.count() == 1
    web._on_cookie_added(cookie(".youtube.com", "extra", "x"))
    web._finish_if_ready()
    assert spy.count() == 1


@needs_webengine
def test_window_ignores_a_removed_session_and_closing_reports_it(web):
    captured, closed = QSignalSpy(web.session_captured), QSignalSpy(web.closed)
    web._on_cookie_added(cookie(".youtube.com", "SAPISID", "k"))
    web._on_cookie_removed(cookie(".youtube.com", "SAPISID", "k"))
    web._on_url(QUrl("https://music.youtube.com/"))
    QTest.qWait(1600)
    assert captured.count() == 0
    web.show()
    web.close()
    assert closed.count() == 1 and captured.count() == 0
    web.close()
    assert web._disposed


@needs_webengine
def test_window_uses_a_firefox_agent_and_the_disguise_on_the_google_login_page(web):
    from ui.web_login_window import DISGUISE_SCRIPT_NAME, LOGIN_URL

    assert web._user_agent == google_login_user_agent()
    assert web._profile.httpUserAgent() == web._user_agent
    assert web._profile.httpAcceptLanguage().startswith("es")
    scripts = web._profile.scripts().find(DISGUISE_SCRIPT_NAME)
    assert len(scripts) == 1 and scripts[0].sourceCode() == firefox_disguise_script()
    assert scripts[0].runsOnSubFrames() and LOGIN_URL.startswith("https://accounts.google.com/ServiceLogin")


class FakeAuth:
    is_authenticated = False

    def __init__(self):
        self.web_calls = []

    def login_with_web_session(self, cookies, user_agent, on_done):
        self.web_calls.append((cookies, user_agent))
        self.on_done = on_done


@needs_webengine
def test_login_screen_offers_google_first_and_finishes_through_the_auth_service(qapp):
    auth = FakeAuth()
    window = LoginWindow(auth, qapp.windowIcon())
    window.show()
    assert window._web_button.text() == "Iniciar sesión con Google"
    success = QSignalSpy(window.login_success)
    window._on_web_session({"SAPISID": "k"}, "UA/3")
    assert auth.web_calls == [({"SAPISID": "k"}, "UA/3")]
    assert not window._web_button.isEnabled() and window._web_button.text() == "Iniciando sesión…"
    auth.on_done(True, "")
    assert success.count() == 1 and window._web_button.isEnabled()
    window.close()


@needs_webengine
def test_login_screen_reports_a_failed_web_login_and_can_retry(qapp, monkeypatch):
    from ui.components import dialogs

    shown = []
    monkeypatch.setattr(dialogs, "notify", lambda parent, title, message: shown.append(message))
    auth = FakeAuth()
    window = LoginWindow(auth, qapp.windowIcon())
    window.show()
    window._on_web_session({"SAPISID": "k"}, "UA")
    auth.on_done(False, "sesión rechazada")
    assert shown and "sesión rechazada" in shown[0]
    assert window._web_button.isEnabled() and window._web is None
    window.close()


@needs_webengine
def test_web_window_is_reused_while_open_and_forgotten_when_closed(qapp, monkeypatch):
    import ui.web_login_window as module

    created = []

    class FakeWeb:
        def __init__(self):
            from PySide6.QtCore import QObject, Signal

            class Signals(QObject):
                session_captured = Signal(dict, str)
                closed = Signal()

            self.signals = Signals()
            self.session_captured = self.signals.session_captured
            self.closed = self.signals.closed
            self.started = 0
            self.raised = 0
            created.append(self)

        def start(self):
            self.started += 1

        def show(self):
            pass

        def raise_(self):
            self.raised += 1

        def activateWindow(self):
            pass

    monkeypatch.setattr(module, "WebLoginWindow", FakeWeb)
    window = LoginWindow(FakeAuth(), qapp.windowIcon())
    window._login_with_web()
    window._login_with_web()
    assert len(created) == 1 and created[0].started == 1 and created[0].raised == 1
    created[0].closed.emit()
    window._login_with_web()
    assert len(created) == 2
    window.close()
