import sys

import qtawesome

from core import icons


def test_import_leaves_the_blocked_qt_modules_importable_afterwards(qapp):
    icons.import_qtawesome()
    for name in icons._UNUSED_QT:
        assert sys.modules.get(name, "absent") is not None


def test_only_the_used_icon_fonts_are_loaded(qapp):
    previous = qtawesome._resource["iconic"]
    try:
        icons.load_used_fonts()
        loaded = set(qtawesome._resource["iconic"].charmap)
        assert loaded == set(icons.USED_FONTS)
        assert not qtawesome.icon("fa5s.music").isNull() and not qtawesome.icon("fa5b.google").isNull()
    finally:
        qtawesome._resource["iconic"] = previous
