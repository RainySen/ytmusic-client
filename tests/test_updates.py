import re

import pytest
import requests

from core.config import app_version
from domain.settings import Settings
from domain.versions import is_newer
from infra.concurrency import TaskRunner
from infra.settings_repository import SettingsRepository
from presenters.update_presenter import UpdatePresenter
from services import update_service
from services.settings_service import SettingsService
from services.update_service import RELEASES_URL, UpdateService
from tests.test_presenters import Rig


@pytest.mark.parametrize("latest, current, expected", [
    ("v1.5.0", "1.4.0", True),
    ("v.1.10.0", "1.9.3", True),
    ("1.4.1", "1.4", True),
    ("v1.4.0", "1.4.0", False),
    ("1.4", "1.4.0", False),
    ("v1.3.9", "1.4.0", False),
    ("v1.5.0", "", False),
    ("", "1.4.0", False),
])
def test_versions_compare_numerically(latest, current, expected):
    assert is_newer(latest, current) is expected


def test_the_installed_version_comes_from_version_info():
    assert re.fullmatch(r"\d+(\.\d+)+", app_version())


def test_the_announced_version_is_remembered():
    assert Settings().announced_version == ""
    assert Settings.from_dict({"announced_version": "1.5.0"}).announced_version == "1.5.0"
    assert Settings.from_dict({"announced_version": 5}).announced_version == ""


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


@pytest.fixture
def updates(qapp, tmp_path, monkeypatch):
    runner = TaskRunner("updates", 1)
    settings = SettingsService(SettingsRepository(str(tmp_path / "settings.json")))
    release = {"tag_name": "v1.5.0", "html_url": "https://github.com/RainySen/ytmusic-client/releases/tag/v1.5.0"}
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if isinstance(release, Exception):
            raise release
        return FakeResponse(release)

    monkeypatch.setattr(update_service.requests, "get", fake_get)
    service = UpdateService(runner, settings, "1.4.0")
    yield service, settings, release, calls
    runner.shutdown()


def check(service, wait_until):
    found = []
    service.check(lambda version, url: found.append((version, url)))
    wait_until(lambda: False, 200)
    return found


def test_a_newer_release_is_announced_once(updates, wait_until):
    service, settings, release, calls = updates
    assert check(service, wait_until) == [("1.5.0", release["html_url"])]
    assert calls == [RELEASES_URL]
    service.dismiss("1.5.0")
    assert settings.settings.announced_version == "1.5.0"
    assert check(service, wait_until) == []


def test_no_notice_for_the_same_version_or_a_network_error(updates, wait_until, monkeypatch):
    service, _settings, release, _calls = updates
    release["tag_name"] = "v1.4.0"
    assert check(service, wait_until) == []

    def offline(url, **kwargs):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(update_service.requests, "get", offline)
    assert check(service, wait_until) == []


class FakeUpdates:
    def __init__(self):
        self.dismissed = []
        self.pending = None

    def check(self, on_available):
        self.pending = on_available

    def dismiss(self, version):
        self.dismissed.append(version)


@pytest.fixture
def rig(qapp):
    r = Rig()
    yield r
    r.dispose()


def test_banner_offers_the_release_and_never_forces_it(rig):
    updates, opened = FakeUpdates(), []
    presenter = rig.keep(UpdatePresenter(rig.window, updates, open_url=opened.append, delay_ms=0))
    presenter.check_now()
    banner = rig.window.update_banner
    assert banner.isHidden()

    updates.pending("1.5.0", "https://example/r")
    assert not banner.isHidden() and "1.5.0" in banner.text()
    banner.open_button.click()
    assert opened == ["https://example/r"] and updates.dismissed == ["1.5.0"] and banner.isHidden()

    updates.pending("1.6.0", "https://example/r2")
    banner.close_button.click()
    assert updates.dismissed == ["1.5.0", "1.6.0"] and banner.isHidden() and opened == ["https://example/r"]
