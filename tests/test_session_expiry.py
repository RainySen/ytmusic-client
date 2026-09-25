import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTest import QSignalSpy

from infra.concurrency import TaskRunner
from infra.ytmusic_gateway import SessionRejected, YTMusicGateway, looks_like_auth_failure
from presenters.auth_presenter import SESSION_CHECK_MS, AuthPresenter
from services.auth_service import AuthService
from tests.test_presenters import Rig


@pytest.mark.parametrize("message, expected", [
    ("Server returned HTTP 401: Unauthorized.\nRequest had invalid authentication credentials", True),
    ("Server returned HTTP 403: Forbidden.", True),
    ("Please provide authentication before using this function", True),
    ("login required", True),
    ("Server returned HTTP 500: Internal Server Error.", False),
    ("Server returned HTTP 429: Too Many Requests", False),
    ("Connection aborted", False),
    ("can only concatenate str (not NoneType) to str", False),
])
def test_auth_failures_are_told_apart_from_other_errors(message, expected):
    assert looks_like_auth_failure(RuntimeError(message)) is expected


class FakeClient:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def get_library_playlists(self, limit=1):
        self.calls += 1
        if self.error:
            raise self.error
        return []


def gateway_with(client, authenticated=True):
    gateway = YTMusicGateway("unused.json")
    gateway._ytm = client
    gateway._authenticated = authenticated
    return gateway


def test_a_working_session_stays_authenticated():
    client = FakeClient()
    gateway = gateway_with(client)
    gateway.verify_session()
    assert client.calls == 1 and gateway.is_authenticated


def test_a_rejected_session_is_marked_as_signed_out():
    gateway = gateway_with(FakeClient(RuntimeError("Server returned HTTP 401: Unauthorized.")))
    with pytest.raises(SessionRejected):
        gateway.verify_session()
    assert not gateway.is_authenticated


def test_network_errors_do_not_sign_the_user_out():
    gateway = gateway_with(FakeClient(ConnectionError("offline")))
    with pytest.raises(ConnectionError):
        gateway.verify_session()
    assert gateway.is_authenticated


class ScriptedGateway:
    def __init__(self, error=None, authenticated=True):
        self.error = error
        self.is_authenticated = authenticated
        self.checks = 0

    def verify_session(self):
        self.checks += 1
        if self.error:
            raise self.error


@pytest.fixture
def service(qapp):
    runner = TaskRunner("expiry", 2)
    yield runner
    runner.shutdown()


def test_service_announces_an_expired_session(service, wait_until):
    gateway = ScriptedGateway(SessionRejected("HTTP 401"))
    auth = AuthService(gateway, service)
    expired, changed = QSignalSpy(auth.session_expired), QSignalSpy(auth.auth_changed)
    auth.verify_session()
    assert wait_until(lambda: expired.count() == 1)
    assert changed.count() == 1 and changed.at(0)[0] is False


def test_service_stays_quiet_when_the_session_is_fine_or_the_network_is_down(service, wait_until):
    fine = AuthService(ScriptedGateway(), service)
    spy = QSignalSpy(fine.session_expired)
    fine.verify_session()
    offline_gateway = ScriptedGateway(ConnectionError("offline"))
    offline = AuthService(offline_gateway, service)
    offline_spy = QSignalSpy(offline.session_expired)
    offline.verify_session()
    assert wait_until(lambda: offline_gateway.checks == 1)
    wait_until(lambda: False, 300)
    assert spy.count() == 0 and offline_spy.count() == 0


def test_service_does_not_check_when_signed_out(service):
    gateway = ScriptedGateway(authenticated=False)
    AuthService(gateway, service).verify_session()
    assert gateway.checks == 0


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


class FakeLogin(QObject):
    login_success = Signal()
    login_skipped = Signal()

    def show(self):
        pass

    def raise_(self):
        pass

    def activateWindow(self):
        pass

    def close(self):
        pass


def make_presenter(rig, monkeypatch, answers):
    class Home:
        def refresh(self, force=False):
            pass

    monkeypatch.setattr(rig.window, "ask_relogin", lambda: answers.pop(0))
    opened = []

    def factory():
        login = FakeLogin()
        opened.append(login)
        return login

    presenter = rig.keep(AuthPresenter(rig.window, rig.auth, rig.catalog, Home(), factory, rig.notifier))
    return presenter, opened


def test_starting_checks_the_session_and_schedules_more_checks(rig, monkeypatch):
    presenter, _ = make_presenter(rig, monkeypatch, [])
    presenter.start()
    assert rig.auth.verifications == 1
    assert presenter._checker.isActive() and presenter._checker.interval() == SESSION_CHECK_MS
    presenter._checker.timeout.emit()
    assert rig.auth.verifications == 2
    presenter._checker.stop()


def test_an_expired_session_offers_to_sign_in_again(rig, monkeypatch):
    presenter, opened = make_presenter(rig, monkeypatch, [True])
    rig.auth.session_expired.emit()
    assert len(opened) == 1
    rig.auth.session_expired.emit()
    assert len(opened) == 1


def test_declining_does_not_nag_until_the_next_login(rig, monkeypatch):
    presenter, opened = make_presenter(rig, monkeypatch, [False, True])
    rig.auth.session_expired.emit()
    rig.auth.session_expired.emit()
    assert opened == [] and presenter._asked
    presenter._reset_asked()
    rig.auth.session_expired.emit()
    assert len(opened) == 1
