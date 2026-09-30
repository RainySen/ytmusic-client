from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime

from infra.json_store import read_json, write_json_atomic

log = logging.getLogger(__name__)


class LocalPlaylistRepository:
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.RLock()
        self._playlists: list[dict] | None = None

    def _load(self) -> list[dict]:
        if self._playlists is None:
            data = read_json(self._path, [])
            self._playlists = [self._clean(p) for p in data if isinstance(p, dict)] if isinstance(data, list) else []
        return self._playlists

    @staticmethod
    def _clean(playlist: dict) -> dict:
        tracks = playlist.get("tracks")
        playlist["tracks"] = [t for t in tracks if isinstance(t, dict)] if isinstance(tracks, list) else []
        if not playlist.get("updated_at"):
            playlist["updated_at"] = playlist.get("created_at", "")
        return playlist

    def all(self) -> list[dict]:
        with self._lock:
            return list(self._load())

    def get(self, playlist_id: str) -> dict | None:
        with self._lock:
            return next((p for p in self._load() if p.get("playlistId") == playlist_id), None)

    def add(self, title: str, tracks: list[dict], source: str = "imported") -> str | None:
        playlist_id = f"local_{uuid.uuid4().hex}"
        now = datetime.now().isoformat()
        playlist = {
            "playlistId": playlist_id,
            "title": title,
            "source": source,
            "tracks": tracks,
            "created_at": now,
            "updated_at": now,
            "track_count": len(tracks),
        }
        with self._lock:
            playlists = self._load()
            playlists.append(playlist)
            if write_json_atomic(self._path, playlists):
                return playlist_id
            playlists.pop()
            return None

    def add_tracks(self, playlist_id: str, tracks: list[dict]) -> int | None:
        with self._lock:
            playlist = self.get(playlist_id)
            if playlist is None:
                return None
            present = {t.get("videoId") for t in playlist.get("tracks", [])}
            fresh = []
            for track in tracks:
                if track.get("videoId") and track["videoId"] not in present:
                    present.add(track["videoId"])
                    fresh.append(track)
            if not fresh:
                return 0
            before = playlist.get("tracks", [])
            before_updated = playlist.get("updated_at", "")
            playlist["tracks"] = before + fresh
            playlist["track_count"] = len(playlist["tracks"])
            playlist["updated_at"] = datetime.now().isoformat()
            if write_json_atomic(self._path, self._load()):
                return len(fresh)
            playlist["tracks"] = before
            playlist["track_count"] = len(before)
            playlist["updated_at"] = before_updated
            return None

    def delete(self, playlist_id: str) -> bool:
        with self._lock:
            playlists = self._load()
            remaining = [p for p in playlists if p.get("playlistId") != playlist_id]
            if len(remaining) == len(playlists):
                return False
            self._playlists = remaining
            return write_json_atomic(self._path, remaining)

    def rename(self, playlist_id: str, new_title: str) -> bool:
        with self._lock:
            playlist = self.get(playlist_id)
            if playlist is None:
                return False
            playlist["title"] = new_title
            playlist["updated_at"] = datetime.now().isoformat()
            return write_json_atomic(self._path, self._load())
