from PySide6.QtCore import QEvent, QPoint, QTimer, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMenu, QPushButton

from ui.components import dialogs
from ui.components.clickable import ClickableWidget
from ui.components.home_panel import HomePanel
from ui.components.section_feed import CARD_SIZE, CardsSection, CompactSection, CompactSongItem
from ui.components.lazy_thumbnail import LazyThumbnail
from ui.components.search_panel import SearchPanel, _ArtistHero, _ResultRow
from ui.components.track_actions import TrackActionsButton


class FakeThumbnails:
    def __init__(self):
        self.requests = []

    def request(self, url, callback):
        self.requests.append(url)


def song(n):
    return {"type": "song", "videoId": f"v{n}", "title": f"Song {n}", "artists": [{"name": "A"}],
            "thumbnails": [{"url": f"http://t/{n}", "width": 200}]}


def playlist(n):
    return {"type": "playlist", "playlistId": f"p{n}", "title": f"PL {n}",
            "thumbnails": [{"url": f"http://p/{n}", "width": 300}]}


def test_click_activates_on_release_inside(qapp):
    widget = ClickableWidget()
    widget.resize(100, 40)
    widget.show()
    spy = QSignalSpy(widget.activated)
    QTest.mouseClick(widget, Qt.LeftButton, pos=QPoint(50, 20))
    assert spy.count() == 1


def test_press_then_release_outside_does_not_activate(qapp):
    widget = ClickableWidget()
    widget.resize(100, 40)
    widget.show()
    spy = QSignalSpy(widget.activated)
    QTest.mousePress(widget, Qt.LeftButton, pos=QPoint(50, 20))
    QTest.mouseRelease(widget, Qt.LeftButton, pos=QPoint(500, 500))
    assert spy.count() == 0


def test_release_without_press_does_not_activate(qapp):
    widget = ClickableWidget()
    widget.resize(100, 40)
    widget.show()
    spy = QSignalSpy(widget.activated)
    QTest.mouseRelease(widget, Qt.LeftButton, pos=QPoint(50, 20))
    assert spy.count() == 0


def test_right_click_does_not_activate(qapp):
    widget = ClickableWidget()
    widget.resize(100, 40)
    widget.show()
    spy = QSignalSpy(widget.activated)
    QTest.mouseClick(widget, Qt.RightButton, pos=QPoint(50, 20))
    assert spy.count() == 0


def test_thumbnail_requested_only_when_shown(qapp):
    cache = FakeThumbnails()
    thumb = LazyThumbnail(48)
    thumb.set_source("http://x/1", cache)
    assert cache.requests == []
    thumb.show()
    assert cache.requests == ["http://x/1"]
    thumb.hide()
    thumb.show()
    assert cache.requests == ["http://x/1"]


def test_thumbnail_requested_immediately_if_already_visible(qapp):
    cache = FakeThumbnails()
    thumb = LazyThumbnail(48)
    thumb.show()
    thumb.set_source("http://x/2", cache)
    assert cache.requests == ["http://x/2"]


def test_thumbnail_without_url_never_requests(qapp):
    cache = FakeThumbnails()
    thumb = LazyThumbnail(48)
    thumb.set_source("", cache)
    thumb.show()
    assert cache.requests == []


def test_actions_button_keeps_its_space_when_hidden(qapp):
    button = TrackActionsButton()
    button.show()
    width = button.width()
    assert not button.isEnabled() and button.icon().isNull()
    button.set_revealed(True)
    assert button.isEnabled() and not button.icon().isNull() and button.width() == width
    button.set_revealed(False)
    assert not button.isEnabled() and button.icon().isNull()


def choose_from_open_menu(index, row=None, log=None):
    def choose():
        menu = next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible())
        if row is not None:
            QApplication.sendEvent(row, QEvent(QEvent.Leave))
        if log is not None:
            log.append(menu.isEnabled())
        menu.setActiveAction(menu.actions()[index])
        QTest.keyClick(menu, Qt.Key_Return)
    QTimer.singleShot(50, choose)


def test_song_menu_offers_play_next_queue_and_playlist(qapp):
    button = TrackActionsButton()
    button.show()
    seen = []
    QTimer.singleShot(50, lambda: (seen.extend(
        a.text() for a in next(w for w in QApplication.topLevelWidgets()
                               if isinstance(w, QMenu) and w.isVisible()).actions()),
        next(w for w in QApplication.topLevelWidgets() if isinstance(w, QMenu) and w.isVisible()).close()))
    button.set_revealed(True)
    button.click()
    assert seen == ["Reproducir a continuación", "Agregar a la cola", "Agregar a una playlist"]


def test_song_menu_choices_work_even_when_the_row_loses_hover(qapp):
    for index, name in enumerate(("add_next", "add_queue", "add_playlist")):
        row = CompactSongItem(song(1), FakeThumbnails())
        row.resize(380, 60)
        row.move(400, 400)
        row.show()
        got, menu_enabled = [], []
        getattr(row, name).connect(got.append)
        QApplication.sendEvent(row, QEvent(QEvent.Enter))
        choose_from_open_menu(index, row, menu_enabled)
        row._actions.click()
        assert got == [song(1)] and menu_enabled == [True], name
        assert not row._actions.isEnabled()


def test_song_menu_dismissed_emits_nothing(qapp):
    row = CompactSongItem(song(1), FakeThumbnails())
    row.show()
    got = []
    for name in ("add_next", "add_queue", "add_playlist"):
        getattr(row, name).connect(got.append)
    QApplication.sendEvent(row, QEvent(QEvent.Enter))
    QTimer.singleShot(50, lambda: next(w for w in QApplication.topLevelWidgets()
                                       if isinstance(w, QMenu) and w.isVisible()).close())
    row._actions.click()
    assert got == [] and row._actions.isEnabled()


def saved_playlists(n=5):
    return [{"playlistId": f"p{i}", "title": f"Lista {i}", "source": "local" if i % 2 else "ytmusic",
             "track_count": i * 10, "thumbnails": []} for i in range(1, n + 1)]


def test_save_dialog_shows_recent_tiles_and_every_playlist(qapp):
    from ui.components.save_to_playlist_dialog import SaveToPlaylistDialog, _PlaylistRow, _RecentTile

    playlists = saved_playlists()
    dialog = SaveToPlaylistDialog({"recent": playlists[:2], "all": playlists}, FakeThumbnails())
    dialog.show()
    assert len(dialog.findChildren(_RecentTile)) == 2 and len(dialog.findChildren(_PlaylistRow)) == 5
    assert dialog.choice is None


def test_save_dialog_choosing_a_row_or_tile_accepts_it(qapp):
    from ui.components.save_to_playlist_dialog import SaveToPlaylistDialog, _PlaylistRow, _RecentTile

    playlists = saved_playlists()
    dialog = SaveToPlaylistDialog({"recent": playlists[:1], "all": playlists}, FakeThumbnails())
    dialog.show()
    QTest.mouseClick(dialog.findChildren(_PlaylistRow)[2], Qt.LeftButton, pos=QPoint(40, 20))
    assert dialog.choice == ("existing", playlists[2]) and dialog.result() == QDialog.Accepted

    again = SaveToPlaylistDialog({"recent": playlists[:1], "all": playlists}, FakeThumbnails())
    again.show()
    QTest.mouseClick(again.findChildren(_RecentTile)[0], Qt.LeftButton, pos=QPoint(40, 40))
    assert again.choice == ("existing", playlists[0])


def test_save_dialog_without_recents_or_playlists(qapp):
    from ui.components.save_to_playlist_dialog import SaveToPlaylistDialog, _RecentTile

    dialog = SaveToPlaylistDialog({"recent": [], "all": []}, FakeThumbnails())
    dialog.show()
    assert dialog.findChildren(_RecentTile) == []
    texts = [label.text() for label in dialog.findChildren(QLabel)]
    assert "Recientes" not in texts and any("Nueva playlist" in t for t in texts)


def test_save_dialog_new_playlist_asks_for_a_name(qapp, monkeypatch):
    from ui.components.save_to_playlist_dialog import SaveToPlaylistDialog

    dialog = SaveToPlaylistDialog({"recent": [], "all": []}, FakeThumbnails())
    monkeypatch.setattr(dialogs, "prompt_text", lambda *a, **k: "Gym")
    dialog.new_button.click()
    assert dialog.choice == ("new", "Gym")

    cancelled = SaveToPlaylistDialog({"recent": [], "all": []}, FakeThumbnails())
    monkeypatch.setattr(dialogs, "prompt_text", lambda *a, **k: None)
    cancelled.new_button.click()
    assert cancelled.choice is None


def test_save_dialog_counts_are_readable(qapp):
    from ui.components.save_to_playlist_dialog import _count_text

    assert _count_text({"track_count": 49}, "pista", "pistas") == "49 pistas"
    assert _count_text({"track_count": 1}, "pista", "pistas") == "1 pista"
    assert _count_text({"track_count": "1,200 songs"}, "pista", "pistas") == "1200 pistas"
    assert _count_text({"track_count": 0}, "pista", "pistas") == ""
    assert _count_text({}, "pista", "pistas") == "" and _count_text({"track_count": "many"}, "pista", "pistas") == ""


def count_sections(panel):
    layout = panel.feed._layout
    return sum(1 for i in range(layout.count() - 1)
               if isinstance(layout.itemAt(i).widget(), (CardsSection, CompactSection)))


def card_count(section):
    return section._row.count()


def test_carousel_builds_only_cards_in_range(qapp):
    cache = FakeThumbnails()
    section = CardsSection("T", [playlist(i) for i in range(60)], cache)
    section.resize(1200, 300)
    section.show()
    assert card_count(section) < 10
    assert len(cache.requests) == card_count(section)
    section._go_next()
    assert card_count(section) < 20


def test_carousel_shows_a_partial_card_at_the_edge(qapp):
    section = CardsSection("T", [playlist(i) for i in range(30)], FakeThumbnails())
    section.resize(1000, 300)
    section.show()
    card_width = CARD_SIZE + 12
    starts = [i * CardsSection.SLOT for i in range(card_count(section))]
    assert any(x < 1000 < x + card_width for x in starts)
    assert section._content_width() > 1000


def test_carousel_arrow_slides_by_a_page_with_animation(qapp):
    section = CardsSection("T", [playlist(i) for i in range(30)], FakeThumbnails())
    section.resize(1000, 300)
    section.show()
    assert section._view.offset == 0 and not section._header.prev.isEnabled()
    section._go_next()
    step = (1000 // CardsSection.SLOT) * CardsSection.SLOT
    assert section._target == step and section._header.prev.isEnabled()
    seen_moving = False
    for _ in range(60):
        QTest.qWait(10)
        if 0 < section._view.offset < step:
            seen_moving = True
            break
    assert seen_moving
    QTest.qWait(600)
    assert section._view.offset == step
    assert section._view.track.pos().x() == -step


def test_carousel_stops_at_the_end(qapp):
    section = CardsSection("T", [playlist(i) for i in range(7)], FakeThumbnails())
    section.resize(1000, 300)
    section.show()
    for _ in range(10):
        section._go_next()
    assert section._target == section._max_offset() > 0 and not section._header.next.isEnabled()
    for _ in range(10):
        section._go_prev()
    assert section._target == 0 and not section._header.prev.isEnabled()


def test_short_carousel_needs_no_arrows(qapp):
    section = CardsSection("T", [playlist(i) for i in range(2)], FakeThumbnails())
    section.resize(1000, 300)
    section.show()
    assert not section._header.next.isEnabled() and not section._header.prev.isEnabled()


def test_carousel_keeps_position_valid_when_resized(qapp):
    section = CardsSection("T", [playlist(i) for i in range(12)], FakeThumbnails())
    section.resize(600, 300)
    section.show()
    for _ in range(10):
        section._go_next()
    QTest.qWait(500)
    section.resize(1500, 300)
    assert section._target == section._max_offset() and section._view.offset == section._target


def test_carousel_never_forces_the_feed_wider_than_the_window(qapp):
    section = CardsSection("T", [playlist(i) for i in range(20)], FakeThumbnails())
    assert section.minimumSizeHint().width() < 5 * 222


def test_artist_cards_get_round_art_and_label(qapp):
    from ui.components.section_feed import HomeCard

    card = HomeCard({"type": "artist", "browseId": "UC1", "title": "Someone", "thumbnails": []}, FakeThumbnails())
    assert card.thumb._circle is True
    assert "Artista" in [label.text() for label in card.findChildren(QLabel)]


def test_compact_section_pages_slide(qapp):
    section = CompactSection("T", [song(i) for i in range(30)], FakeThumbnails())
    section.resize(1000, 400)
    section.show()
    assert section.page_count == 3 and len(section._pages) == 1
    assert not section._header.prev.isEnabled() and section._header.next.isEnabled()
    section._go_next()
    assert len(section._pages) == 2 and section._page == 1
    QTest.qWait(600)
    assert section._view.offset == 1000
    section._go_next()
    section._go_next()
    assert section._page == 2 and not section._header.next.isEnabled()
    section._go_prev()
    assert section._page == 1


def test_compact_section_relayouts_on_resize(qapp):
    section = CompactSection("T", [song(i) for i in range(30)], FakeThumbnails())
    section.resize(1000, 400)
    section.show()
    section._go_next()
    QTest.qWait(600)
    section.resize(700, 400)
    assert section._view.offset == 700 and section._pages[1].x() == 700


def test_home_builds_sections_lazily_then_on_scroll(qapp):
    panel = HomePanel()
    panel.resize(1000, 600)
    panel.show()
    sections = [(f"Section {i}", [playlist(j) for j in range(6)]) for i in range(25)]
    panel.set_sections(sections, FakeThumbnails())
    QApplication.processEvents()
    initial = count_sections(panel)
    assert 0 < initial < 25
    bar = panel.feed._scroll.verticalScrollBar()
    for _ in range(40):
        bar.setValue(bar.maximum())
        QApplication.processEvents()
    assert count_sections(panel) == 25


def test_home_empty_and_loading_states(qapp):
    panel = HomePanel()
    panel.show()
    panel.set_loading()
    assert panel.feed._message.isVisible() and panel.feed._message.text() == "Cargando…"
    panel.set_sections([("Empty", [])], FakeThumbnails())
    assert "No hay contenido" in panel.feed._message.text()
    panel.set_sections([("S", [playlist(1)])], FakeThumbnails())
    assert not panel.feed._message.isVisible() and count_sections(panel) == 1


def test_home_replaces_previous_sections(qapp):
    panel = HomePanel()
    panel.resize(1000, 600)
    panel.show()
    panel.set_sections([("A", [playlist(1)]), ("B", [playlist(2)])], FakeThumbnails())
    panel.set_sections([("C", [playlist(3)])], FakeThumbnails())
    QApplication.processEvents()
    assert count_sections(panel) == 1


def test_mood_chip_selection_emits_and_highlights(qapp):
    panel = HomePanel()
    spy = QSignalSpy(panel.mood_selected)
    chip = next(c for c in panel._chips if c.text() == "Fiesta")
    chip.click()
    assert spy.count() == 1 and spy.at(0) == ["Fiesta"]
    assert [c.text() for c in panel._chips if c.isChecked()] == ["Fiesta"]


def test_play_all_emits_the_section_songs(qapp):
    section = CompactSection("T", [song(i) for i in range(3)], FakeThumbnails())
    received = []
    section.play_all_requested.connect(received.append)
    next(b for b in section.findChildren(QPushButton) if b.text() == "Reproducir todo").click()
    assert [s["videoId"] for s in received[0]] == ["v0", "v1", "v2"]


def rows_of(panel):
    return [panel._layout.itemAt(i).widget() for i in range(panel._layout.count() - 1)]


def test_search_shows_artist_hero_with_name(qapp):
    panel = SearchPanel()
    artist = {"resultType": "artist", "subscribers": "1M", "artists": [{"name": "Daft Punk", "id": "UC1"}]}
    panel.show_results({"top_result": artist, "songs": [], "more": []}, FakeThumbnails())
    hero = next(w for w in rows_of(panel) if isinstance(w, _ArtistHero))
    assert "Daft Punk" in [label.text() for label in hero.findChildren(QLabel)]


def test_search_non_artist_top_result_becomes_a_row(qapp):
    panel = SearchPanel()
    top = {"resultType": "song", "videoId": "t", "title": "Top", "artists": [{"name": "X"}]}
    panel.show_results({"top_result": top, "songs": [{"resultType": "song", "videoId": "s", "title": "S"}],
                        "more": []}, FakeThumbnails())
    widgets = rows_of(panel)
    assert not any(isinstance(w, _ArtistHero) for w in widgets)
    assert sum(isinstance(w, _ResultRow) for w in widgets) == 2


def test_search_no_results_message(qapp):
    panel = SearchPanel()
    panel.show_results({"top_result": None, "songs": [], "more": []}, FakeThumbnails())
    assert "Sin resultados" in rows_of(panel)[0].text()


def test_search_row_click_emits_item(qapp):
    panel = SearchPanel()
    panel.resize(800, 600)
    panel.show()
    item = {"resultType": "song", "videoId": "s", "title": "S", "artists": [{"name": "X"}]}
    panel.show_results({"top_result": None, "songs": [item], "more": []}, FakeThumbnails())
    got = []
    panel.item_clicked.connect(got.append)
    row = next(w for w in rows_of(panel) if isinstance(w, _ResultRow))
    QTest.mouseClick(row, Qt.LeftButton, pos=QPoint(20, 20))
    assert got == [item]


def test_artist_row_hides_the_actions_button(qapp):
    row = _ResultRow({"resultType": "artist", "artists": [{"name": "X", "id": "UC"}]}, FakeThumbnails())
    assert row._actions.isHidden()


def test_artist_hero_shuffle_emits_the_artist(qapp):
    artist = {"resultType": "artist", "artists": [{"name": "X", "id": "UC1"}]}
    hero = _ArtistHero(artist, FakeThumbnails())
    got = []
    hero.shuffle_clicked.connect(got.append)
    hero.findChild(QPushButton).click()
    assert got == [artist]


def _enter(widget):
    QApplication.sendEvent(widget, QEnterEvent(QPoint(5, 5), QPoint(5, 5), QPoint(5, 5)))


def test_dwell_fires_after_resting_and_not_on_a_quick_pass(qapp):
    widget = ClickableWidget(dwell_ms=40)
    widget.resize(100, 40)
    widget.move(400, 400)
    widget.show()
    spy = QSignalSpy(widget.dwelled)
    _enter(widget)
    QApplication.sendEvent(widget, QEvent(QEvent.Leave))
    QTest.qWait(80)
    assert spy.count() == 0
    _enter(widget)
    QTest.qWait(120)
    assert spy.count() == 1


def test_dwell_cancelled_by_press(qapp):
    widget = ClickableWidget(dwell_ms=60)
    widget.resize(100, 40)
    widget.move(400, 400)
    widget.show()
    spy = QSignalSpy(widget.dwelled)
    _enter(widget)
    QTest.mousePress(widget, Qt.LeftButton, pos=QPoint(5, 5))
    QTest.qWait(120)
    assert spy.count() == 0


def test_dwell_disabled_by_default_and_for_non_song_rows(qapp):
    assert ClickableWidget()._dwell_timer is None
    artist_row = _ResultRow({"resultType": "artist", "artists": [{"name": "X"}]}, FakeThumbnails())
    assert artist_row._dwell_timer is None
    song_row = _ResultRow({"resultType": "song", "videoId": "v", "title": "T"}, FakeThumbnails())
    assert song_row._dwell_timer is not None


def test_side_panel_has_a_fixed_width_and_evenly_sized_tabs(qapp):
    from ui.components.side_panel import PANEL_WIDTH, SidePanel

    panel = SidePanel()
    panel.show()
    assert panel.minimumWidth() == panel.maximumWidth() == PANEL_WIDTH
    widths = [panel._tab_group.button(i).width() for i in range(3)]
    assert max(widths) - min(widths) <= 1
    assert sum(widths) >= PANEL_WIDTH - 40


def test_side_panel_tab_switching_and_signals(qapp):
    from ui.components.side_panel import SidePanel

    panel = SidePanel()
    spy = QSignalSpy(panel.similar_tab_opened)
    panel._select_tab(1)
    assert panel.current_tab() == 1 and spy.count() == 0
    panel.set_lyrics_message("x", focus=False)
    panel._select_tab(2)
    assert panel.is_similar_tab_active() and spy.count() == 1
    panel.set_lyrics_message("y", focus=True)
    assert panel.current_tab() == 1 and panel._tab_group.button(1).isChecked()


def related(n_songs=20, n_cards=6):
    return {
        "songs": [dict(song(i), type="song") for i in range(n_songs)],
        "playlists": [playlist(i) for i in range(n_cards)],
        "artists": [{"type": "artist", "browseId": f"UC{i}", "title": f"A{i}", "subscribers": "1 M",
                     "thumbnails": []} for i in range(n_cards)],
    }


def test_similar_tab_shows_three_sections_with_song_columns(qapp):
    from ui.components.side_panel import SidePanel

    panel = SidePanel()
    panel.resize(420, 800)
    panel.show()
    panel.set_similar(related(), FakeThumbnails())
    sections = [panel._similar_layout.itemAt(i).widget() for i in range(3)]
    songs, playlists, artists = sections
    assert isinstance(songs, CompactSection) and isinstance(playlists, CardsSection)
    assert songs.page_count == 5 and songs._page_size == 4
    assert len(songs._pages) == 1
    assert playlists._card_size == 150 and artists._card_size == 130


def test_similar_song_columns_slide_and_peek(qapp):
    songs = CompactSection("T", [song(i) for i in range(20)], FakeThumbnails(), columns=1, rows=4,
                           play_all=False, peek=36)
    songs.resize(380, 400)
    songs.show()
    page_width = 380 - 36
    assert songs._pages[0].width() == page_width
    songs._go_next()
    assert songs._pages[1].x() == page_width + CompactSection.GAP
    assert songs._pages[1].x() < 380
    QTest.qWait(600)
    assert songs._view.offset == page_width + CompactSection.GAP
    for _ in range(10):
        songs._go_next()
    assert songs._page == 4 and not songs._header.next.isEnabled()
    for _ in range(10):
        songs._go_prev()
    assert songs._page == 0 and not songs._header.prev.isEnabled()


def test_similar_tab_states(qapp):
    from ui.components.side_panel import SidePanel

    panel = SidePanel()
    panel.set_similar({"songs": [], "playlists": [], "artists": []}, FakeThumbnails())
    assert "No hay contenido similar" in panel._similar_layout.itemAt(0).widget().text()
    panel.set_similar({"songs": [], "playlists": [playlist(1)], "artists": []}, FakeThumbnails())
    assert panel._similar_layout.count() == 2
    panel.set_similar_loading()
    assert panel._similar_layout.itemAt(0).widget().text() == "Cargando…"
    panel.clear_similar()
    assert panel._similar_layout.count() == 1


def test_now_playing_cover_is_a_plain_rounded_square(qapp):
    from PySide6.QtGui import QPixmap
    from ui.components.now_playing_panel import COVER_RADIUS, MARGIN, NowPlayingPanel

    panel = NowPlayingPanel()
    panel.resize(900, 700)
    pixmap = QPixmap(300, 200)
    pixmap.fill(Qt.red)
    panel.set_cover(pixmap)
    assert panel._cover.width() == panel._cover.height() == 700 - 2 * MARGIN
    assert not hasattr(panel, "_bg_tiny") and not hasattr(panel, "_tint")
    corner = panel._cover.toImage().pixelColor(0, 0)
    assert corner.alpha() == 0 and COVER_RADIUS > 0
    centre = panel._cover.toImage().pixelColor(panel._cover.width() // 2, panel._cover.height() // 2)
    assert centre.alpha() == 255
    panel.set_cover(QPixmap())
    assert panel._cover is None


def test_long_section_title_never_pushes_the_arrows_out(qapp):
    section = CardsSection("Un título extremadamente largo que no cabe en el panel lateral", [playlist(1)] * 8,
                           FakeThumbnails(), card_size=150, title_px=16)
    section.resize(380, 300)
    section.show()
    header = section._header
    assert header.next.geometry().right() <= 380 and header.prev.geometry().left() > 0


def test_covers_hold_real_pixels_on_scaled_displays(qapp):
    from PySide6.QtGui import QPixmap
    from ui.imaging import circle_pixmap, round_pixmap, scale_cover

    source = QPixmap(600, 400)
    source.fill(Qt.red)
    cover = scale_cover(source, 100, 1.5)
    assert cover.width() == cover.height() == 150 and cover.devicePixelRatio() == 1.5
    assert round(cover.deviceIndependentSize().width()) == 100
    rounded = round_pixmap(cover, 10)
    assert rounded.size() == cover.size() and rounded.devicePixelRatio() == 1.5
    assert rounded.toImage().pixelColor(0, 0).alpha() == 0
    assert rounded.toImage().pixelColor(75, 75).alpha() == 255
    circle = circle_pixmap(source, 60, 2.0)
    assert circle.width() == 120 and circle.toImage().pixelColor(0, 0).alpha() == 0
    plain = scale_cover(source, 100)
    assert plain.width() == 100 and plain.devicePixelRatio() == 1.0


def test_prompt_dialog_needs_a_name_before_ok(qapp):
    dialog = dialogs.PromptDialog(None, "Nueva playlist", "Nombre", ok="Crear")
    dialog.show()
    assert not dialog.ok_button.isEnabled()
    dialog.field.setText("   ")
    assert not dialog.ok_button.isEnabled()
    dialog.field.setText("  Gym  ")
    assert dialog.ok_button.isEnabled() and dialog.ok_button.text() == "Crear"
    dialog.ok_button.click()
    assert dialog.value == "Gym" and dialog.result() == QDialog.Accepted


def test_prompt_dialog_enter_accepts_and_cancel_rejects(qapp):
    dialog = dialogs.PromptDialog(None, "T", text="Mi Cola", ok="Guardar")
    dialog.show()
    QTest.keyClick(dialog.field, Qt.Key_Return)
    assert dialog.value == "Mi Cola"
    other = dialogs.PromptDialog(None, "T", text="x")
    other.show()
    QTest.keyClick(other, Qt.Key_Escape)
    assert other.value is None and other.result() == QDialog.Rejected


def test_prompt_dialog_buttons_are_large_and_ok_is_the_default(qapp):
    dialog = dialogs.PromptDialog(None, "T", text="x")
    dialog.show()
    buttons = dialog.findChildren(QPushButton)
    assert len(buttons) == 2 and all(b.height() >= 40 and b.width() >= 100 for b in buttons)
    assert dialog.ok_button.isDefault()


def test_multiline_prompt_reads_the_whole_text(qapp):
    dialog = dialogs.PromptDialog(None, "cURL", "pasos", ok="Iniciar", multiline=True)
    dialog.show()
    dialog.field.setPlainText("curl a\n  -H b  ")
    dialog.ok_button.click()
    assert dialog.value == "curl a\n  -H b"


def test_confirm_and_choice_dialogs(qapp):
    confirm = dialogs.ConfirmDialog(None, "¿Seguro?", "Se borrará", ok="Borrar")
    confirm.show()
    assert [b.text() for b in confirm.findChildren(QPushButton)] == ["Cancelar", "Borrar"]
    notice = dialogs.ConfirmDialog(None, "Aviso", "Listo", ok="Entendido", cancel=None)
    assert [b.text() for b in notice.findChildren(QPushButton)] == ["Entendido"]

    choice = dialogs.ChoiceDialog(None, "Guardar", "¿Dónde?", [("En este equipo", "local"), ("En YouTube Music", "cloud")])
    choice.show()
    next(b for b in choice.findChildren(QPushButton) if b.text() == "En YouTube Music").click()
    assert choice.value == "cloud" and choice.result() == QDialog.Accepted
    dismissed = dialogs.ChoiceDialog(None, "Guardar", "¿Dónde?", [("A", "a")])
    dismissed.reject()
    assert dismissed.value is None


def test_modal_dims_the_window_while_it_is_open(qapp):
    from PySide6.QtWidgets import QWidget

    host = QWidget()
    host.resize(600, 400)
    host.show()
    dialog = dialogs.ConfirmDialog(host, "T", "m")
    seen = []
    QTimer.singleShot(50, lambda: (seen.append([w for w in host.children()
                                                if isinstance(w, QWidget) and w.geometry() == host.rect()]),
                                   dialog.accept()))
    dialog.exec()
    QApplication.processEvents()
    assert len(seen[0]) == 1
