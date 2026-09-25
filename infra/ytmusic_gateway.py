from __future__ import annotations

import logging
import os
import threading
from typing import Any

from core.config import CONTENT_LANGUAGE
from infra.json_store import read_json, write_json_atomic

log = logging.getLogger(__name__)


class GatewayError(Exception):
    pass


class AuthRequired(GatewayError):
    pass


class SessionRejected(GatewayError):
    pass


_AUTH_FAILURE_MARKERS = ("http 401", "http 403", "unauthorized", "forbidden", "authenticat", "sign in", "login required")


def looks_like_auth_failure(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _AUTH_FAILURE_MARKERS)


# ytmusicapi cliente
class YTMusicGateway:
    def __init__(self, auth_file: str):
        self._auth_file = auth_file
        self._client_lock = threading.Lock()
        self._ytm: Any = None
        self._ytm_browse: Any = None
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        if self._ytm is None:
            return self._has_credentials()
        return self._authenticated

    # credenciales archivo valido
    def _has_credentials(self) -> bool:
        data = read_json(self._auth_file) if os.path.exists(self._auth_file) else None
        return isinstance(data, dict) and any(str(k).lower() == "cookie" and v for k, v in data.items())

    def _client(self) -> Any:
        ytm = self._ytm
        if ytm is not None:
            return ytm
        with self._client_lock:
            if self._ytm is None:
                self._ytm, self._authenticated = self._build()
            return self._ytm

    # cliente idioma es
    def _browse_client(self) -> Any:
        ytm = self._ytm_browse
        if ytm is not None:
            return ytm
        self._client()
        with self._client_lock:
            if self._ytm_browse is None:
                self._ytm_browse, _ = self._build(language=CONTENT_LANGUAGE)
            return self._ytm_browse

    def _build(self, language: str | None = None) -> tuple[Any, bool]:
        from ytmusicapi import YTMusic

        options = {"language": language} if language else {}
        if self._has_credentials():
            try:
                return YTMusic(self._auth_file, **options), True
            except OSError:
                raise
            except Exception:
                log.warning("Stored credentials are invalid; continuing unauthenticated", exc_info=True)
        return YTMusic(**options), False

    def warm_up(self) -> None:
        for client in (self._client(), self._browse_client()):
            try:
                client.base_headers
            except Exception:
                log.debug("Header warm-up failed", exc_info=True)

    # login validar guardar credenciales
    def authenticate(self, headers: dict[str, str]) -> None:
        from ytmusicapi import YTMusic

        try:
            candidate = YTMusic(auth=headers)
            candidate.get_library_playlists(limit=1)
        except Exception as exc:
            raise GatewayError(str(exc)) from exc
        if not write_json_atomic(self._auth_file, headers, indent=4):
            raise GatewayError("No se pudieron guardar las credenciales.")
        try:
            browse = YTMusic(auth=headers, language=CONTENT_LANGUAGE)
        except Exception:
            browse = None
        with self._client_lock:
            self._ytm = candidate
            self._ytm_browse = browse
            self._authenticated = True

    # login cerrar sesion
    # login verificar sesion caducada
    def verify_session(self) -> None:
        client = self._require_auth()
        try:
            client.get_library_playlists(limit=1)
        except Exception as exc:  # noqa: BLE001
            if looks_like_auth_failure(exc):
                with self._client_lock:
                    self._authenticated = False
                raise SessionRejected(str(exc)) from exc
            raise

    def logout(self) -> None:
        from ytmusicapi import YTMusic

        try:
            if os.path.exists(self._auth_file):
                os.remove(self._auth_file)
        except OSError as exc:
            raise GatewayError(str(exc)) from exc
        with self._client_lock:
            self._ytm = YTMusic()
            self._ytm_browse = None
            self._authenticated = False

    def _require_auth(self) -> Any:
        client = self._client()
        if not self._authenticated:
            raise AuthRequired("Se requiere iniciar sesión.")
        return client

    def search(self, query: str, filter: str | None = None, limit: int = 25) -> list[dict]:
        return self._client().search(query, filter=filter, limit=limit)

    def get_home(self, limit: int) -> list[dict]:
        return self._browse_client().get_home(limit=limit)

    def get_watch_playlist(self, video_id: str, limit: int) -> dict:
        return self._client().get_watch_playlist(videoId=video_id, limit=limit)

    def get_playlist(self, playlist_id: str, limit: int | None = None) -> dict:
        return self._client().get_playlist(playlist_id, limit=limit)

    def get_playlist_page(self, playlist_id: str) -> dict:
        return self._browse_client().get_playlist(playlist_id, limit=None)

    def get_related(self, video_id: str) -> list[dict]:
        client = self._browse_client()
        related_id = client.get_watch_playlist(videoId=video_id, limit=1).get("related")
        return client.get_song_related(related_id) if related_id else []

    def get_charts(self) -> dict:
        return self._browse_client().get_charts()

    def get_explore(self) -> dict:
        return self._browse_client().get_explore()

    def get_mood_playlists(self, params: str) -> list[dict]:
        return self._browse_client().get_mood_playlists(params)

    def get_artist(self, browse_id: str) -> dict:
        return self._browse_client().get_artist(browse_id)

    def get_album(self, browse_id: str) -> dict:
        return self._browse_client().get_album(browse_id)

    def get_watch_playlist_for(self, playlist_id: str, limit: int) -> dict:
        return self._client().get_watch_playlist(playlistId=playlist_id, limit=limit)

    def get_lyrics(self, browse_id: str) -> dict:
        return self._client().get_lyrics(browseId=browse_id)

    def get_lyrics_browse_id(self, video_id: str) -> str | None:
        return self._client().get_watch_playlist(videoId=video_id, limit=1).get("lyrics")

    def get_library_playlists(self, limit: int = 50) -> list[dict]:
        return self._require_auth().get_library_playlists(limit=limit)

    def get_library_songs(self, limit: int = 50) -> list[dict]:
        return self._require_auth().get_library_songs(limit=limit)

    def get_library_artists(self, limit: int = 50) -> list[dict]:
        return self._require_auth().get_library_artists(limit=limit)

    def add_playlist_items(self, playlist_id: str, video_ids: list[str]) -> bool:
        response = self._require_auth().add_playlist_items(playlist_id, video_ids, duplicates=False)
        return "SUCCEEDED" in str((response or {}).get("status", ""))

    def create_playlist(self, title: str, description: str, video_ids: list[str]) -> str:
        return self._require_auth().create_playlist(
            title=title, description=description, privacy_status="PRIVATE", video_ids=video_ids
        )
