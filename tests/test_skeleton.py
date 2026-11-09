from ui.components.section_feed import SectionFeed
from ui.components.skeleton import FeedSkeleton


def song(n):
    return {"videoId": f"v{n}", "title": f"T{n}", "artists": [{"name": "A"}], "type": "song", "thumbnails": []}


def test_loading_shows_a_shimmering_skeleton_instead_of_text(qapp):
    feed = SectionFeed()
    feed.resize(900, 700)
    feed.show()
    feed.set_loading()
    skeleton = feed.findChild(FeedSkeleton)
    assert skeleton is not None and skeleton.isVisible() and skeleton._timer.isActive()
    assert not feed._message.isVisible()
    feed.close()


def test_content_or_message_replaces_the_skeleton_and_stops_its_timer(qapp):
    feed = SectionFeed()
    feed.resize(900, 700)
    feed.show()
    feed.set_loading()
    skeleton = feed.findChild(FeedSkeleton)
    feed.set_sections([("Quick picks", [song(i) for i in range(6)])], None)
    assert not skeleton.isVisible() and not skeleton._timer.isActive()
    feed.set_loading()
    feed.show_message("Sin conexión")
    assert not skeleton.isVisible() and feed._message.isVisible()
    feed.close()


def test_skeleton_paints_under_every_theme(qapp):
    from ui import theme
    try:
        for name in theme.THEMES:
            theme.apply(name)
            skeleton = FeedSkeleton()
            skeleton.resize(800, 600)
            assert not skeleton.grab().isNull()
    finally:
        theme.apply("classic")
