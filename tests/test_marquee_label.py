from ui.components.marquee_label import GAP_PX, MarqueeLabel


def test_marquee_scrolls_only_long_titles_loops_and_idles_when_hidden(qapp):
    label = MarqueeLabel("corto")
    label.resize(200, 20)
    label.show()
    assert not label.scrolling
    label.setText("薔薇は美しく散る - Bara Ha Utsukushiku Chiru " * 3)
    assert label.overflowing() and label.scrolling and label.offset == 0
    for _ in range(label.text_width() + GAP_PX):
        label._advance()
    assert label.offset == 0 and label.scrolling
    label._advance()
    assert label.offset == 1
    label.hide()
    assert not label.scrolling and label.offset == 0
    label.show()
    label.setText("corto")
    assert not label.scrolling
    label.close()
