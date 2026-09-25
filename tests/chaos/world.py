from __future__ import annotations

import logging
import os
import random
import sys
import threading
import time
import traceback
from contextlib import ExitStack
from unittest import mock

import qtawesome as qta
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from core import bootstrap
from core.config import AppPaths
from domain.models import LyricLine, Lyrics, LyricWord
from domain.stream_cache import StreamInfo
from infra.stream_resolver import StreamResolveError, YtDlpStreamResolver
from infra.thumbnail_cache import ThumbnailCache
from infra.ytmusic_gateway import AuthRequired, GatewayError, SessionRejected, YTMusicGateway
from tests.chaos.payloads import Factory, mutate

log = logging.getLogger("chaos")

ERRORS = (
    lambda: ConnectionError("Network is unreachable"),
    lambda: TimeoutError("timed out"),
    lambda: RuntimeError("Server returned HTTP 500: Internal error"),
    lambda: KeyError("contents"),
    lambda: ValueError("Unexpected response shape"),
    lambda: RuntimeError("Server returned HTTP 401: Unauthorized"),
    lambda: Exception(),
)


class Recorder:
    def __init__(self):
        self.problems: dict[str, str] = {}
        self.history: list[str] = []
        self._lock = threading.Lock()
        self._old_hook = sys.excepthook
        self._old_thread_hook = threading.excepthook
        self._handler = _RecordingHandler(self)

    def install(self) -> None:
        sys.excepthook = self._on_exception
        threading.excepthook = lambda args: self._on_exception(args.exc_type, args.exc_value, args.exc_traceback)
        logging.getLogger().addHandler(self._handler)

    def uninstall(self) -> None:
        sys.excepthook = self._old_hook
        threading.excepthook = self._old_thread_hook
        logging.getLogger().removeHandler(self._handler)

    def note(self, action: str) -> None:
        self.history.append(action)
        del self.history[:-40]

    def report(self, kind: str, detail: str) -> None:
        signature = f"{kind}: {detail.strip().splitlines()[-1] if detail.strip() else ''}"[:300]
        with self._lock:
            if signature not in self.problems:
                self.problems[signature] = "\n".join([kind, detail, "-- last actions --", *self.history[-12:]])
                if os.environ.get("CHAOS_LIVE"):
                    print(f"\n### PROBLEM {signature}\n{self.problems[signature]}\n", file=sys.__stderr__, flush=True)

    def _on_exception(self, exc_type, exc, tb) -> None:
        self.report("exception", "".join(traceback.format_exception(exc_type, exc, tb)))


class _RecordingHandler(logging.Handler):
    def __init__(self, recorder: Recorder):
        super().__init__(level=logging.WARNING)
        self._recorder = recorder

    def emit(self, record: logging.LogRecord) -> None:
        if record.name == "chaos":
            return
        message = record.getMessage()
        if record.name == "qt" and not any(key in message for key in ("QObject::", "QLayout", "QPainter", "QWidget::",
                                                                      "QPixmap", "QFont::setPointSize: Point size <= 0")):
            return
        if record.levelno >= logging.ERROR or record.name == "qt":
            trace = "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else ""
            self._recorder.report(f"log {record.name}", f"{message}\n{trace}")


class ChaosAudio(QObject):
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    time_ms_changed = Signal(int)
    finished = Signal()
    failed = Signal()

    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.is_playing = False
        self.has_media = False
        self.urls: list[str] = []

    def warm_up(self):
        pass

    def play_url(self, url):
        self.urls.append(url)
        self.is_playing = True
        self.has_media = True

    def pause(self):
        self.is_playing = False

    def resume(self):
        self.is_playing = True

    def stop(self):
        self.is_playing = False
        self.has_media = False

    def seek(self, fraction):
        pass

    def set_volume(self, volume):
        pass


class ChaosLyrics:
    name = "Chaos"

    def __init__(self, world):
        self._world = world

    def fetch(self, query):
        rng = self._world._call_rng("lyrics")
        if self._world.offline or rng.random() < self._world.failure_rate:
            raise ConnectionError("lyrics unavailable")
        kind = rng.choice(("none", "plain", "synced", "words", "empty"))
        if kind == "none":
            return None
        texts = [Factory(rng).text("Verso") for _ in range(rng.randrange(0, 80 if kind != "empty" else 1))]
        if kind == "plain" or kind == "empty":
            return Lyrics(tuple(LyricLine(t) for t in texts), synced=False, source=self.name)
        if kind == "synced":
            return Lyrics(tuple(LyricLine(t, i * 3000) for i, t in enumerate(texts)), synced=True, source=self.name)
        lines = []
        for i, text in enumerate(texts):
            words = tuple(LyricWord(w, i * 3000 + j * 400, i * 3000 + j * 400 + 350) for j, w in enumerate(text.split() or [text]))
            lines.append(LyricLine(text, i * 3000, i * 3000 + 2900, words))
        return Lyrics(tuple(lines), synced=True, source=self.name)


class World:
    def __init__(self, tmp_dir: str, seed: int, *, failure_rate: float = 0.08, mutation_rate: float = 0.06,
                 authenticated: bool = True, latency: float = 0.01, wild: bool = False):
        self.seed = seed
        self.rng = random.Random(seed)
        self.failure_rate = failure_rate
        self.mutation_rate = mutation_rate
        self.latency = latency
        self.wild = wild
        self.offline = False
        self.recorder = Recorder()
        self._call_lock = threading.Lock()
        self._calls = 0
        self._stack = ExitStack()
        self.paths = AppPaths(tmp_dir)
        self.paths.ensure_dirs()
        if authenticated:
            with open(self.paths.auth_file, "w", encoding="utf-8") as fh:
                fh.write('{"cookie": "x", "x-goog-authuser": "0"}')
        self.services = None
        self.ui = None

    # llamadas red simuladas
    def _call_rng(self, name: str) -> random.Random:
        with self._call_lock:
            self._calls += 1
            return random.Random(f"{self.seed}:{name}:{self._calls}")

    def _network(self, name: str, make, *, mutate_result: bool = True):
        def call(*_args, **_kwargs):
            rng = self._call_rng(name)
            time.sleep(rng.random() * self.latency)
            if self.offline or rng.random() < self.failure_rate:
                raise rng.choice(ERRORS)()
            data = make(Factory(rng))
            return mutate(data, rng, self.mutation_rate, wild=self.wild) if mutate_result else data
        call.__name__ = name
        return call

    def _gateway_patches(self):
        data = {
            "get_home": lambda f: f.home(), "get_charts": lambda f: f.charts(), "get_explore": lambda f: f.explore(),
            "search": lambda f: f.search(), "get_watch_playlist": lambda f: f.watch(),
            "get_watch_playlist_for": lambda f: f.watch(), "get_playlist": lambda f: f.playlist(),
            "get_playlist_page": lambda f: f.playlist(), "get_related": lambda f: f.related(),
            "get_mood_playlists": lambda f: [f.playlist_card() for _ in range(6)], "get_artist": lambda f: f.artist(),
            "get_album": lambda f: f.album(), "get_lyrics": lambda f: f.lyrics(),
            "get_lyrics_browse_id": lambda f: f._id("MPLY"), "get_library_playlists": lambda f: f.library_playlists(),
            "get_library_songs": lambda f: f.library_songs(), "get_library_artists": lambda f: f.library_artists(),
            "add_playlist_items": lambda f: f.rng.random() < 0.7, "create_playlist": lambda f: f._id("PL"),
        }
        for name, make in data.items():
            yield name, self._network(name, make)

    def start(self, *, start_ui: bool = True):
        self.recorder.install()
        stack = self._stack
        for name, fn in self._gateway_patches():
            stack.enter_context(mock.patch.object(YTMusicGateway, name, fn))
        gateway_state = {"auth": os.path.exists(self.paths.auth_file)}

        def authenticate(_self, headers):
            if self.offline or self.rng.random() < 0.3:
                raise GatewayError("HTTP 401 unauthorized")
            gateway_state["auth"] = True
            with open(self.paths.auth_file, "w", encoding="utf-8") as fh:
                fh.write("{}")

        def logout(_self):
            gateway_state["auth"] = False
            if os.path.exists(self.paths.auth_file):
                os.remove(self.paths.auth_file)

        def verify_session(_self):
            if not gateway_state["auth"]:
                raise AuthRequired("Se requiere iniciar sesión.")
            if self.rng.random() < 0.1:
                raise SessionRejected("HTTP 401")

        stack.enter_context(mock.patch.object(YTMusicGateway, "authenticate", authenticate))
        stack.enter_context(mock.patch.object(YTMusicGateway, "logout", logout))
        stack.enter_context(mock.patch.object(YTMusicGateway, "verify_session", verify_session))
        stack.enter_context(mock.patch.object(YTMusicGateway, "warm_up", lambda _self: None))
        stack.enter_context(mock.patch.object(YTMusicGateway, "is_authenticated",
                                              mock.PropertyMock(side_effect=lambda: gateway_state["auth"])))
        stack.enter_context(mock.patch.object(bootstrap, "VlcAudioBackend", ChaosAudio))
        stack.enter_context(mock.patch.object(YtDlpStreamResolver, "warm_up", lambda _self: None))
        stack.enter_context(mock.patch.object(YtDlpStreamResolver, "resolve", lambda _resolver, video_id: self._resolve(video_id)))
        stack.enter_context(mock.patch.object(ThumbnailCache, "request", lambda _cache, url, callback: self._thumbnail(url, callback)))
        stack.enter_context(mock.patch.object(bootstrap, "build_lyrics_providers", lambda paths, gateway: [ChaosLyrics(self)]))
        import ui.login_window as login_window
        stack.enter_context(mock.patch.object(login_window, "WEB_LOGIN_AVAILABLE", False))

        self.services = bootstrap.build_services(self.paths)
        if start_ui:
            self.ui = bootstrap.build_ui(self.services, qta.icon("fa5s.music"))
            self.ui.start(self.services)
            self.ui.window.resize(1240, 750)
            self.ui.window.show()
        return self

    def _resolve(self, video_id: str) -> StreamInfo:
        rng = self._call_rng("resolve")
        time.sleep(rng.random() * self.latency)
        if self.offline or rng.random() < self.failure_rate * 1.5:
            raise StreamResolveError(rng.choice(("Video unavailable", "Sign in to confirm your age", "HTTP Error 403")))
        return StreamInfo(video_id, f"http://stream.invalid/{video_id}", f"title-{video_id}", time.time() + rng.choice((20, 3600)))

    def _thumbnail(self, url: str, callback) -> None:
        rng = self._call_rng("thumb")
        if not url or rng.random() < 0.2:
            return
        mode = os.environ.get("CHAOS_THUMBS", "async")
        if mode == "none":
            return
        size = rng.choice((0, 1, 60, 226, 544, 3000))
        pixmap = QPixmap(max(size, 1), max(size, 1)) if size else QPixmap()
        pixmap.fill(QColor(rng.randrange(256), rng.randrange(256), rng.randrange(256)))
        if mode == "sync":
            callback(pixmap)
        else:
            QTimer.singleShot(rng.randrange(0, 40), lambda: ThumbnailCache._invoke(callback, pixmap))

    def stop(self) -> None:
        try:
            if self.ui is not None:
                self.ui.window.hide()
                self.ui.window.deleteLater()
            if self.services is not None:
                self.services.shutdown()
        finally:
            for widget in QApplication.topLevelWidgets():
                if widget is not None and widget.isVisible():
                    widget.close()
            QApplication.processEvents()
            self._stack.close()
            self.recorder.uninstall()
