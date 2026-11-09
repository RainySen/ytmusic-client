import pytest

from domain.settings import Settings
from ui.settings_dialog import SettingsDialog


@pytest.fixture(autouse=True)
def first_tab():
    SettingsDialog._last_tab = 0
    yield
    SettingsDialog._last_tab = 0


def dialog(qapp):
    return SettingsDialog(None, Settings(), True, lambda **kw: None)


def test_settings_are_split_into_four_tabs(qapp):
    d = dialog(qapp)
    assert [b.text() for b in d.tab_buttons] == ["Reproducción", "Apariencia", "Sistema", "Cuenta"]
    pages = [d.pages.widget(i) for i in range(d.pages.count())]
    assert pages[0].isAncestorOf(d.previous_restarts) and pages[0].isAncestorOf(d.auto_queue)
    assert pages[1].isAncestorOf(d.theme_combo) and pages[1].isAncestorOf(d.thumbnail_quality)
    assert pages[2].isAncestorOf(d.background) and pages[2].isAncestorOf(d.cache_button)
    assert pages[3].isAncestorOf(d.account_button) and pages[3].isAncestorOf(d.log_button)
    d.deleteLater()


def test_clicking_a_tab_shows_its_page_and_is_remembered(qapp):
    d = dialog(qapp)
    assert d.pages.currentIndex() == 0 and d.tab_buttons[0].isChecked()
    d.tab_buttons[2].click()
    assert d.pages.currentIndex() == 2 and d.tab_buttons[2].isChecked() and not d.tab_buttons[0].isChecked()
    d.deleteLater()
    again = dialog(qapp)
    assert again.pages.currentIndex() == 2
    again.deleteLater()
