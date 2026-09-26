from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from domain.settings import CONTENT_LANGUAGES, FREE_MEMORY_OPTIONS, LYRICS_PROVIDER_NAMES, RADIO_SIZE_OPTIONS, Settings
from ui import theme
from ui.components.dialogs import Modal
from ui.components.icon_button import icon_button
from ui.components.switch import Switch

RADIO_LABELS = {size: f"{size} canciones" for size in RADIO_SIZE_OPTIONS}
RADIO_LABELS[0] = "Ilimitada (se extiende sola)"
MEMORY_LABELS = {10: "10 segundos", 20: "20 segundos", 60: "1 minuto", 180: "3 minutos"}
PROVIDER_LABELS = {"betterlyrics": "Better Lyrics", "lrclib": "LRCLIB", "youtube": "YouTube Music"}
PROVIDER_HINTS = {"betterlyrics": "Sincronizada por palabra", "lrclib": "Sincronizada por línea",
                  "youtube": "Suele ser texto sin sincronizar"}

_COMBO_QSS = f"""
    QComboBox {{ background: rgba(255,255,255,0.08); color: {theme.TEXT}; border: 1px solid {theme.BORDER};
                 border-radius: 8px; padding: 6px 12px; min-width: 190px; font-size: 13px; }}
    QComboBox:hover {{ border-color: rgba(255,255,255,0.4); }}
    QComboBox QAbstractItemView {{ background: {theme.SURFACE_RAISED}; color: {theme.TEXT}; border: 1px solid {theme.BORDER};
                                   selection-background-color: rgba(255,255,255,0.14); outline: none; }}
"""


_SCROLL_QSS = """
    QScrollArea { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
    QScrollBar::handle:vertical { background: rgba(255,255,255,0.25); border-radius: 3px; min-height: 30px; }
    QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.4); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
DIALOG_HEIGHT = 560
SCREEN_MARGIN = 0.85


def format_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{max(0, size) // 1024} KB"
    if size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} MB".replace(".", ",")
    return f"{size / 1024 ** 3:.2f} GB".replace(".", ",")


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


def _combo(options, labels, current) -> QComboBox:
    box = QComboBox()
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


# configuracion ajustes modal
class SettingsDialog(Modal):
    def __init__(self, parent, settings: Settings, tray_available: bool, on_change, on_free=None, *,
                 cache_size=None, clear_cache=None, logged_in: bool = False, on_account=None,
                 autostart_available: bool = True):
        super().__init__(parent, "Configuración", width=540, height=_dialog_height())
        self._on_change = on_change
        self._on_free = on_free
        self._cache_size = cache_size
        self._clear_cache = clear_cache
        self._on_account = on_account
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
        self._build_lyrics(body, settings)
        self._build_cache(body)
        self._build_account(body, logged_in)
        body.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(_SCROLL_QSS)
        scroll.setWidget(content)
        self.body.addWidget(scroll)
        self.add_button("Listo", "primary", self.accept, default=True)

    def _build_background(self, body, settings: Settings, tray_available: bool, autostart_available: bool) -> None:
        body.addWidget(_title("Segundo plano"))
        self.background = Switch(settings.background_on_close and tray_available)
        self.background.setEnabled(tray_available)
        hint = ("Al cerrar la ventana la música sigue sonando y la app queda en la bandeja del sistema. Si lo apagas, "
                "cerrar la ventana cierra la app.")
        if not tray_available:
            hint = "No disponible: este sistema no tiene bandeja del sistema."
        body.addWidget(_row("Seguir en segundo plano al cerrar", hint, self.background, tray_available))
        self._mini_choice = settings.mini_player
        self.mini = Switch(settings.mini_player and self.background.isChecked())
        self.mini.setEnabled(self.background.isChecked())
        self._mini_label = _row("Mini reproductor", "Ventana pequeña con los controles cuando minimizas o cierras la app. "
                                "Requiere seguir en segundo plano.", self.mini, self.background.isChecked())
        body.addWidget(self._mini_label)
        self.autostart = Switch(settings.start_with_windows and autostart_available)
        self.autostart.setEnabled(autostart_available)
        body.addWidget(_row("Iniciar con Windows", "Se abre al encender el equipo, minimizada en la bandeja y sin "
                            "mostrar la ventana." if autostart_available else "No disponible en este sistema.",
                            self.autostart, autostart_available))
        body.addWidget(_separator())
        self.background.toggled.connect(self._on_background)
        self.mini.toggled.connect(self._on_mini)
        self.autostart.toggled.connect(lambda v: self._on_change(start_with_windows=v))

    def _build_radio(self, body, settings: Settings) -> None:
        body.addWidget(_title("Cola de radio"))
        self.radio = _combo(RADIO_SIZE_OPTIONS, RADIO_LABELS, settings.radio_size)
        body.addWidget(_row("Canciones al elegir una canción",
                            "La primera tanda llega junto con la canción y el resto se carga en segundo plano hasta "
                            "completar el tamaño elegido. Una cola grande no consume memoria de forma apreciable.",
                            self.radio))
        body.addWidget(_separator())
        self.radio.currentIndexChanged.connect(lambda _i: self._on_change(radio_size=self.radio.currentData()))

    def _build_memory(self, body, settings: Settings) -> None:
        body.addWidget(_title("Memoria"))
        self.free_memory = Switch(settings.free_memory)
        body.addWidget(_row("Liberar memoria en segundo plano", "Descarta miniaturas y listas cuando la ventana está "
                            "cerrada o minimizada; se recargan al volver.", self.free_memory))
        self.free_seconds = _combo(FREE_MEMORY_OPTIONS, MEMORY_LABELS, settings.free_memory_seconds)
        body.addWidget(_row("Esperar antes de liberar", "", self.free_seconds))
        self.free_result = _note("")
        self.free_button = QPushButton("Liberar RAM ahora")
        self.free_button.setCursor(Qt.PointingHandCursor)
        self.free_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.free_button.setEnabled(self._on_free is not None)
        self.free_button.clicked.connect(self._free_now)
        body.addWidget(_row("Liberar memoria ahora", "Devuelve al sistema la memoria que la app no está usando, como hace RAMMap. Crece de nuevo solo lo que necesite.", self.free_button))
        body.addWidget(self.free_result)
        body.addWidget(_separator())
        self.free_memory.toggled.connect(lambda v: self._on_change(free_memory=v))
        self.free_seconds.currentIndexChanged.connect(
            lambda _i: self._on_change(free_memory_seconds=self.free_seconds.currentData()))

    def _build_playback(self, body, settings: Settings) -> None:
        body.addWidget(_title("Reproducción"))
        self.remember_volume = Switch(settings.remember_volume)
        body.addWidget(_row("Recordar el volumen", "", self.remember_volume))
        self.restore_queue = Switch(settings.restore_queue)
        body.addWidget(_row("Restaurar la cola al abrir", "Recupera la cola y la canción de la última vez.",
                            self.restore_queue))
        self.media_keys = Switch(settings.media_keys)
        body.addWidget(_row("Teclas multimedia", "Pausa, siguiente y anterior desde el teclado, incluso con la app en "
                            "segundo plano. Si otra aplicación ya las usa, se apaga sola.", self.media_keys))
        self.notifications = Switch(settings.notifications)
        body.addWidget(_row("Aviso al cambiar de canción", "Muestra una notificación cuando la ventana está oculta o "
                            "minimizada.", self.notifications))
        body.addWidget(_separator())
        self.remember_volume.toggled.connect(lambda v: self._on_change(remember_volume=v))
        self.restore_queue.toggled.connect(lambda v: self._on_change(restore_queue=v))
        self.media_keys.toggled.connect(lambda v: self._on_change(media_keys=v))
        self.notifications.toggled.connect(lambda v: self._on_change(notifications=v))

    def _build_language(self, body, settings: Settings) -> None:
        body.addWidget(_title("Idioma"))
        self.language = _combo(tuple(CONTENT_LANGUAGES), CONTENT_LANGUAGES, settings.content_language)
        body.addWidget(_row("Idioma del contenido", "Textos que entrega YouTube Music en el inicio, Explorar y las "
                            "búsquedas. Los menús de la app siguen en español.", self.language))
        body.addWidget(_separator())
        self.language.currentIndexChanged.connect(lambda _i: self._on_change(content_language=self.language.currentData()))

    def _build_lyrics(self, body, settings: Settings) -> None:
        body.addWidget(_title("Letras"))
        body.addWidget(_note("Se prueban en este orden y se usa la primera letra sincronizada; si ninguna lo está, la "
                             "primera que responda."))
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
        self.lyrics_key.setPlaceholderText("Opcional")
        self.lyrics_key.setFixedWidth(220)
        self.lyrics_key.setStyleSheet(theme.input_qss("QLineEdit") + "QLineEdit { padding: 6px 12px; font-size: 13px; }")
        self._saved_key = settings.better_lyrics_key
        self.lyrics_key.editingFinished.connect(self._commit_key)
        body.addWidget(_row("Clave de Better Lyrics", "Sin clave solo responde lo que ya tiene guardado. La entregan "
                            "sus autores por proyecto.", self.lyrics_key))
        body.addWidget(_separator())

    def _build_cache(self, body) -> None:
        body.addWidget(_title("Caché"))
        self.cache_label = _note("")
        self.cache_button = QPushButton("Vaciar caché")
        self.cache_button.setCursor(Qt.PointingHandCursor)
        self.cache_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.cache_button.setEnabled(self._clear_cache is not None)
        self.cache_button.clicked.connect(self._empty_cache)
        body.addWidget(_row("Miniaturas y datos temporales", "Se vuelven a descargar cuando hacen falta. No borra tu "
                            "sesión, tus playlists ni tu cola.", self.cache_button))
        body.addWidget(self.cache_label)
        self._show_cache_size()
        body.addWidget(_separator())

    def _build_account(self, body, logged_in: bool) -> None:
        body.addWidget(_title("Cuenta"))
        self.account_button = QPushButton("Cerrar sesión" if logged_in else "Iniciar sesión")
        self.account_button.setCursor(Qt.PointingHandCursor)
        self.account_button.setStyleSheet(theme.button_qss("tonal", height=34))
        self.account_button.setEnabled(self._on_account is not None)
        self.account_button.clicked.connect(self._account)
        hint = ("Con la sesión iniciada ves tu biblioteca y tus playlists de YouTube Music." if logged_in
                else "Sin sesión puedes escuchar, pero no ves tu biblioteca ni tus playlists.")
        body.addWidget(_row("Sesión iniciada" if logged_in else "Sin sesión", hint, self.account_button))

    def _on_background(self, enabled: bool) -> None:
        self._on_change(background_on_close=enabled)
        self.mini.blockSignals(True)
        self.mini.setChecked(self._mini_choice and enabled)
        self.mini.blockSignals(False)
        self.mini.setEnabled(enabled)
        self._mini_label.findChild(QLabel).setStyleSheet(
            f"color: {theme.TEXT if enabled else theme.TEXT_MUTED}; font-size: 14px; font-weight: 600; background: transparent;")

    def _on_mini(self, enabled: bool) -> None:
        self._mini_choice = enabled
        self._on_change(mini_player=enabled)

    def _free_now(self) -> None:
        before, after = self._on_free()
        freed = max(0, before - after)
        self.free_result.setText(f"Liberados {freed} MB (de {before} MB a {after} MB)." if before else "Memoria liberada.")

    # letras orden y activos
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
                           f"{PROVIDER_HINTS[name]}</span>")
            label.setTextFormat(Qt.RichText)
            label.setStyleSheet(f"color: {theme.TEXT}; font-size: 14px; font-weight: 600; background: transparent;")
            up = icon_button("fa5s.chevron-up", 28, "Subir")
            down = icon_button("fa5s.chevron-down", 28, "Bajar")
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
        self.cache_label.setText(f"Ocupa {format_size(self._cache_size())}.")

    def _empty_cache(self) -> None:
        freed = self._clear_cache()
        self._show_cache_size()
        self.cache_label.setText(f"{self.cache_label.text()} Liberados {format_size(freed)}.")

    def _account(self) -> None:
        self.accept()
        self._on_account()
