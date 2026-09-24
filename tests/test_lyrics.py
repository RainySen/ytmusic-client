import json

import pytest

from bootstrap import build_lyrics_providers
from config import AppPaths
from domain.lyrics_parsing import parse_lrc, parse_ttml, plain_lyrics
from domain.models import LyricLine, Lyrics, LyricsQuery, LyricWord, clean_title, lyrics_query
from infra.concurrency import TaskRunner
from infra.lyrics_providers import BetterLyricsProvider, LrcLibProvider, YouTubeMusicProvider
from infra.lyrics_settings import DEFAULT_PROVIDERS, load_lyrics_settings
from services.lyrics_service import PROVIDER_COOLDOWN_S, LyricsService
from ui.components.side_panel import SidePanel

TTML = """<?xml version="1.0" encoding="UTF-8"?>
<tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttm="http://www.w3.org/ns/ttml#metadata">
<body><div>
<p begin="0:12.000" end="0:15.500"><span begin="0:12.000" end="0:12.400">Hel</span><span begin="0:12.400" end="0:12.900">lo</span> <span begin="0:13.000" end="0:13.500">world</span><span ttm:role="x-translation">Hola mundo</span></p>
<p begin="0:16.000" end="0:18.000">Only line text</p>
</div></body></tt>"""


def test_lrc_lines_times_and_metadata():
    lyrics = parse_lrc("[ar:Artist]\n[ti:Title]\n[00:01.50]first\n[00:05.00]second\n[01:02.5]third\n", "LRCLIB")
    assert lyrics.synced and lyrics.source == "LRCLIB" and not lyrics.word_synced
    assert [(l.text, l.time_ms) for l in lyrics.lines] == [("first", 1500), ("second", 5000), ("third", 62500)]
    assert [l.end_ms for l in lyrics.lines] == [5000, 62500, 62500]


def test_lrc_fraction_digits_and_multiple_stamps_and_sorting():
    lyrics = parse_lrc("[00:10.123]b\n[00:02.5][00:30.00]chorus\n[00:05.05]a")
    assert [(l.text, l.time_ms) for l in lyrics.lines] == [
        ("chorus", 2500), ("a", 5050), ("b", 10123), ("chorus", 30000)]


def test_lrc_strips_enhanced_word_tags_and_marks_instrumental_gaps():
    lyrics = parse_lrc("[00:01.00]<00:01.00>Hel <00:01.50>lo\n[00:05.00]\n[00:09.00]next\n[00:12.00]\n")
    assert [l.text for l in lyrics.lines] == ["Hel lo", "♪", "next"]


def test_lrc_without_usable_lines_is_none():
    assert parse_lrc(None) is None and parse_lrc("") is None
    assert parse_lrc("[ar:x]\njust text") is None and parse_lrc("[00:01.00]\n") is None


def test_plain_lyrics():
    lyrics = plain_lyrics("a\nb\n\nc\n", "LRCLIB")
    assert not lyrics.synced and lyrics.texts == ["a", "b", "", "c"] and lyrics.source == "LRCLIB"
    assert plain_lyrics("  \n") is None and plain_lyrics(None) is None


def test_ttml_syllables_words_and_skipped_translations():
    lyrics = parse_ttml(TTML, "Better Lyrics")
    assert lyrics.synced and lyrics.word_synced and lyrics.source == "Better Lyrics"
    first, second = lyrics.lines
    assert first.text == "Hello world" and first.time_ms == 12000 and first.end_ms == 15500
    assert [(w.text, w.start_ms, w.end_ms) for w in first.words] == [
        ("Hel", 12000, 12400), ("lo ", 12400, 12900), ("world", 13000, 13500)]
    assert second.text == "Only line text" and second.words == () and second.time_ms == 16000


def test_ttml_clock_formats():
    doc = ('<tt xmlns="http://www.w3.org/ns/ttml"><body><div>'
           '<p begin="1:02.500" end="1:04"><span begin="1:02.500" end="1:03">a</span></p>'
           '<p begin="12.5s" end="14s"><span begin="12.5s" end="13s">b</span></p>'
           '<p begin="01:02:03.000" end="01:02:04.000"><span begin="01:02:03.000" end="01:02:04.000">c</span></p>'
           '</div></body></tt>')
    lyrics = parse_ttml(doc)
    assert [(l.text, l.time_ms) for l in lyrics.lines] == [("b", 12500), ("a", 62500), ("c", 3723000)]


def test_ttml_missing_word_ends_and_untimed_spans_get_sensible_times():
    doc = ('<tt xmlns="http://www.w3.org/ns/ttml"><body><div><p begin="0:10.0" end="0:14.0">'
           '<span begin="0:10.0">one</span> <span begin="0:11.0">two</span> <span>three</span></p></div></body></tt>')
    words = parse_ttml(doc).lines[0].words
    assert [(w.text, w.start_ms, w.end_ms) for w in words] == [
        ("one ", 10000, 11000), ("two ", 11000, 11000), ("three", 11000, 14000)]


def test_ttml_nested_background_vocals_are_flattened_in_order():
    doc = ('<tt xmlns="http://www.w3.org/ns/ttml" xmlns:ttm="http://www.w3.org/ns/ttml#metadata"><body><div>'
           '<p begin="0:01.0" end="0:05.0"><span begin="0:01.0" end="0:02.0">Main</span> '
           '<span ttm:role="x-bg"><span begin="0:02.0" end="0:03.0">(echo)</span></span>'
           '<span ttm:role="x-roman">roman</span></p></div></body></tt>')
    line = parse_ttml(doc).lines[0]
    assert line.text == "Main (echo)" and [w.text for w in line.words] == ["Main ", "(echo)"]


def test_ttml_refuses_entities_bad_xml_and_empty_documents():
    assert parse_ttml('<!DOCTYPE x [<!ENTITY a "aaaa">]><tt><body><p begin="0:01">&a;</p></body></tt>') is None
    assert parse_ttml("<tt><body><p") is None
    assert parse_ttml(None) is None and parse_ttml("") is None
    assert parse_ttml('<tt xmlns="http://www.w3.org/ns/ttml"><body><div><p begin="0:01.0">  </p></div></body></tt>') is None


def test_ttml_paragraphs_without_a_start_are_skipped():
    doc = '<tt xmlns="http://www.w3.org/ns/ttml"><body><div><p>no time</p><p begin="0:02.0">ok</p></div></body></tt>'
    assert [l.text for l in parse_ttml(doc).lines] == ["ok"]


def test_titles_lose_their_noise():
    assert clean_title("Song (Official Video) [HD]") == "Song"
    assert clean_title("Artist - Topic") == "Artist"
    assert clean_title("(Only Brackets)") == "(Only Brackets)"
    assert clean_title("Plain") == "Plain" and clean_title("") == ""


def test_query_from_a_track():
    query = lyrics_query({"videoId": "v", "title": "T (Live)", "artists": [{"name": "A"}, {"name": "B"}],
                          "album": {"name": "Al"}, "duration": "3:45"})
    assert query == LyricsQuery("v", "T (Live)", "A", "Al", 225)
    bare = lyrics_query({"videoId": "v", "title": "T", "album": "Plain album"})
    assert bare.artist == "" and bare.album == "Plain album" and bare.duration == 0
    assert lyrics_query({"videoId": "v", "duration_seconds": 200}).duration == 200


class Response:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, params=None, headers=None):
        self.calls.append((url, params, headers))
        return self.responses.pop(0)


QUERY = LyricsQuery("v1", "Instant Crush (Official Video)", "Daft Punk", "RAM", 337)
SYNCED = "[00:01.00]one\n[00:04.00]two"


def test_lrclib_exact_match_prefers_synced_lyrics():
    http = FakeHttp(Response(200, {"syncedLyrics": SYNCED, "plainLyrics": "one\ntwo"}))
    lyrics = LrcLibProvider(http).fetch(QUERY)
    assert lyrics.synced and lyrics.source == "LRCLIB" and lyrics.texts == ["one", "two"]
    url, params, _ = http.calls[0]
    assert url.endswith("/get") and params == {"artist_name": "Daft Punk", "track_name": "Instant Crush",
                                               "album_name": "RAM", "duration": 337}


def test_lrclib_uses_plain_lyrics_when_nothing_is_timed():
    lyrics = LrcLibProvider(FakeHttp(Response(200, {"syncedLyrics": None, "plainLyrics": "a\nb"}))).fetch(QUERY)
    assert not lyrics.synced and lyrics.texts == ["a", "b"]


def test_lrclib_falls_back_to_search_and_picks_the_closest_timed_match():
    candidates = [
        {"duration": 337, "syncedLyrics": None, "plainLyrics": "plain"},
        {"duration": 400, "syncedLyrics": "[00:01.00]far"},
        {"duration": 339, "syncedLyrics": "[00:01.00]near"},
        {"duration": 337, "syncedLyrics": "[00:01.00]exact"},
        {"duration": 337, "instrumental": True, "syncedLyrics": "[00:01.00]instrumental"},
    ]
    http = FakeHttp(Response(404), Response(200, candidates))
    lyrics = LrcLibProvider(http).fetch(QUERY)
    assert lyrics.texts == ["exact"]
    assert http.calls[1][0].endswith("/search") and http.calls[1][1]["track_name"] == "Instant Crush"


def test_lrclib_search_only_when_duration_or_album_is_unknown():
    http = FakeHttp(Response(200, [{"duration": 10, "syncedLyrics": "[00:01.00]x"}]))
    lyrics = LrcLibProvider(http).fetch(LyricsQuery("v", "T", "A"))
    assert lyrics.texts == ["x"] and len(http.calls) == 1 and http.calls[0][0].endswith("/search")


def test_lrclib_gives_nothing_for_instrumentals_unknowns_and_empty_queries():
    assert LrcLibProvider(FakeHttp(Response(200, {"instrumental": True}), Response(404))).fetch(QUERY) is None
    assert LrcLibProvider(FakeHttp(Response(404), Response(200, []))).fetch(QUERY) is None
    assert LrcLibProvider(FakeHttp()).fetch(LyricsQuery("v", "", "A")) is None
    assert LrcLibProvider(FakeHttp()).fetch(LyricsQuery("v", "T", "")) is None


def test_lrclib_errors_are_raised_so_the_service_can_back_off():
    with pytest.raises(RuntimeError):
        LrcLibProvider(FakeHttp(Response(500))).fetch(QUERY)


def test_better_lyrics_returns_syllable_timed_lyrics_and_sends_the_key():
    http = FakeHttp(Response(200, {"ttml": TTML}))
    lyrics = BetterLyricsProvider("secret", http).fetch(QUERY)
    assert lyrics.word_synced and lyrics.source == "Better Lyrics"
    url, params, headers = http.calls[0]
    assert url == "https://api.betterlyrics.org/getLyrics"
    assert params == {"s": "Instant Crush", "a": "Daft Punk", "al": "RAM", "d": 337} and headers == {"X-API-Key": "secret"}


def test_better_lyrics_without_a_key_sends_none_and_treats_refusals_as_no_answer():
    http = FakeHttp(Response(401, {"error": "API key required"}))
    assert BetterLyricsProvider("", http).fetch(QUERY) is None
    assert http.calls[0][2] == {}
    for status in (403, 404, 422):
        assert BetterLyricsProvider("", FakeHttp(Response(status))).fetch(QUERY) is None
    assert BetterLyricsProvider("", FakeHttp()).fetch(LyricsQuery("v", "", "A")) is None
    with pytest.raises(RuntimeError):
        BetterLyricsProvider("", FakeHttp(Response(502))).fetch(QUERY)
    assert BetterLyricsProvider("", FakeHttp(Response(200, {"ttml": "<broken"}))).fetch(QUERY) is None


def test_youtube_provider_wraps_the_gateway():
    class Gateway:
        def get_lyrics_browse_id(self, video_id):
            return "MPLY" if video_id == "v1" else None

        def get_lyrics(self, browse_id):
            return {"lyrics": "x\ny"}

    provider = YouTubeMusicProvider(Gateway())
    lyrics = provider.fetch(QUERY)
    assert lyrics.texts == ["x", "y"] and lyrics.source == "YouTube Music" and not lyrics.synced
    assert provider.fetch(LyricsQuery("other", "T", "A")) is None


def test_settings_defaults_order_and_key(tmp_path):
    missing = load_lyrics_settings(str(tmp_path / "none.json"), {})
    assert missing.providers == DEFAULT_PROVIDERS == ("betterlyrics", "lrclib", "youtube") and missing.better_lyrics_api_key == ""
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"providers": ["LRCLIB", "youtube"], "better_lyrics_api_key": "file-key"}))
    assert load_lyrics_settings(str(path), {}).providers == ("lrclib", "youtube")
    assert load_lyrics_settings(str(path), {}).better_lyrics_api_key == "file-key"
    assert load_lyrics_settings(str(path), {"BETTER_LYRICS_API_KEY": "env-key"}).better_lyrics_api_key == "env-key"
    path.write_text("not json")
    assert load_lyrics_settings(str(path), {}).providers == DEFAULT_PROVIDERS
    path.write_text(json.dumps({"providers": []}))
    assert load_lyrics_settings(str(path), {}).providers == DEFAULT_PROVIDERS


def test_providers_are_built_in_the_configured_order(tmp_path):
    (tmp_path / "lyrics_settings.json").write_text(json.dumps({"providers": ["youtube", "nonsense", "lrclib"]}))
    providers = build_lyrics_providers(AppPaths(str(tmp_path)), gateway=object())
    assert [p.name for p in providers] == ["YouTube Music", "LRCLIB"]
    default = build_lyrics_providers(AppPaths(str(tmp_path / "empty")), gateway=object())
    assert [p.name for p in default] == ["Better Lyrics", "LRCLIB", "YouTube Music"]


class Scripted:
    def __init__(self, name, result=None, error=None):
        self.name, self.result, self.error, self.calls = name, result, error, 0

    def fetch(self, query):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


TIMED = Lyrics((LyricLine("t", 1000),), synced=True, source="timed")
PLAIN = Lyrics((LyricLine("p"),), synced=False, source="plain")
SONG = {"videoId": "v1", "title": "T", "artists": [{"name": "A"}]}


@pytest.fixture
def make_service(qapp, wait_until):
    runners = []

    def build(*providers, clock=None):
        runner = TaskRunner("lyrics-test", 2)
        runners.append(runner)
        return LyricsService(list(providers), runner, **({"clock": clock} if clock else {}))

    def ask(service, song=SONG):
        box = []
        service.fetch(song, box.append)
        assert wait_until(lambda: box)
        return box[0]

    yield build, ask
    for runner in runners:
        runner.shutdown()


def test_first_timed_answer_wins_and_later_providers_are_not_asked(make_service):
    build, ask = make_service
    first, second = Scripted("a", TIMED), Scripted("b", PLAIN)
    assert ask(build(first, second)) is TIMED and second.calls == 0


def test_a_plain_answer_is_kept_while_looking_for_a_timed_one(make_service):
    build, ask = make_service
    service = build(Scripted("a", PLAIN), Scripted("b", None), Scripted("c", TIMED))
    assert ask(service) is TIMED
    assert ask(build(Scripted("a", PLAIN), Scripted("b", None))) is PLAIN
    assert ask(build(Scripted("a", None), Scripted("b", None))) is None


def test_failing_provider_is_skipped_for_a_while_then_retried(make_service):
    build, ask = make_service
    now = [1000.0]
    broken, working = Scripted("broken", error=RuntimeError("down")), Scripted("ok", TIMED)
    service = build(broken, working, clock=lambda: now[0])
    assert ask(service, dict(SONG, videoId="a")) is TIMED and broken.calls == 1
    assert ask(service, dict(SONG, videoId="b")) is TIMED and broken.calls == 1
    now[0] += PROVIDER_COOLDOWN_S + 1
    assert ask(service, dict(SONG, videoId="c")) is TIMED and broken.calls == 2


def test_answers_and_misses_are_cached_per_song(make_service):
    build, ask = make_service
    provider = Scripted("a", TIMED)
    service = build(provider)
    assert ask(service) is TIMED and ask(service) is TIMED and provider.calls == 1
    nothing = Scripted("n", None)
    service = build(nothing)
    assert ask(service) is None and ask(service) is None and nothing.calls == 1


def word_lyrics():
    line1 = LyricLine("Hello world", 1000, 4000, (LyricWord("Hel", 1000, 1400), LyricWord("lo ", 1400, 1900),
                                                  LyricWord("world", 2000, 3000)))
    line2 = LyricLine("Bye <now>", 5000, 7000, (LyricWord("Bye ", 5000, 5500), LyricWord("<now>", 5500, 6500)))
    return Lyrics((line1, line2), synced=True, source="Better Lyrics")


def label_html(panel, index):
    return panel._lyric_words[index][0].text()


def lit_words(panel, index):
    import re
    return [text for color, text in re.findall(r'color:(#\w+)">([^<]*)</span>', label_html(panel, index).replace("&lt;", "<"))
            if color == "#ffffff"]


def test_word_timed_lyrics_get_a_label_per_line_with_credit(qapp):
    panel = SidePanel()
    panel.show()
    panel.set_lyrics(word_lyrics())
    assert panel._lyrics.count() == 2 and set(panel._lyric_words) == {0, 1}
    assert not panel._lyrics_credit.isHidden() and panel._lyrics_credit.text() == "Letra: Better Lyrics"
    assert lit_words(panel, 0) == []
    assert "&lt;now&gt;" in label_html(panel, 1)


def test_words_light_up_as_they_are_sung_and_reset_on_the_next_line(qapp):
    panel = SidePanel()
    panel.show()
    panel.set_lyrics(word_lyrics())
    panel.set_lyric_progress(0, 1100)
    assert lit_words(panel, 0) == ["Hel"]
    panel.set_lyric_progress(0, 2100)
    assert lit_words(panel, 0) == ["Hel", "lo ", "world"]
    panel.set_lyric_progress(1, 5100)
    assert lit_words(panel, 0) == [] and lit_words(panel, 1) == ["Bye "]
    panel.set_lyric_progress(0, 1100)
    assert lit_words(panel, 0) == ["Hel"] and lit_words(panel, 1) == []
    panel.set_lyric_progress(9, 0)


def test_line_timed_and_plain_lyrics_use_plain_items(qapp):
    panel = SidePanel()
    panel.show()
    panel.set_lyrics(Lyrics((LyricLine("a", 1000), LyricLine("b", 2000)), synced=True, source="LRCLIB"))
    assert panel._lyric_words == {} and panel._lyrics.item(0).text() == "a"
    assert panel._lyrics_credit.text() == "Letra: LRCLIB"
    panel.set_lyrics(Lyrics((LyricLine("x"),), synced=False, source=""))
    assert panel._lyrics_credit.isHidden()
    panel.set_lyrics(word_lyrics())
    panel.set_lyrics_message("Letra no encontrada.")
    assert panel._lyric_words == {} and panel._lyrics_credit.isHidden()


def test_presenter_drives_word_progress(qapp):
    from presenters.lyrics_presenter import LyricsPresenter
    from tests.test_presenters import FakeLyrics, Rig

    rig = Rig()
    lyrics = FakeLyrics()
    rig.keep(LyricsPresenter(rig.window, rig.playback, lyrics))
    rig.playback.track_loading.emit({"videoId": "v1", "title": "T"})
    assert lyrics.calls[-1][0]["videoId"] == "v1"
    lyrics.calls[-1][1](word_lyrics())
    panel = rig.window.side_panel
    rig.playback.time_ms.emit(500)
    assert panel._lyrics.currentRow() == -1
    rig.playback.time_ms.emit(1500)
    assert panel._lyrics.currentRow() == 0 and lit_words(panel, 0) == ["Hel", "lo "]
    rig.playback.time_ms.emit(2500)
    assert lit_words(panel, 0) == ["Hel", "lo ", "world"]
    rig.playback.time_ms.emit(5200)
    assert panel._lyrics.currentRow() == 1 and lit_words(panel, 1) == ["Bye "]
    rig.window.close()
