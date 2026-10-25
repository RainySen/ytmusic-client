from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

from core.i18n import t

Track = dict[str, Any]

LOCAL_SOURCES = ("local", "imported", "user_created")


# built on use: the language is only known after startup
def unknown_artist() -> str:
    return t("domain.unknown_artist")


def artist_list(item: dict) -> list[str]:
    artists = item.get("artists")
    if not isinstance(artists, list):
        return []
    return [a["name"] for a in artists if isinstance(a, dict) and isinstance(a.get("name"), str) and a["name"]]


def artist_names(item: dict, limit: int | None = None, sep: str = " • ") -> str:
    names = artist_list(item)
    if limit is not None:
        names = names[:limit]
    return sep.join(names)


def primary_artist(item: dict, default: str | None = None) -> str:
    names = artist_list(item)
    if names:
        return names[0]
    return default if default is not None else unknown_artist()


MAX_THUMBNAIL_PX = 1200
_SIZED_IMAGE = re.compile(r"^(https://[\w-]+\.(?:googleusercontent|ggpht)\.com/.+)=w(\d+)-h(\d+)((?:-[\w-]+)*)$")


def _at_size(url: str, pixels: int) -> str:
    match = _SIZED_IMAGE.match(url)
    if pixels <= 0 or not match or match.group(2) != match.group(3):
        return url
    size = min(pixels, MAX_THUMBNAIL_PX)
    return f"{match.group(1)}=w{size}-h{size}{match.group(4)}"


def _width(thumb: dict) -> int:
    width = thumb.get("width")
    return width if isinstance(width, (int, float)) and not isinstance(width, bool) else 0


def thumbnail_url(item: dict, min_width: int = 0) -> str:
    raw = item.get("thumbnails")
    thumbs = [thumb for thumb in (raw if isinstance(raw, list) else []) if isinstance(thumb, dict) and isinstance(thumb.get("url"), str) and thumb["url"]]
    if thumbs:
        thumbs.sort(key=_width)
        for thumb in thumbs:
            if _width(thumb) >= min_width:
                return _at_size(thumb["url"], min_width)
        return _at_size(thumbs[-1]["url"], min_width)
    video_id = item.get("videoId", "")
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return ""


def format_seconds(total: int) -> str:
    total = max(0, int(total))
    return f"{total // 60}:{total % 60:02d}"


def normalize_track(raw: dict | None) -> Track | None:
    if not raw or not raw.get("videoId"):
        return None
    track: Track = {
        "videoId": raw["videoId"],
        "title": raw.get("title") or t("domain.unknown_title"),
        "artists": raw.get("artists") or [{"name": unknown_artist()}],
        "thumbnails": raw.get("thumbnails") or [],
    }
    duration = raw.get("duration")
    if duration:
        track["duration"] = duration
    album = raw.get("album")
    album_name = album.get("name") if isinstance(album, dict) else album
    if album_name:
        track["album"] = album_name
    album_id = album.get("id") if isinstance(album, dict) else None
    if album_id:
        track["albumId"] = album_id
    like = raw.get("likeStatus")
    if like:
        track["likeStatus"] = like
    views = _play_count(raw.get("views"))
    if views:
        track["views"] = views
    return track


def _plays_text(text: str) -> str:
    return t("domain.plays", count=text)


# known suffixes from YouTube in every supported UI/content language
_PLAY_SUFFIXES = (" plays", " views", " reproducciones", " reproduções")


def _has_plays_suffix(text: str) -> bool:
    return text.endswith(_PLAY_SUFFIXES)


def _play_count(raw: Any) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    text = raw.strip()
    for english in (" plays", " views"):
        if text.endswith(english):
            return _plays_text(text[: -len(english)])
    return text


def normalize_tracks(raw_tracks: Iterable[dict]) -> list[Track]:
    result = []
    for raw in raw_tracks:
        track = normalize_track(raw)
        if track:
            result.append(track)
    return result


def playlist_id_of(raw: dict) -> str:
    pid = raw.get("playlistId", "")
    if not pid:
        browse_id = raw.get("browseId", "")
        pid = browse_id[2:] if browse_id.startswith("VL") else browse_id
    return pid


def normalize_playlist_item(raw: dict) -> dict:
    return {
        "type": "playlist",
        "playlistId": playlist_id_of(raw),
        "title": raw.get("title", ""),
        "thumbnails": raw.get("thumbnails", []),
    }


def release_label(kind: Any, default: str | None = None) -> str:
    key = str(kind or "").strip().lower()
    key = "".join(c for c in unicodedata.normalize("NFKD", key) if not unicodedata.combining(c))
    labels = {
        "single": t("domain.release.single"), "sencillo": t("domain.release.single"),
        "ep": t("domain.release.ep"), "album": t("domain.release.album"),
    }
    fallback = default if default is not None else t("domain.release.album")
    return labels.get(key, fallback)


def normalize_release(raw: dict, default_kind: str | None = None) -> dict | None:
    if not raw.get("browseId"):
        return None
    label = release_label(raw.get("type"), default_kind)
    year = str(raw.get("year") or "")
    return {
        "type": "album",
        "browseId": raw["browseId"],
        "title": raw.get("title", ""),
        "artists": raw.get("artists") or [],
        "thumbnails": raw.get("thumbnails") or [],
        "subtitle": f"{label} • {year}" if year else label,
    }


def _views_label(raw: Any) -> str:
    if not raw or not isinstance(raw, str):
        return ""
    text = raw.strip()
    return t("domain.views", count=text) if re.fullmatch(r"[\d.,]+\s?[KMBkmb]?", text) else text


def normalize_video(raw: dict) -> dict | None:
    if not raw.get("videoId"):
        return None
    views = _views_label(raw.get("views"))
    by = artist_names(raw, limit=1)
    return {
        "type": "video",
        "videoId": raw["videoId"],
        "title": raw.get("title", ""),
        "artists": raw.get("artists") or [],
        "thumbnails": raw.get("thumbnails") or [],
        "subtitle": " • ".join(p for p in (by, views) if p),
    }


def normalize_artist_card(raw: dict) -> dict | None:
    if not raw.get("browseId"):
        return None
    return {
        "type": "artist",
        "browseId": raw["browseId"],
        "title": raw.get("title") or raw.get("artist", ""),
        "subscribers": raw.get("subscribers", ""),
        "thumbnails": raw.get("thumbnails") or [],
    }


def parse_home_section(section: dict) -> list[dict]:
    items = []
    for item in section.get("contents") or []:
        if not item:
            continue
        thumbs = item.get("thumbnails", [])
        if "videoId" in item:
            song = {
                "type": "song",
                "videoId": item.get("videoId"),
                "title": item.get("title", t("domain.untitled")),
                "artists": item.get("artists", []),
                "thumbnails": thumbs,
            }
            if item.get("likeStatus"):
                song["likeStatus"] = item["likeStatus"]
            views = _home_plays(item.get("views"))
            if views:
                song["views"] = views
            items.append(song)
        elif "playlistId" in item:
            items.append({
                "type": "playlist",
                "playlistId": item.get("playlistId"),
                "title": item.get("title", t("domain.playlist")),
                "thumbnails": thumbs,
            })
        elif "browseId" in item:
            kind = "artist" if str(item.get("browseId")).startswith("UC") else "album"
            entry = {"type": kind, "browseId": item.get("browseId"), "title": item.get("title", t("domain.release.album")),
                     "thumbnails": thumbs}
            if kind == "album":
                by = artist_names(item, limit=2)
                label = release_label(item.get("type"))
                entry["artists"] = item.get("artists") or []
                entry["subtitle"] = f"{label} • {by}" if by else label
            items.append(entry)
    return items


def _home_plays(raw: Any) -> str:
    text = _play_count(raw)
    return text if not text or _has_plays_suffix(text) else _plays_text(text)


@dataclass(frozen=True)
class LyricWord:
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class LyricLine:
    text: str
    time_ms: int = 0
    end_ms: int = 0
    words: tuple[LyricWord, ...] = ()
    romanization: str = ""


@dataclass(frozen=True)
class Lyrics:
    lines: tuple[LyricLine, ...]
    synced: bool
    source: str = ""

    @property
    def texts(self) -> list[str]:
        return [line.text for line in self.lines]

    @property
    def word_synced(self) -> bool:
        return self.synced and any(line.words for line in self.lines)


@dataclass(frozen=True)
class LyricsQuery:
    video_id: str
    title: str
    artist: str
    album: str = ""
    duration: int = 0


_TITLE_NOISE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]|\s+-\s+(topic|official.*|lyrics?|audio|video)$", re.IGNORECASE)


def clean_title(title: str) -> str:
    cleaned = _TITLE_NOISE.sub("", title or "").strip()
    return cleaned or (title or "").strip()


def lyrics_query(song: dict) -> LyricsQuery:
    duration = song.get("duration")
    seconds = round(parse_time_ms(duration) / 1000) if isinstance(duration, str) else int(song.get("duration_seconds") or 0)
    album = song.get("album")
    return LyricsQuery(
        video_id=song.get("videoId", ""),
        title=song.get("title", ""),
        artist=primary_artist(song, default=""),
        album=(album.get("name") if isinstance(album, dict) else album) or "",
        duration=seconds,
    )


def parse_time_ms(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        parts = str(value).split(":")
        if len(parts) == 2:
            seconds = int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        else:
            seconds = float(value)
        return int(seconds * 1000) if math.isfinite(seconds) else 0
    except (ValueError, TypeError, OverflowError):
        return 0


def parse_lyrics(data: dict | None) -> Lyrics | None:
    if not data:
        return None
    raw_lines = data.get("lines")
    if raw_lines:
        lines = tuple(LyricLine(l.get("text", ""), parse_time_ms(l.get("time"))) for l in raw_lines)
        return Lyrics(lines, synced=any(l.time_ms > 0 for l in lines))
    text = data.get("lyrics")
    if isinstance(text, list):
        # ytmusicapi timed lines: objects with text, start_time, end_time (ms)
        lines = tuple(LyricLine(getattr(l, "text", "") or "", int(getattr(l, "start_time", 0) or 0),
                                int(getattr(l, "end_time", 0) or 0)) for l in text)
        return Lyrics(lines, synced=any(l.time_ms > 0 for l in lines)) if lines else None
    if text:
        return Lyrics(tuple(LyricLine(t) for t in text.split("\n")), synced=False)
    return None
