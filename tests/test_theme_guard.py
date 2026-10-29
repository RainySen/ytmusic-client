import ast
import pathlib
import re

import pytest
import qtawesome as qta
from PySide6.QtGui import QColor

from domain.settings import Settings
from tests.test_presenters import NullThumbnails
from ui import theme
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = ("bg", "bg_end", "surface", "surface_raised", "border", "text", "text_secondary", "text_muted", "accent",
          "link", "danger", "scrim", "hover", "pressed", "selection", "chip", "chip_checked", "chip_checked_text",
          "button_bg", "button_text", "glow", "panel_top", "panel_bottom", "switch_knob")
# files still holding color literals; each conversion batch removes its own, the list ends empty
PENDING = set()
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|QColor\(\s*[\"']#")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")


@pytest.fixture(autouse=True)
def classic_theme():
    yield
    theme.apply("classic")


def color(value):
    match = RGBA.fullmatch(value.strip())
    if match:
        red, green, blue, alpha = match.groups()
        return QColor(int(red), int(green), int(blue), 255 if alpha is None else round(float(alpha) * 255))
    return QColor(value)


def luminance(value):
    channels = [color(value).red(), color(value).green(), color(value).blue()]

    def linear(channel):
        channel = channel / 255
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(first, second):
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def ui_files():
    for path in sorted((ROOT / "ui").rglob("*.py")):
        yield path.relative_to(ROOT).as_posix(), path


def import_time_nodes(tree):
    pending = list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.ClassDef):
            pending.extend(node.body)
            pending.extend(node.decorator_list)
            pending.extend(node.bases)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            # defaults and decorators run at import, the body does not
            pending.extend(node.args.defaults)
            pending.extend(default for default in node.args.kw_defaults if default is not None)
            if not isinstance(node, ast.Lambda):
                pending.extend(node.decorator_list)
        else:
            yield node
            pending.extend(ast.iter_child_nodes(node))


@pytest.mark.parametrize("name", theme.THEMES)
def test_every_theme_defines_exactly_the_same_tokens(name):
    assert set(theme._TOKENS[name]) == set(TOKENS)


@pytest.mark.parametrize("name", theme.THEMES)
def test_every_token_is_a_valid_color(name):
    for key, value in theme._TOKENS[name].items():
        if key == "glow" and value == "transparent":
            continue
        assert color(value).isValid(), (name, key, value)


@pytest.mark.parametrize("name", theme.THEMES)
def test_text_has_enough_contrast(name):
    tokens = theme._TOKENS[name]
    assert contrast(tokens["text"], tokens["bg"]) >= 4.5, name
    assert contrast(tokens["text"], tokens["surface"]) >= 4.5, name
    assert contrast(tokens["text_secondary"], tokens["bg"]) >= 3, name


@pytest.mark.parametrize("name", theme.THEMES)
def test_checked_switch_knob_stands_out_from_its_track(name):
    tokens = theme._TOKENS[name]
    assert contrast(tokens["switch_knob"], tokens["link"]) >= 1.8, name


def test_classic_keeps_todays_values():
    assert theme.apply("classic") == "classic"
    assert theme.current() == "classic"
    expected = {
        "bg": "#0f0f0f", "bg_end": "#0f0f0f", "surface": "#212121", "surface_raised": "#282828", "border": "#3a3a3a",
        "text": "#f1f1f1", "text_secondary": "#aaaaaa", "text_muted": "#717171", "accent": "#ff0033",
        "link": "#3ea6ff", "danger": "#ff4e45", "scrim": "rgba(0, 0, 0, 0.6)", "hover": "#e6e6e6",
        "pressed": "#cccccc", "selection": "rgba(255,255,255,0.14)", "chip": "rgba(255,255,255,0.10)",
        "chip_checked": "#ffffff", "chip_checked_text": "#0f0f0f", "button_bg": "#ffffff",
        "button_text": "#0f0f0f", "glow": "transparent", "panel_top": "#212121", "panel_bottom": "#212121", "switch_knob": "#ffffff",
    }
    assert theme._TOKENS["classic"] == expected
    for key, value in expected.items():
        assert getattr(theme, key.upper()) == value


def test_unknown_theme_falls_back_to_classic():
    assert theme.apply("nope") == "classic" and theme.current() == "classic"
    assert theme.apply("aero") == "aero" and theme.current() == "aero"
    assert theme.BG == "#071a2e"


def test_primary_buttons_follow_the_theme():
    theme.apply("aero")
    assert "qlineargradient" in theme.button_qss() and "stop:0.5" in theme.button_qss()
    theme.apply("cyberpunk")
    assert f"1px solid {theme.LINK}" in theme.button_qss()
    theme.apply("classic")
    assert "qlineargradient" not in theme.button_qss() and "1px solid" not in theme.button_qss()


def test_no_theme_reads_at_import_time():
    # pending files still build QSS from colors at import; their batch moves it into functions
    offenders = {}
    for rel, path in ui_files():
        if rel in PENDING:
            continue
        found = []
        for node in import_time_nodes(ast.parse(path.read_text(encoding="utf-8"))):
            is_read = isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "theme"
            is_call = (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                       and isinstance(node.func.value, ast.Name) and node.func.value.id == "theme"
                       and node.func.attr.endswith("_qss"))
            if is_read or is_call:
                found.append(node.lineno)
        if found:
            offenders[rel] = found
    assert not offenders, offenders


def test_no_color_literals_outside_the_theme_module():
    leftovers = {}
    for rel, path in ui_files():
        if rel == "ui/theme.py" or rel in PENDING:
            continue
        hits = LITERAL.findall(path.read_text(encoding="utf-8"))
        if hits:
            leftovers[rel] = hits[:5]
    assert not leftovers, leftovers


@pytest.mark.parametrize("name", theme.THEMES)
def test_main_window_and_settings_dialog_build_under_each_theme(qapp, name):
    theme.apply(name)
    window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
    dialog = SettingsDialog(window, Settings(theme=name), True, lambda **kw: None, on_restart=lambda: None)
    assert theme.current() == name
    assert [dialog.theme_combo.itemData(index) for index in range(dialog.theme_combo.count())] == list(theme.THEMES)
    dialog.deleteLater()
    window.deleteLater()


def test_overlay_and_shade_keep_classic_and_tint_other_themes():
    from ui import theme
    try:
        theme.apply("classic")
        assert theme.overlay(0.08) == "rgba(255,255,255,0.08)" and theme.shade(0.6) == "rgba(0,0,0,0.6)"
        theme.apply("cyberpunk")
        assert theme.overlay(0.08) != "rgba(255,255,255,0.08)"
    finally:
        theme.apply("classic")


def test_accent_soft_keeps_the_classic_red_tint_and_brand_stays_youtube_red():
    from ui import theme
    try:
        theme.apply("classic")
        assert theme.accent_soft(0.08) == "rgba(255,0,0,0.08)" and theme.BRAND == "#FF0000"
        theme.apply("aero")
        assert theme.accent_soft(0.08) != "rgba(255,0,0,0.08)" and theme.BRAND == "#FF0000"
    finally:
        theme.apply("classic")


def _under(name):
    from ui import theme
    theme.apply(name)
    return theme


def test_the_window_stylesheet_follows_the_theme_applied_at_startup(qapp):
    import qtawesome as qta
    from tests.test_presenters import NullThumbnails
    from ui.main_window import MainWindow
    try:
        theme = _under("aero")
        window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
        sheet = window.styleSheet()
        window.deleteLater()
        assert theme.BG in sheet and "qlineargradient" in sheet
        theme = _under("classic")
        window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
        assert "qlineargradient" not in window.styleSheet()
        window.deleteLater()
    finally:
        _under("classic")


def test_cyberpunk_glows_only_on_play_and_the_active_nav_item(qapp):
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    import qtawesome as qta
    from tests.test_presenters import NullThumbnails
    from ui.main_window import MainWindow
    try:
        _under("cyberpunk")
        window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
        assert isinstance(window.player_panel.play_button.graphicsEffect(), QGraphicsDropShadowEffect)
        glowing = [b for b in window.sidebar.nav_buttons.values() if b.graphicsEffect() is not None]
        assert len(glowing) == 1
        window.deleteLater()
        _under("classic")
        window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
        assert window.player_panel.play_button.graphicsEffect() is None
        assert all(b.graphicsEffect() is None for b in window.sidebar.nav_buttons.values())
        window.deleteLater()
    finally:
        _under("classic")
