from __future__ import annotations

from typing import Any


# busqueda agrupar
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


def flatten_search_results(grouped: dict[str, Any]) -> list[dict]:
    top = [grouped["top_result"]] if grouped.get("top_result") else []
    return top + grouped.get("songs", []) + grouped.get("more", [])
