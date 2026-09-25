from PySide6.QtTest import QTest

from tests.test_ui import FakeThumbnails, playlist
from ui.components.section_feed import SectionFeed


def shelves(prefix, offset):
    return [(f"{prefix} {n}", [playlist(offset + n * 10 + k) for k in range(8)]) for n in range(8)]


def test_feed_rebuilds_after_replacing_a_tall_feed(qapp):
    feed = SectionFeed()
    feed.resize(1200, 700)
    feed.show()
    feed.set_sections(shelves("Estante", 0), FakeThumbnails())
    QTest.qWait(50)
    assert len(feed._built) >= 2
    feed.set_sections(shelves("Nuevo", 500), FakeThumbnails(), reset_scroll=False)
    QTest.qWait(50)
    assert feed._built, "the new feed must render without waiting for a view switch"
    feed.close()
    feed.deleteLater()
    QTest.qWait(10)
