from __future__ import annotations

import sys

# qtpy imports these unused qt modules; blocking them saves ~20 MB ram
_UNUSED_QT = ("PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtDataVisualization")
USED_FONTS = ("fa5s", "fa5b")


def import_qtawesome():
    blocked = [name for name in _UNUSED_QT if name not in sys.modules]
    for name in blocked:
        sys.modules[name] = None
    try:
        import qtawesome
    finally:
        for name in blocked:
            if sys.modules.get(name, False) is None:
                del sys.modules[name]
    return qtawesome


# needs QApplication
def load_used_fonts() -> None:
    qtawesome = import_qtawesome()
    from qtawesome.iconic_font import IconicFont

    fonts = [font for font in qtawesome._BUNDLED_FONTS if font[0] in USED_FONTS]
    qtawesome._resource["iconic"] = IconicFont(*fonts)
