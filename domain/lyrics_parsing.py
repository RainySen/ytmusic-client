from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from domain.models import LyricLine, Lyrics, LyricWord, parse_time_ms

_LRC_STAMP = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")
_LRC_WORD_TAG = re.compile(r"<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>")
_SKIPPED_ROLES = ("x-translation", "x-roman")
_INSTRUMENTAL = "♪"


def _fraction_ms(digits: str | None) -> int:
    if not digits:
        return 0
    return int(digits.ljust(3, "0")[:3])


# letra lrc lineas tiempos
def parse_lrc(text: str | None, source: str = "") -> Lyrics | None:
    if not text:
        return None
    timed: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stamps = list(_LRC_STAMP.finditer(raw))
        if not stamps:
            continue
        body = _LRC_WORD_TAG.sub("", raw[stamps[-1].end():]).strip()
        for stamp in stamps:
            minutes, seconds, fraction = stamp.groups()
            timed.append(((int(minutes) * 60 + int(seconds)) * 1000 + _fraction_ms(fraction), body))
    timed.sort(key=lambda item: item[0])
    while timed and not timed[-1][1]:
        timed.pop()
    while timed and not timed[0][1]:
        timed.pop(0)
    if not timed:
        return None
    lines = []
    for position, (start, body) in enumerate(timed):
        end = timed[position + 1][0] if position + 1 < len(timed) else start
        lines.append(LyricLine(body or _INSTRUMENTAL, start, end))
    return Lyrics(tuple(lines), synced=True, source=source)


def plain_lyrics(text: str | None, source: str = "") -> Lyrics | None:
    if not text or not text.strip():
        return None
    return Lyrics(tuple(LyricLine(line) for line in text.strip().splitlines()), synced=False, source=source)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _role(node: ET.Element) -> str:
    return next((value for key, value in node.attrib.items() if key.rsplit("}", 1)[-1] == "role"), "")


def _clock(value: str | None) -> int | None:
    if not value:
        return None
    value = value.strip()
    if value.endswith("s") and ":" not in value:
        value = value[:-1]
    return parse_time_ms(value) if value else None


def _collect_words(node: ET.Element, words: list[list], line_start: int) -> None:
    for child in node:
        if _local(child.tag) != "span":
            continue
        if _role(child) in _SKIPPED_ROLES:
            pass
        elif any(_local(grand.tag) == "span" for grand in child):
            _collect_words(child, words, line_start)
        elif child.text:
            start = _clock(child.get("begin"))
            end = _clock(child.get("end"))
            if start is None:
                start = (words[-1][2] if words[-1][2] is not None else words[-1][1]) if words else line_start
            words.append([child.text, start, end])
        if child.tail and child.tail.isspace() and words and not words[-1][0].endswith(" "):
            words[-1][0] += " "


# letra ttml silabas palabras
def parse_ttml(document: str | None, source: str = "") -> Lyrics | None:
    if not document or "<!DOCTYPE" in document or "<!ENTITY" in document:
        return None
    try:
        root = ET.fromstring(document)
    except ET.ParseError:
        return None
    lines: list[LyricLine] = []
    for paragraph in root.iter():
        if _local(paragraph.tag) != "p":
            continue
        begin, end = _clock(paragraph.get("begin")), _clock(paragraph.get("end"))
        words: list[list] = []
        _collect_words(paragraph, words, begin or 0)
        if words:
            for position, word in enumerate(words):
                if word[2] is None:
                    following = words[position + 1][1] if position + 1 < len(words) else end
                    word[2] = following if following is not None else word[1]
            words[-1][0] = words[-1][0].rstrip()
            text = "".join(w[0] for w in words).strip()
            start = begin if begin is not None else words[0][1]
            stop = end if end is not None else words[-1][2]
            timed = tuple(LyricWord(w[0], w[1], w[2]) for w in words)
        else:
            text = " ".join("".join(paragraph.itertext()).split())
            start, stop, timed = begin, end, ()
        if not text or start is None:
            continue
        lines.append(LyricLine(text, start, stop if stop is not None else start, timed))
    if not lines:
        return None
    lines.sort(key=lambda line: line.time_ms)
    return Lyrics(tuple(lines), synced=True, source=source)
