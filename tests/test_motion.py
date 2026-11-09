import pytest
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

from ui import motion


@pytest.fixture(autouse=True)
def motion_on():
    motion.set_enabled(True)
    yield
    motion.set_enabled(True)


def test_fade_in_animates_opacity_and_cleans_up(qapp, wait_until):
    widget = QWidget()
    widget.show()
    motion.fade_in(widget, ms=40)
    assert isinstance(widget.graphicsEffect(), QGraphicsOpacityEffect)
    assert wait_until(lambda: widget.graphicsEffect() is None)


def test_fade_in_does_nothing_when_animations_are_off(qapp):
    motion.set_enabled(False)
    widget = QWidget()
    motion.fade_in(widget)
    assert widget.graphicsEffect() is None


def test_fade_in_never_replaces_an_existing_effect(qapp):
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    widget = QWidget()
    glow = QGraphicsDropShadowEffect()
    widget.setGraphicsEffect(glow)
    motion.fade_in(widget)
    assert widget.graphicsEffect() is glow


def test_switching_pages_fades_the_new_page_in(qapp):
    import qtawesome as qta
    from tests.test_presenters import NullThumbnails
    from ui.main_window import MainWindow
    window = MainWindow(NullThumbnails(), qta.icon("fa5s.music"))
    window.show()
    window.show_view("explore")
    assert isinstance(window.explore_panel.graphicsEffect(), QGraphicsOpacityEffect)
    window.deleteLater()


def test_animations_setting_defaults_on_and_reaches_the_motion_module(qapp, tmp_path):
    from domain.settings import Settings
    assert Settings().animations is True
    assert Settings.from_dict({"animations": False}).animations is False
    from presenters.settings_presenter import SettingsPresenter
    from services.settings_service import SettingsService
    from infra.settings_repository import SettingsRepository
    from tests.test_presenters import Rig
    rig = Rig()
    try:
        service = SettingsService(SettingsRepository(str(tmp_path / "s.json")))
        rig.keep(SettingsPresenter(rig.window, service))
        service.update(animations=False)
        assert motion.enabled() is False
    finally:
        rig.dispose()


def test_card_actions_fade_in_on_hover(qapp, monkeypatch):
    from ui.components.clickable import ClickableWidget
    from ui.components.section_feed import HomeCard
    card = HomeCard({"type": "playlist", "playlistId": "p1", "title": "P", "thumbnails": []}, None)
    card.show()
    monkeypatch.setattr(ClickableWidget, "hovered", property(lambda _self: True))
    card._sync_overlay()
    assert isinstance(card._overlay_widget.graphicsEffect(), QGraphicsOpacityEffect)
