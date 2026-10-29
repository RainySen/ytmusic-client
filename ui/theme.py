THEMES = ("classic", "aero", "cyberpunk")

BG = "#0f0f0f"
SURFACE = "#212121"
SURFACE_RAISED = "#282828"
BORDER = "#3a3a3a"
TEXT = "#f1f1f1"
TEXT_SECONDARY = "#aaaaaa"
TEXT_MUTED = "#717171"
ACCENT = "#ff0033"
LINK = "#3ea6ff"
DANGER = "#ff4e45"

SCRIM = "rgba(0, 0, 0, 0.6)"
HOVER = "#e6e6e6"
PRESSED = "#cccccc"
SELECTION = "rgba(255,255,255,0.14)"
CHIP = "rgba(255,255,255,0.10)"
CHIP_CHECKED = "#ffffff"
CHIP_CHECKED_TEXT = "#0f0f0f"
BUTTON_BG = "#ffffff"
BUTTON_TEXT = "#0f0f0f"
GLOW = "transparent"
PANEL_TOP = SURFACE
PANEL_BOTTOM = SURFACE
SWITCH_KNOB = "#ffffff"

_TOKENS = {
    "classic": {
        "bg": BG,
        "bg_end": BG,
        "surface": SURFACE,
        "surface_raised": SURFACE_RAISED,
        "border": BORDER,
        "text": TEXT,
        "text_secondary": TEXT_SECONDARY,
        "text_muted": TEXT_MUTED,
        "accent": ACCENT,
        "link": LINK,
        "danger": DANGER,
        "scrim": SCRIM,
        "hover": HOVER,
        "pressed": PRESSED,
        "selection": SELECTION,
        "chip": CHIP,
        "chip_checked": CHIP_CHECKED,
        "chip_checked_text": CHIP_CHECKED_TEXT,
        "button_bg": BUTTON_BG,
        "button_text": BUTTON_TEXT,
        "glow": GLOW,
        "panel_top": PANEL_TOP,
        "panel_bottom": PANEL_BOTTOM,
        "switch_knob": SWITCH_KNOB,
    },
    "aero": {
        "bg": "#071a2e",
        "bg_end": "#0b4a6e",
        "surface": "#0b2a44",
        "surface_raised": "#10385a",
        "border": "#1f5a80",
        "text": "#e6f6ff",
        "text_secondary": "#9cc6dd",
        "text_muted": "#6f9cb6",
        "accent": "#3fe0d0",
        "link": "#7fd7ff",
        "danger": "#ff7a8a",
        "scrim": "rgba(3, 12, 24, 0.65)",
        "hover": "#6fe4f8",
        "pressed": "#2a9fc0",
        "selection": "rgba(63,224,208,0.25)",
        "chip": "rgba(255,255,255,0.10)",
        "chip_checked": "#3fe0d0",
        "chip_checked_text": "#04202e",
        "button_bg": "#3cc4e6",
        "button_text": "#04202e",
        "glow": "rgba(63,224,208,0.6)",
        "panel_top": "#12406a",
        "panel_bottom": "#0b2a44",
        "switch_knob": "#06304f",
    },
    "cyberpunk": {
        "bg": "#07070d",
        "bg_end": "#07070d",
        "surface": "#0f0f1a",
        "surface_raised": "#16162a",
        "border": "#2a2a4a",
        "text": "#d6dcff",
        "text_secondary": "#8e95c8",
        "text_muted": "#6a6f9e",
        "accent": "#ff2bd6",
        "link": "#00f0ff",
        "danger": "#ff5470",
        "scrim": "rgba(0, 0, 0, 0.7)",
        "hover": "#24243d",
        "pressed": "#2f2f52",
        "selection": "rgba(0,240,255,0.22)",
        "chip": "rgba(255,255,255,0.08)",
        "chip_checked": "#00f0ff",
        "chip_checked_text": "#07070d",
        "button_bg": "#ff2bd6",
        "button_text": "#0a0a12",
        "glow": "rgba(0,240,255,0.7)",
        "panel_top": "#0f0f1a",
        "panel_bottom": "#0f0f1a",
        "switch_knob": "#07070d",
    },
}

_current = "classic"


def apply(name: str) -> str:
    global _current
    _current = name if name in _TOKENS else "classic"
    globals().update({key.upper(): value for key, value in _TOKENS[_current].items()})
    return _current


def current() -> str:
    return _current


# translucent layers: white/black in classic, tinted elsewhere
_OVERLAY_RGB = {"classic": "255,255,255", "aero": "200,240,255", "cyberpunk": "170,200,255"}
_SHADE_RGB = {"classic": "0,0,0", "aero": "0,12,28", "cyberpunk": "4,0,16"}


_ACCENT_SOFT_RGB = {"classic": "255,0,0", "aero": "63,224,208", "cyberpunk": "255,43,214"}
# youtube logo red: brand, never themed
BRAND = "#FF0000"


def accent_soft(alpha: float) -> str:
    return f"rgba({_ACCENT_SOFT_RGB[_current]},{alpha})"


_FONTS = {
    "classic": '"YouTube Sans", "Roboto", "Google Sans", "Segoe UI", system-ui',
    "aero": '"Segoe UI", system-ui',
    # cyberpunk: empty, the family comes from the application font set in load_fonts
    "cyberpunk": "",
}
_FONT_FILES = {"cyberpunk": ("Jersey15.ttf", "Jersey 15")}


def font_family() -> str:
    return _FONTS[_current]


def load_fonts() -> None:
    # bundled font for the active theme; needs a running QApplication
    entry = _FONT_FILES.get(_current)
    if not entry:
        return
    import os
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication
    QFontDatabase.addApplicationFont(os.path.join(os.path.dirname(__file__), "fonts", entry[0]))
    font = QFont(entry[1])
    # pixel fonts ship odd ligatures; QSS cannot turn features off, the app font can
    font.setFeature(QFont.Tag("liga"), 0)
    font.setFeature(QFont.Tag("calt"), 0)
    QApplication.setFont(font)


def radius(px: int) -> int:
    # cyberpunk: hard pixel corners
    return 0 if _current == "cyberpunk" else px


def glass(fallback: str) -> str:
    # aero bars: soft vista glass, faint sheen fading down; tall bars make a hard shine line look like a seam
    if _current != "aero":
        return fallback
    return (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e5c8a, stop:0.45 {PANEL_TOP}, "
            f"stop:1 {PANEL_BOTTOM})")


def glow_effect():
    # neon halo, cyberpunk only; callers pass the result to setGraphicsEffect
    if _current != "cyberpunk":
        return None
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    r, g, b, a = (float(v) for v in GLOW[GLOW.index("(") + 1:-1].split(","))
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(18)
    effect.setOffset(0)
    effect.setColor(QColor(int(r), int(g), int(b), int(a * 255)))
    return effect


def overlay(alpha: float) -> str:
    return f"rgba({_OVERLAY_RGB[_current]},{alpha})"


def shade(alpha: float) -> str:
    return f"rgba({_SHADE_RGB[_current]},{alpha})"


# gel: bright top half, hard stop at the middle, deep bottom
def gel() -> str:
    return (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8ff0ff, stop:0.5 {BUTTON_BG}, "
            f"stop:0.5 #2aa8c8, stop:1 #127aa0)")


def button_qss(kind: str = "primary", height: int = 40) -> str:
    palette = {
        "primary": (BUTTON_BG, BUTTON_TEXT, HOVER, PRESSED),
        "tonal": ("rgba(255,255,255,0.12)", "#ffffff", "rgba(255,255,255,0.20)", "rgba(255,255,255,0.26)"),
        "text": ("transparent", LINK, "rgba(62,166,255,0.12)", "rgba(62,166,255,0.20)"),
    }[kind]
    background, color, hover, pressed = palette
    border = "none"
    if kind == "primary" and _current == "aero":
        background = gel()
        border = f"1px solid {BORDER}"
    elif kind == "primary" and _current == "cyberpunk":
        border = f"1px solid {LINK}"
    return f"""
        QPushButton {{ background: {background}; color: {color}; border: {border}; border-radius: {radius(height // 2)}px;
                       padding: 0 22px; min-height: {height}px; font-size: 14px; font-weight: 600; }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: {pressed}; }}
        QPushButton:disabled {{ background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.35); }}
        QPushButton:focus {{ outline: none; }}
    """


def input_qss(selector: str) -> str:
    return f"""
        {selector} {{ background: transparent; color: {TEXT}; border: 2px solid rgba(255,255,255,0.22);
                      border-radius: {radius(10)}px; padding: 11px 14px; font-size: 15px;
                      selection-background-color: {LINK}; selection-color: {BG}; }}
        {selector}:focus {{ border: 2px solid {LINK}; background: transparent; }}
    """


def chip_qss(selected: bool) -> str:
    if selected:
        background = gel() if _current == "aero" else CHIP_CHECKED
        return f"""
            QPushButton {{ background: {background}; color: {CHIP_CHECKED_TEXT}; border: none;
                          border-radius: {radius(8)}px; padding: 8px 16px; font-size: 14px; font-weight: 600; }}
        """
    return f"""
        QPushButton {{ background: {CHIP}; color: {TEXT}; border: none; border-radius: {radius(8)}px;
                      padding: 8px 16px; font-size: 14px; font-weight: 500; }}
        QPushButton:hover {{ background: rgba(255,255,255,0.18); }}
    """


apply("classic")
