import pytest
import qtawesome as qta
from PySide6.QtWidgets import QAbstractButton, QLabel, QLineEdit

from core import i18n
from domain.settings import Settings
from tests.test_presenters import NullThumbnails
from tests.test_i18n_guard import PENDING
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog


def visible_texts(widget):
    texts = [w.text() for w in widget.findChildren(QLabel)]
    texts += [w.text() for w in widget.findChildren(QAbstractButton)]
    texts += [w.placeholderText() for w in widget.findChildren(QLineEdit)]
    texts += [w.toolTip() for w in widget.findChildren(QAbstractButton)]
    return [text for text in texts if text]


@pytest.mark.parametrize("lang", ["en", "pt"])
def test_main_screens_have_no_raw_keys(qapp, lang):
    i18n.set_language(lang, i18n.load(i18n.locales_dir()))
    window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
    dialog = SettingsDialog(window, Settings(), True, lambda **kw: None, logged_in=True, on_open_log=lambda: None)
    keys = i18n.load(i18n.locales_dir())[i18n.SOURCE]
    # keys anywhere in the text: labels may be padded or wrapped in rich text
    raw = [text for text in visible_texts(window) + visible_texts(dialog) if any(key in text for key in keys)]
    dialog.deleteLater()
    window.deleteLater()
    assert not raw


def test_every_file_is_converted():
    assert not PENDING


def test_feed_loading_and_empty_messages_follow_the_language(qapp):
    from ui.components.section_feed import SectionFeed
    i18n.set_language("en", i18n.load(i18n.locales_dir()))
    feed = SectionFeed()
    feed.set_loading()
    assert feed._message.text() == i18n.t("home.loading") != "Cargando…"
    feed.set_sections([], None)
    assert feed._message.text() == i18n.t("home.feed.empty")
    feed.set_sections([], None, empty_message="")
    feed.deleteLater()
