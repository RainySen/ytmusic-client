from __future__ import annotations

from typing import Any


def group_search_results(raw: list[dict]) -> dict[str, Any]:
    top_result = None
    songs: list[dict] = []
    more: list[dict] = []
    category = None

    for item in raw:
        category = item.get("category") or category
        if category == "Top result" and top_result is None:
            top_result = item
        elif item.get("resultType") == "song":
            songs.append(item)
        else:
            more.append(item)

    if top_result and top_result.get("resultType") == "artist" and top_result.get("artists"):
        songs = [s if s.get("artists") else {**s, "artists": top_result["artists"]} for s in songs]

    return {"top_result": top_result, "songs": songs, "more": more}


LIBRARY_SECTIONS = (("artist", "Artistas"), ("album", "Álbumes"), ("song", "Canciones"), ("playlist", "Playlists"),
                    ("video", "Videos"))


# library search groups by type; library artist ids are MPLA + channel id
def group_library_results(raw: list[dict], local_songs: list[dict] | None = None) -> list[tuple[str, list[dict]]]:
    buckets: dict[str, list[dict]] = {kind: [] for kind, _title in LIBRARY_SECTIONS}
    seen: set[str] = set()
    for item in raw:
        kind = item.get("resultType")
        if kind not in buckets:
            continue
        if kind == "artist" and str(item.get("browseId", "")).startswith("MPLA"):
            item = {**item, "browseId": item["browseId"][4:]}
        if item.get("videoId"):
            seen.add(item["videoId"])
        buckets[kind].append(item)
    for song in local_songs or []:
        if song.get("videoId") not in seen:
            seen.add(song["videoId"])
            buckets["song"].append({**song, "resultType": "song"})
    return [(title, buckets[kind]) for kind, title in LIBRARY_SECTIONS if buckets[kind]]


def matches_query(item: dict, query: str) -> bool:
    words = query.lower().split()
    names = " ".join(a.get("name", "") for a in item.get("artists") or [] if isinstance(a, dict))
    album = item.get("album")
    album = album.get("name", "") if isinstance(album, dict) else album or ""
    text = f"{item.get('title', '')} {names} {album}".lower()
    return bool(words) and all(word in text for word in words)


def flatten_search_results(grouped: dict[str, Any]) -> list[dict]:
    top = [grouped["top_result"]] if grouped.get("top_result") else []
    return top + grouped.get("songs", []) + grouped.get("more", [])
