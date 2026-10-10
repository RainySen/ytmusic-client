from __future__ import annotations

from typing import Any

LIBRARY_TAB = 1
MRLIR = "musicResponsiveListItemRenderer"


# ytmusicapi crashes on lazy "show all" shelves; skip them
def lenient_library_search(client: Any, query: str) -> list[dict]:
    from ytmusicapi.parsers.search import get_search_params, parse_search_results

    body = {"query": query, "params": get_search_params(None, "library", False)}
    results: list[dict] = []
    for shelf in _shelves(client._send_request("search", body), LIBRARY_TAB):
        contents = shelf.get("contents") or []
        if contents and MRLIR in contents[0]:
            results.extend(parse_search_results(contents, None, _shelf_title(shelf)))
    return results


def _shelves(response: dict, tab_index: int) -> list[dict]:
    root = response.get("contents") or {}
    tabs = (root.get("tabbedSearchResultsRenderer") or {}).get("tabs")
    if tabs:
        root = tabs[min(tab_index, len(tabs) - 1)]["tabRenderer"].get("content") or {}
    sections = (root.get("sectionListRenderer") or {}).get("contents") or []
    return [s["musicShelfRenderer"] for s in sections if "musicShelfRenderer" in s]


def _shelf_title(shelf: dict) -> str | None:
    runs = (shelf.get("title") or {}).get("runs") or []
    return runs[0].get("text") if runs else None
