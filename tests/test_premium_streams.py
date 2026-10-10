import json

import pytest

from infra import stream_resolver
from infra.account_only_tracks import AccountOnlyTracks
from infra.stream_resolver import (NO_RUNTIME_MESSAGE, NO_SESSION_MESSAGE, StreamResolveError, YtDlpStreamResolver,
                                   needs_account, session_cookies)

PREMIUM = Exception("ERROR: [youtube] x: This video is only available to Music Premium members")


class FakeYdl:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def extract_info(self, url, download=False):
        self.calls.append(url)
        if self.error:
            raise self.error
        return {"url": "https://audio.example/stream?expire=9999999999", "title": "T"}


def make(tmp_path, cookie="SID=abc; __Secure-3PSID=def", remembered=None):
    auth = tmp_path / "oauth.json"
    if cookie is not None:
        auth.write_text(json.dumps({"cookie": cookie}), encoding="utf-8")
    resolver = YtDlpStreamResolver(str(tmp_path / "cache"), auth_file=str(auth), account_only=remembered)
    anonymous, session, used = FakeYdl(PREMIUM), FakeYdl(), []
    resolver._ydl = lambda: anonymous

    def session_ydl(header):
        used.append(header)
        return session

    resolver._session_ydl = session_ydl
    return resolver, anonymous, session, used


def test_premium_songs_retry_with_the_session_and_remember_it(tmp_path):
    resolver, anonymous, session, used = make(tmp_path)
    assert resolver.resolve("vp").url.startswith("https://audio.example")
    assert len(anonymous.calls) == 1 and len(session.calls) == 1 and used == ["SID=abc; __Secure-3PSID=def"]
    resolver.resolve("vp")
    assert len(anonymous.calls) == 1 and len(session.calls) == 2


def test_remembered_premium_tracks_survive_a_restart_and_skip_the_doomed_attempt(tmp_path):
    store = tmp_path / "cache" / "account_only.json"
    resolver, anonymous, session, _ = make(tmp_path, remembered=AccountOnlyTracks(str(store)))
    resolver.resolve("vp")
    assert len(anonymous.calls) == 1 and json.loads(store.read_text(encoding="utf-8")) == ["vp"]

    after_restart, anonymous2, session2, _ = make(tmp_path, remembered=AccountOnlyTracks(str(store)))
    after_restart.resolve("vp")
    assert anonymous2.calls == [] and len(session2.calls) == 1


def test_the_remembered_list_is_capped_and_ignores_a_damaged_file(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert "vp" not in AccountOnlyTracks(str(path))
    small = AccountOnlyTracks(str(tmp_path / "small.json"), limit=2)
    for vid in ("a", "b", "c"):
        small.add(vid)
    small.add("c")
    assert json.loads((tmp_path / "small.json").read_text(encoding="utf-8")) == ["c", "b"]
    assert "a" not in small and "c" in small


def test_other_errors_and_missing_sessions_do_not_use_the_account(tmp_path):
    resolver, anonymous, session, used = make(tmp_path)
    anonymous.error = Exception("ERROR: Video unavailable")
    with pytest.raises(StreamResolveError, match="Video unavailable"):
        resolver.resolve("gone")
    assert session.calls == [] and used == []
    other = tmp_path / "logged_out"
    other.mkdir()
    logged_out, *_ = make(other, cookie=None)
    with pytest.raises(StreamResolveError, match="Inicia sesión"):
        logged_out.resolve("vp")
    assert NO_SESSION_MESSAGE.startswith("Esta canción es solo para YouTube Music Premium")


def test_without_a_js_runtime_the_message_says_what_to_install(tmp_path, monkeypatch):
    monkeypatch.setattr(stream_resolver, "available_js_runtimes", lambda: {})
    resolver = YtDlpStreamResolver(str(tmp_path), auth_file=None)
    with pytest.raises(StreamResolveError) as caught:
        resolver._session_ydl("SID=1")
    assert str(caught.value) == NO_RUNTIME_MESSAGE


def test_account_markers_and_cookie_parsing():
    assert needs_account(PREMIUM) and needs_account(Exception("Sign in to confirm your age"))
    assert not needs_account(Exception("Video unavailable"))
    cookies = session_cookies("SID=a=b; broken; HSID=c", now=0)
    assert [(c.name, c.value, c.domain, c.secure) for c in cookies] == [
        ("SID", "a=b", ".youtube.com", True), ("HSID", "c", ".youtube.com", True)]
