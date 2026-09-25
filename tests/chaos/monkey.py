from __future__ import annotations

import random
import time

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QDialog, QLineEdit, QMenu, QPlainTextEdit, QPushButton, QScrollArea, QSlider,
    QWidget,
)

from tests.chaos.payloads import WEIRD_STRINGS
from tests.chaos.world import World
from ui.components.clickable import ClickableWidget

SEARCHES = ("daft punk", "  ", "a", "🎵", "x" * 300, "Bad Bunny", "%s", "日本語", "", "the weeknd blinding lights", "‮abc")
PASTES = ("", "curl 'https://music.youtube.com/youtubei/v1/browse' -H 'cookie: SAPISID=abc; __Secure-3PAPISID=abc'",
          "not a curl at all", "\x00\x01\x02", "SAPISID=1", "{}", "[", "cookie: " + "a=b; " * 500, "https://music.youtube.com/playlist?list=PL1",
          "https://music.youtube.com/playlist?list=" + "x" * 500, "javascript:alert(1)", "🎵" * 100)
KEYS = (Qt.Key_Space, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up,
        Qt.Key_Down, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End, Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_A, Qt.Key_F5)


class Monkey:
    def __init__(self, world: World, seed: int, only: str = ""):
        self.world = world
        self.rng = random.Random(seed * 7919 + 13)
        self.window = world.ui.window
        self.recorder = world.recorder
        self.audio = world.services.audio
        self._resolver = QTimer()
        self._resolver.setInterval(15)
        self._resolver.timeout.connect(self._resolve_modal)
        self._resolver.start()
        self.actions = [
            (6, self.navigate), (5, self.search), (12, self.click_card), (6, self.click_button), (4, self.player),
            (3, self.audio_event), (2, self.resize), (2, self.toggle_now_playing), (3, self.side_tab), (3, self.keyboard),
            (3, self.scroll), (5, self.wait), (1, self.tray_cycle), (2, self.queue_ops), (1, self.connectivity),
            (2, self.right_click), (2, self.hover), (1, self.login_paste), (1, self.session_events),
        ]
        if only:
            names = set(only.split(","))
            self.actions = [(w, a) for w, a in self.actions if a.__name__ in names]
        self._weights = [weight for weight, _ in self.actions]
        self.counts: dict[str, int] = {}

    def run(self, steps: int, step_limit_s: float = 4.0) -> None:
        for _ in range(steps):
            _, action = self.rng.choices(self.actions, weights=self._weights)[0]
            self.recorder.note(action.__name__)
            self.counts[action.__name__] = self.counts.get(action.__name__, 0) + 1
            started = time.time()
            try:
                action()
            except RuntimeError as exc:
                if "already deleted" not in str(exc):
                    self._driver_problem(action, exc)
            except Exception as exc:
                self._driver_problem(action, exc)
            QApplication.processEvents()
            elapsed = time.time() - started
            if elapsed > step_limit_s:
                self.recorder.report("slow step", f"{action.__name__} took {elapsed:.1f}s")
        self._resolver.stop()

    def _driver_problem(self, action, exc) -> None:
        import traceback
        self.recorder.report("driver exception", f"{action.__name__}: {''.join(traceback.format_exception(exc))}")

    # dialogos menus modales
    def _resolve_modal(self) -> None:
        widget = QApplication.activePopupWidget()
        if isinstance(widget, QMenu):
            actions = [a for a in widget.actions() if a.isEnabled() and not a.isSeparator()]
            if actions and self.rng.random() < 0.7:
                actions[self.rng.randrange(len(actions))].trigger()
            widget.close()
            return
        modal = QApplication.activeModalWidget()
        if modal is None:
            return
        for field in modal.findChildren(QLineEdit):
            field.setText(self.rng.choice(PASTES + WEIRD_STRINGS))
        for field in modal.findChildren(QPlainTextEdit):
            field.setPlainText(self.rng.choice(PASTES + WEIRD_STRINGS))
        buttons = [b for b in modal.findChildren(QPushButton) if b.isVisible() and b.isEnabled()]
        for clickable in modal.findChildren(ClickableWidget):
            if clickable.isVisible() and self.rng.random() < 0.4:
                clickable.activated.emit()
                if not modal.isVisible():
                    return
        if buttons and self.rng.random() < 0.85:
            self.rng.choice(buttons).click()
        elif isinstance(modal, QDialog):
            modal.reject()

    def _visible(self, kind) -> list:
        return [w for w in self.window.findChildren(kind) if w.isVisible() and w.isEnabled()]

    def navigate(self) -> None:
        self.rng.choice((self.window.home_requested, self.window.explore_requested, self.window.library_requested)).emit()

    def search(self) -> None:
        box = self.window.top_bar.search_box
        box.setText(self.rng.choice(SEARCHES))
        if self.rng.random() < 0.8:
            self.window._submit_search()
        else:
            QTest.keyClick(box, Qt.Key_Return)

    def click_card(self) -> None:
        cards = self._visible(ClickableWidget)
        if cards:
            card = self.rng.choice(cards)
            if self.rng.random() < 0.5:
                QTest.mouseClick(card, Qt.LeftButton, Qt.NoModifier, card.rect().center())
            else:
                card.activated.emit()

    def click_button(self) -> None:
        buttons = [b for b in self._visible(QAbstractButton) if b.width() > 0]
        if buttons:
            self.rng.choice(buttons).click()

    def player(self) -> None:
        window, panel = self.window, self.window.player_panel
        choice = self.rng.choice(("play", "next", "prev", "loop", "shuffle", "seek", "volume", "spam"))
        if choice == "play":
            window.play_pause_clicked.emit()
        elif choice == "next":
            window.next_clicked.emit()
        elif choice == "prev":
            window.previous_clicked.emit()
        elif choice == "loop":
            window.loop_clicked.emit()
        elif choice == "shuffle":
            window.shuffle_clicked.emit()
        elif choice == "seek":
            window.seek_requested.emit(self.rng.choice((0.0, 1.0, 0.5, -1.0, 2.0, self.rng.random())))
        elif choice == "volume":
            panel.volume_slider.setValue(self.rng.choice((0, 100, self.rng.randrange(101))))
        else:
            signal = self.rng.choice((window.next_clicked, window.previous_clicked, window.play_pause_clicked))
            for _ in range(self.rng.randrange(5, 40)):
                signal.emit()

    def audio_event(self) -> None:
        audio = self.audio
        choice = self.rng.choice(("finished", "failed", "time", "position", "finished"))
        if choice == "finished":
            audio.finished.emit()
        elif choice == "failed":
            audio.failed.emit()
        elif choice == "time":
            total = self.rng.choice((0, 10, 240, 100000))
            audio.time_changed.emit(self.rng.randrange(0, total + 5), total)
            audio.time_ms_changed.emit(self.rng.randrange(0, 300000))
        else:
            audio.position_changed.emit(self.rng.choice((0.0, 0.5, 1.0, self.rng.random())))

    def resize(self) -> None:
        width = self.rng.choice((200, 400, 640, 900, 1240, 1920, 3000))
        height = self.rng.choice((150, 300, 500, 750, 1080, 1600))
        self.window.resize(width, height)

    def toggle_now_playing(self) -> None:
        self.window.toggle_now_playing()

    def side_tab(self) -> None:
        panel = self.window.side_panel
        buttons = panel.findChildren(QPushButton)
        tabs = [b for b in buttons if b.isCheckable()]
        if tabs:
            self.rng.choice(tabs).click()

    def keyboard(self) -> None:
        target = QApplication.focusWidget() or self.window
        for _ in range(self.rng.randrange(1, 6)):
            key = self.rng.choice(KEYS)
            if key == Qt.Key_Escape and self.rng.random() < 0.5:
                continue
            QTest.keyClick(target, key)

    def scroll(self) -> None:
        areas = [a for a in self._visible(QScrollArea)]
        if areas:
            bar = self.rng.choice(areas).verticalScrollBar()
            bar.setValue(self.rng.choice((bar.minimum(), bar.maximum(), self.rng.randrange(bar.minimum(), bar.maximum() + 1))))

    def wait(self) -> None:
        QTest.qWait(self.rng.choice((1, 5, 20, 60, 150)))

    def tray_cycle(self) -> None:
        self.window.close()
        QTest.qWait(20)
        self.window.showNormal()

    def queue_ops(self) -> None:
        panel = self.window.side_panel
        size = 40
        pick = lambda: self.rng.choice((0, 1, 2, self.rng.randrange(size), size + 5, -1))
        choice = self.rng.choice(("activate", "remove", "move"))
        if choice == "activate":
            panel.queue_item_activated.emit(pick())
        elif choice == "remove":
            panel.queue_item_removed.emit(pick())
        else:
            panel.queue_item_moved.emit(pick(), pick())

    def connectivity(self) -> None:
        self.world.offline = self.rng.random() < 0.4

    def right_click(self) -> None:
        cards = self._visible(ClickableWidget)
        if cards:
            card = self.rng.choice(cards)
            card.context_requested.emit(card.mapToGlobal(QPoint(5, 5)))

    def hover(self) -> None:
        cards = self._visible(ClickableWidget)
        if cards:
            card = self.rng.choice(cards)
            QApplication.sendEvent(card, QEvent(QEvent.Enter))
            QTest.qWait(self.rng.choice((1, 30, 400)))
            QApplication.sendEvent(card, QEvent(QEvent.Leave))

    def login_paste(self) -> None:
        self.window.login_requested.emit()

    def session_events(self) -> None:
        auth = self.world.services.auth
        choice = self.rng.choice(("expired", "changed", "verify", "logout"))
        if choice == "expired":
            auth.session_expired.emit()
        elif choice == "changed":
            auth.auth_changed.emit(self.rng.random() < 0.5)
        elif choice == "verify":
            auth.verify_session()
        else:
            self.window.logout_requested.emit()


def drain(world: World, ms: int = 300) -> None:
    QTest.qWait(ms)
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, QSlider):
            continue
        if isinstance(widget, QWidget) and widget is not world.ui.window and widget.isVisible() and isinstance(widget, QDialog):
            widget.reject()
