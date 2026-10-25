from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from core.i18n import t
from domain.settings import (
    APP_LANGUAGES, CONTENT_LANGUAGES, FREE_MEMORY_OPTIONS, LYRICS_PROVIDER_NAMES, RADIO_SIZE_OPTIONS, REWIND_OPTIONS, Settings,
    THUMBNAIL_CACHE_OPTIONS, THUMBNAIL_QUALITY_OPTIONS,
)
from ui import theme
from ui.components import dialogs
from ui.components.dialogs import Modal
from ui.components.icon_button import icon_button
from ui.components.no_scroll_combo import NoScrollComboBox
from ui.components.switch import Switch

PROVIDER_LABELS = {"betterlyrics": "Better Lyrics", "lrclib": "LRCLIB", "youtube": "YouTube Music"}
APP_LANGUAGE_NAMES = {"es": "Español", "en": "English", "pt": "Português"}


# built on use: the language is only known after startup
def _radio_labels() -> dict:
    labels = {size: t("settings.radio.option", n=size) for size in RADIO_SIZE_OPTIONS}
    labels[0] = t("settings.radio.unlimited")
    return labels


def _rewind_labels() -> dict:
    return {seconds: t("settings.rewind.option", n=seconds) for seconds in REWIND_OPTIONS}


def _memory_labels() -> dict:
    return {10: t("settings.memory.seconds_10"), 20: t("settings.memory.seconds_20"),
            60: t("settings.memory.minute_1"), 180: t("settings.memory.minutes_3")}


def _quality_labels() -> dict:
    return {"low": t("settings.quality.low"), "auto": t("settings.quality.auto"), "high": t("settings.quality.high")}


def _cache_limit_labels() -> dict:
    return {100: t("settings.cache_limit.low"), 200: "200", 400: t("settings.cache_limit.recommended"),
            800: t("settings.cache_limit.high")}


def _app_language_labels() -> dict:
    return {"": t("settings.language.automatic"), **APP_LANGUAGE_NAMES}

_COMBO_QSS = f"""
    QComboBox {{ background: rgba(255,255,255,0.08); color: {theme.TEXT}; border: 1px solid {theme.BORDER};
                 border-radius: 8px; padding: 6px 12px; min-width: 190px; font-size: 13px; }}
    QComboBox:hover {{ border-color: rgba(255,255,255,0.4); }}
    QComboBox QAbstractItemView {{ background: {theme.SURFACE_RAISED}; color: {theme.TEXT}; border: 1px solid {theme.BORDER};
                                   selection-background-color: rgba(255,255,255,0.14); outline: none; }}
"""


# always visible and easy to grab: usable without a mouse wheel
_SCROLL_QSS = """
    QScrollArea { background: transparent; border: none; }
    QScrollBar:vertical { background: rgba(255,255,255,0.06); width: 12px; margin: 2px; border-radius: 5px; }
    QScrollBar::handle:vertical { background: rgba(255,255,255,0.45); border-radius: 5px; min-height: 40px; }
    QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.65); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
DIALOG_HEIGHT = 560
SCREEN_MARGIN = 0.85


def format_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{max(0, size) // 1024} KB"
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} MB".replace(".", t("format.decimal"))
    return f"{size / 1024 ** 3:.2f} GB".replace(".", t("format.decimal"))


def _dialog_height() -> int:
    screen = QApplication.primaryScreen()
    if screen is None:
        return DIALOG_HEIGHT
    return max(320, min(DIALOG_HEIGHT, int(screen.availableGeometry().height() * SCREEN_MARGIN)))


def _title(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1px; "
                        f"padding-top: 10px; background: transparent;")
    return label


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
    return label


def _row(title: str, hint: str, control: QWidget, enabled: bool = True) -> QWidget:
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 2, 0, 2)
    layout.setSpacing(3)
    line = QHBoxLayout()
    label = QLabel(title)
    label.setStyleSheet(f"color: {theme.TEXT if enabled else theme.TEXT_MUTED}; font-size: 14px; font-weight: 600; "
                        f"background: transparent;")
    line.addWidget(label, 1)
    line.addWidget(control)
    layout.addLayout(line)
    if hint:
        note = QLabel(hint)
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        layout.addWidget(note)
    return holder


def _combo(options, labels, current) -> NoScrollComboBox:
    box = NoScrollComboBox()
    box.setStyleSheet(_COMBO_QSS)
    for option in options:
        box.addItem(labels[option], option)
    box.setCurrentIndex(max(0, box.findData(current)))
    return box


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"color: {theme.BORDER}; background: {theme.BORDER}; max-height: 1px;")
    return line


class SettingsDialog(Modal):
    def __init__(self, parent, settings: Settings, tray_available: bool, on_change, on_free=None, *,
                 cache_size=None, clear_cache=None, logged_in: bool = False, on_account=None,
                 autostart_available: bool = True, on_open_log=None, on_restart=None):
        super().__init__(parent, t("settings.title"), width=540, height=_dialog_height())
        self._on_change = on_change
        self._on_free = on_free
        self._cache_size = cache_size
        self._clear_cache = clear_cache
        self._on_account = on_account
        self._on_open_log = on_open_log
        self._on_restart = on_restart
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 8, 0)
        body.setSpacing(4)

        self._build_background(body, settings, tray_available, autostart_available)
        self._build_radio(body, settings)
        self._build_memory(body, settings)
        self._build_playback(body, settings)
        self._build_language(body, settings)
        self._build_thumbnails(body, settings)
        self._build_lyrics(body, settings)
        self._build_cache(body)
        self._build_account(body, logged_in)
        body.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setStyleSheet(_SCROLL_QSS)
        scroll.setWidget(content)
        self.body.addWidget(scroll)
        self.add_button(t("settings.done"), "primary", self.accept, default=True)

    def _build_background(self, body, settings: Settings, tray_available: bool, autostart_available: bool) -> None:
        body.addWidget(_title(t("settings.background.section")))
        self.background = Switch(settings.background_on_close and tray_available)
        self.background.setEnabled(tray_available)
        hint = t("settings.background.hint") if tray_available else t("settings.background.no_tray")
        body.addWidget(_row(t("settings.background.title"), hint, self.background, tray_available))
        self._mini_choice = settings.mini_player
        self.mini = Switch(settings.mini_player and self.background.isChecked())
        self.mini.setEnabled(self.background.isChecked())
        self._mini_label = _row(t("settings.mini.title"), t("settings.mini.hint"), self.mini, self.background.isChecked())
        body.addWidget(self._mini_label)
        self.rewind = _combo(REWIND_OPTIONS, _rewind_labels(), settings.mini_rewind_seconds)
        self.rewind.setEnabled(self.mini.isChecked())
        body.addWidget(_row(t("settings.rewind.title"), t("settings.rewind.hint"), self.rewind))
        self.rewind.currentIndexChanged.connect(
            lambda _i: self._on_change(mini_rewind_seconds=self.rewind.currentData()))
        self.autostart = Switch(settings.start_with_windows and autostart_available)
        self.autostart.setEnabled(autostart_available)
        body.addWidget(_row(t("settings.autostart.title"), t("settings.autostart.hint") if autostart_available
                            else t("settings.autostart.unavailable"),
                            self.autostart, autostart_available))
        body.addWidget(_separator())
        self.background.toggled.connect(self._on_background)
        self.mini.toggled.connect(self._on_mini)
        self.autostart.toggled.connect(lambda v: self._on_change(start_with_windows=v))

    def _build_radio(self, body, settings: Settings) -> None:
        body.addWidget(_title(t("settings.queue.section")))
        self.auto_queue = Switch(settings.auto_queue)
        body.addWidget(_row(t("settings.queue.title"), t("settings.queue.hint"), self.auto_queue))
        self.radio = _combo(RADIO_SIZE_OPTIONS, _radio_labels(), settings.radio_size)
        self.radio.setEnabled(settings.auto_queue)
        body.addWidget(_row(t("settings.radio.title"), t("settings.radio.hint"), self.radio))
        body.addWidget(_separator())
        self.auto_queue.toggled.connect(self._on_auto_queue)
        self.radio.currentIndexChanged.connect(lambda _i: self._on_change(radio_size=self.radio.currentData()))

    def _build_memory(self, body, settings: Settings) -> None:
        body.addWidget(_title(t("settings.memory.section")))
        self.free_memory = Switch(settings.free_memory)
        body.addWidget(_row(t("settings.memory.title"), t("settings.memory.hint"), self.free_memory))
        self.free_seconds = _combo(FREE_MEMORY_OPTIONS, _memory_labels(), settings.free_memory_seconds)
        body.addWidget(_row(t("settings.memory.wait"), "", self.free_seconds))
        self.free_result = _note("")
        self.free_button = QPushButton(t("settings.memory.free_button"))
        self.free_button.setCursor(Qt.PointingHandCursor)
        self.free_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.free_button.setEnabled(self._on_free is not None)
        self.free_button.clicked.connect(self._free_now)
        body.addWidget(_row(t("settings.memory.free_title"), t("settings.memory.free_hint"), self.free_button))
        body.addWidget(self.free_result)
        body.addWidget(_separator())
        self.free_memory.toggled.connect(lambda v: self._on_change(free_memory=v))
        self.free_seconds.currentIndexChanged.connect(
            lambda _i: self._on_change(free_memory_seconds=self.free_seconds.currentData()))

    def _build_playback(self, body, settings: Settings) -> None:
        body.addWidget(_title(t("settings.playback.section")))
        self.remember_volume = Switch(settings.remember_volume)
        body.addWidget(_row(t("settings.playback.remember_volume"), "", self.remember_volume))
        self.restore_queue = Switch(settings.restore_queue)
        body.addWidget(_row(t("settings.playback.restore_queue"), t("settings.playback.restore_queue_hint"),
                            self.restore_queue))
        self.media_keys = Switch(settings.media_keys)
        body.addWidget(_row(t("settings.playback.media_keys"), t("settings.playback.media_keys_hint"),
                            self.media_keys))
        self.notifications = Switch(settings.notifications)
        body.addWidget(_row(t("settings.playback.notifications"), t("settings.playback.notifications_hint"),
                            self.notifications))
        body.addWidget(_separator())
        self.remember_volume.toggled.connect(lambda v: self._on_change(remember_volume=v))
        self.restore_queue.toggled.connect(lambda v: self._on_change(restore_queue=v))
        self.media_keys.toggled.connect(lambda v: self._on_change(media_keys=v))
        self.notifications.toggled.connect(lambda v: self._on_change(notifications=v))

    def _build_language(self, body, settings: Settings) -> None:
        body.addWidget(_title(t("settings.language.section")))
        self.app_language = _combo(APP_LANGUAGES, _app_language_labels(), settings.app_language)
        body.addWidget(_row(t("settings.language.app_title"), t("settings.language.app_hint"), self.app_language))
        self.app_language.currentIndexChanged.connect(lambda _i: self._on_app_language(self.app_language.currentData()))
        self.language = _combo(tuple(CONTENT_LANGUAGES), CONTENT_LANGUAGES, settings.content_language)
        body.addWidget(_row(t("settings.language.content_title"), t("settings.language.content_hint"), self.language))
        body.addWidget(_separator())
        self.language.currentIndexChanged.connect(lambda _i: self._on_change(content_language=self.language.currentData()))

    def _build_thumbnails(self, body, settings: Settings) -> None:
        body.addWidget(_title(t("settings.thumbnails.section")))
        self.thumbnail_quality = _combo(THUMBNAIL_QUALITY_OPTIONS, _quality_labels(), settings.thumbnail_quality)
        body.addWidget(_row(t("settings.thumbnails.quality_title"), t("settings.thumbnails.quality_hint"),
                            self.thumbnail_quality))
        self.thumbnail_cache_limit = _combo(THUMBNAIL_CACHE_OPTIONS, _cache_limit_labels(), settings.thumbnail_cache_limit)
        body.addWidget(_row(t("settings.thumbnails.cache_title"), t("settings.thumbnails.cache_hint"),
                            self.thumbnail_cache_limit))
        body.addWidget(_separator())
        self.thumbnail_quality.currentIndexChanged.connect(
            lambda _i: self._on_change(thumbnail_quality=self.thumbnail_quality.currentData()))
        self.thumbnail_cache_limit.currentIndexChanged.connect(
            lambda _i: self._on_change(thumbnail_cache_limit=self.thumbnail_cache_limit.currentData()))

    def _build_lyrics(self, body, settings: Settings) -> None:
        body.addWidget(_title(t("settings.lyrics.section")))
        body.addWidget(_note(t("settings.lyrics.order_note")))
        chosen = [name for name in settings.lyrics_providers if name in LYRICS_PROVIDER_NAMES]
        self._provider_order = chosen + [name for name in LYRICS_PROVIDER_NAMES if name not in chosen]
        self._provider_on = {name: name in chosen for name in self._provider_order}
        self._provider_box = QVBoxLayout()
        self._provider_box.setSpacing(2)
        body.addLayout(self._provider_box)
        self.provider_switches: dict[str, Switch] = {}
        self._render_providers()
        self.lyrics_key = QLineEdit(settings.better_lyrics_key)
        self.lyrics_key.setEchoMode(QLineEdit.Password)
        self.lyrics_key.setPlaceholderText(t("settings.lyrics.key_placeholder"))
        self.lyrics_key.setFixedWidth(220)
        self.lyrics_key.setStyleSheet(theme.input_qss("QLineEdit") + "QLineEdit { padding: 6px 12px; font-size: 13px; }")
        self._saved_key = settings.better_lyrics_key
        self.lyrics_key.editingFinished.connect(self._commit_key)
        body.addWidget(_row(t("settings.lyrics.key_title"), t("settings.lyrics.key_hint"), self.lyrics_key))
        self.romanized_lyrics = Switch(settings.romanized_lyrics)
        body.addWidget(_row(t("settings.lyrics.romanized_title"), t("settings.lyrics.romanized_hint"),
                            self.romanized_lyrics))
        body.addWidget(_separator())
        self.romanized_lyrics.toggled.connect(lambda v: self._on_change(romanized_lyrics=v))

    def _build_cache(self, body) -> None:
        body.addWidget(_title(t("settings.cache.section")))
        self.cache_label = _note("")
        self.cache_button = QPushButton(t("settings.cache.button"))
        self.cache_button.setCursor(Qt.PointingHandCursor)
        self.cache_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.cache_button.setEnabled(self._clear_cache is not None)
        self.cache_button.clicked.connect(self._empty_cache)
        body.addWidget(_row(t("settings.cache.title"), t("settings.cache.hint"), self.cache_button))
        body.addWidget(self.cache_label)
        self._show_cache_size()
        body.addWidget(_separator())

    def _build_account(self, body, logged_in: bool) -> None:
        body.addWidget(_title(t("settings.account.section")))
        self.account_button = QPushButton(t("settings.account.logout") if logged_in else t("settings.account.login"))
        self.account_button.setCursor(Qt.PointingHandCursor)
        self.account_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.account_button.setEnabled(self._on_account is not None)
        self.account_button.clicked.connect(self._account)
        hint = t("settings.account.signed_in_hint") if logged_in else t("settings.account.signed_out_hint")
        body.addWidget(_row(t("settings.account.signed_in") if logged_in else t("settings.account.signed_out"), hint,
                            self.account_button))
        self.log_button = QPushButton(t("settings.log.button"))
        self.log_button.setCursor(Qt.PointingHandCursor)
        self.log_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.log_button.setEnabled(self._on_open_log is not None)
        self.log_button.clicked.connect(lambda: self._on_open_log())
        body.addWidget(_row(t("settings.log.title"), t("settings.log.hint"), self.log_button))

    def _on_background(self, enabled: bool) -> None:
        self._on_change(background_on_close=enabled)
        self.mini.blockSignals(True)
        self.mini.setChecked(self._mini_choice and enabled)
        self.mini.blockSignals(False)
        self.mini.setEnabled(enabled)
        self.rewind.setEnabled(self.mini.isChecked())
        self._mini_label.findChild(QLabel).setStyleSheet(
            f"color: {theme.TEXT if enabled else theme.TEXT_MUTED}; font-size: 14px; font-weight: 600; background: transparent;")

    def _on_auto_queue(self, enabled: bool) -> None:
        self.radio.setEnabled(enabled)
        self._on_change(auto_queue=enabled)

    def _on_mini(self, enabled: bool) -> None:
        self._mini_choice = enabled
        self.rewind.setEnabled(enabled)
        self._on_change(mini_player=enabled)

    def _free_now(self) -> None:
        before, after = self._on_free()
        freed = max(0, before - after)
        self.free_result.setText(t("settings.memory.freed", freed=freed, before=before, after=after) if before
                                 else t("settings.memory.freed_unknown"))

    def provider_order(self) -> list[str]:
        return list(self._provider_order)

    def move_provider(self, name: str, step: int) -> None:
        index = self._provider_order.index(name)
        target = index + step
        if not 0 <= target < len(self._provider_order):
            return
        self._provider_order[index], self._provider_order[target] = self._provider_order[target], self._provider_order[index]
        self._render_providers()
        self._report_providers()

    def _toggle_provider(self, name: str, enabled: bool) -> None:
        self._provider_on[name] = enabled
        self._report_providers()

    def _report_providers(self) -> None:
        self._on_change(lyrics_providers=tuple(name for name in self._provider_order if self._provider_on[name]))

    def _render_providers(self) -> None:
        while self._provider_box.count():
            item = self._provider_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.provider_switches = {}
        last = len(self._provider_order) - 1
        for index, name in enumerate(self._provider_order):
            line = QWidget()
            layout = QHBoxLayout(line)
            layout.setContentsMargins(0, 2, 0, 2)
            label = QLabel(f"{PROVIDER_LABELS[name]}  <span style='color:{theme.TEXT_SECONDARY}; font-size:12px;'>"
                           f"{t('settings.lyrics.' + name + '_hint')}</span>")
            label.setTextFormat(Qt.RichText)
            label.setStyleSheet(f"color: {theme.TEXT}; font-size: 14px; font-weight: 600; background: transparent;")
            up = icon_button("fa5s.chevron-up", 28, t("settings.lyrics.move_up"))
            down = icon_button("fa5s.chevron-down", 28, t("settings.lyrics.move_down"))
            up.setEnabled(index > 0)
            down.setEnabled(index < last)
            up.clicked.connect(lambda _c=False, n=name: self.move_provider(n, -1))
            down.clicked.connect(lambda _c=False, n=name: self.move_provider(n, 1))
            switch = Switch(self._provider_on[name])
            switch.toggled.connect(lambda v, n=name: self._toggle_provider(n, v))
            self.provider_switches[name] = switch
            layout.addWidget(label, 1)
            layout.addWidget(up)
            layout.addWidget(down)
            layout.addSpacing(6)
            layout.addWidget(switch)
            self._provider_box.addWidget(line)

    def _commit_key(self) -> None:
        text = self.lyrics_key.text().strip()
        if text != self._saved_key:
            self._saved_key = text
            self._on_change(better_lyrics_key=text)

    def done(self, result: int) -> None:
        self._commit_key()
        super().done(result)

    def _show_cache_size(self) -> None:
        if self._cache_size is None:
            self.cache_label.setText("")
            return
        self.cache_label.setText(t("settings.cache.size", size=format_size(self._cache_size())))

    def _empty_cache(self) -> None:
        freed = self._clear_cache()
        self._show_cache_size()
        self.cache_label.setText(self.cache_label.text() + " " + t("settings.cache.freed", size=format_size(freed)))

    def _on_app_language(self, language: str) -> None:
        self._on_change(app_language=language)
        # one-way: content follows a chosen app language, never the reverse
        if language and self.language.findData(language) >= 0:
            self.language.setCurrentIndex(self.language.findData(language))
        if self._on_restart is None:
            return
        if dialogs.confirm(self, t("settings.language.restart_title"), t("settings.language.restart_message"),
                           ok=t("settings.language.restart_now"), cancel=t("settings.language.restart_later")):
            self._on_restart()

    def _account(self) -> None:
        self.accept()
        self._on_account()
