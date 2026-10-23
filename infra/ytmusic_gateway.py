from __future__ import annotations

import logging
import os
import threading
from typing import Any

from core.config import CONTENT_LANGUAGE
from infra import secure_store
from infra.auth_headers import cookie_header, parse_cookie_string
from infra.library_search import lenient_library_search
from infra.secure_store import read_secret_json

log = logging.getLogger(__name__)


class GatewayError(Exception):
    pass


class AuthRequired(GatewayError):
    pass


class SessionRejected(GatewayError):
    pass


# *PSIDTS expire unless rotated, as the web client does
ROTATE_COOKIES_URL = "https://accounts.youtube.com/RotateCookies"
_ROTATE_COOKIES_BODY = '[000,"-0000000000000000000"]'

_AUTH_FAILURE_MARKERS = ("http 401", "http 403", "unauthorized", "forbidden", "authenticat", "sign in", "login required")


def looks_like_auth_failure(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _AUTH_FAILURE_MARKERS)


class YTMusicGateway:
    def __init__(self, auth_file: str, language: str = CONTENT_LANGUAGE):
        self._auth_file = auth_file
        self._language = language
        self._client_lock = threading.Lock()
        self._ytm: Any = None
        self._ytm_browse: Any = None
        self._ytm_public: Any = None
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        if self._ytm is None:
            return self._has_credentials()
        return self._authenticated

    def _credentials(self) -> dict | None:
        data = read_secret_json(self._auth_file) if os.path.exists(self._auth_file) else None
        if isinstance(data, dict) and any(str(k).lower() == "cookie" and v for k, v in data.items()):
            return data
        return None

    def _has_credentials(self) -> bool:
        return self._credentials() is not None

    def _client(self) -> Any:
        ytm = self._ytm
        if ytm is not None:
            return ytm
        with self._client_lock:
            if self._ytm is None:
                self._ytm, self._authenticated = self._build()
            return self._ytm

    def set_language(self, language: str) -> None:
        with self._client_lock:
            if language != self._language:
                self._language = language
                self._ytm_browse = None

    def _browse_client(self) -> Any:
        ytm = self._ytm_browse
        if ytm is not None:
            return ytm
        self._client()
        with self._client_lock:
            if self._ytm_browse is None:
                self._ytm_browse, _ = self._build(language=self._language)
            return self._ytm_browse

    def _build(self, language: str | None = None) -> tuple[Any, bool]:
        from ytmusicapi import YTMusic

        options = {"language": language} if language else {}
        headers = self._credentials()
        if headers is not None:
            try:
                client = YTMusic(auth=headers, **options)
                self._upgrade_storage(headers)
                return client, True
            except OSError:
                raise
            except Exception:
                log.warning("Stored credentials are invalid; continuing unauthenticated", exc_info=True)
        return YTMusic(**options), False

    # one-time move of a plaintext session to the encrypted format
    def _upgrade_storage(self, headers: dict) -> None:
        if secure_store.available() and not secure_store.is_encrypted(self._auth_file):
            if secure_store.write_secret_json(self._auth_file, headers):
                log.info("Session file encrypted with DPAPI")

    def warm_up(self) -> None:
        for client in (self._client(), self._browse_client()):
            try:
                client.base_headers
            except Exception:
                log.debug("Header warm-up failed", exc_info=True)

    def authenticate(self, headers: dict[str, str]) -> None:
        from ytmusicapi import YTMusic

        try:
            candidate = YTMusic(auth=headers)
            candidate.get_library_playlists(limit=1)
        except Exception as exc:
            raise GatewayError(str(exc)) from exc
        if not secure_store.write_secret_json(self._auth_file, headers):
            raise GatewayError("No se pudieron guardar las credenciales.")
        try:
            browse = YTMusic(auth=headers, language=self._language)
        except Exception:
            browse = None
        with self._client_lock:
            self._ytm = candidate
            self._ytm_browse = browse
            self._authenticated = True

    def rotate_cookies(self) -> None:
        import requests

        headers = self._credentials()
        if headers is None:
            return
        key = next(k for k in headers if str(k).lower() == "cookie")
        response = requests.post(ROTATE_COOKIES_URL, data=_ROTATE_COOKIES_BODY, timeout=15, headers={
            "content-type": "application/json",
            "origin": "https://accounts.youtube.com",
            "user-agent": headers.get("user-agent", ""),
            "cookie": headers[key],
        })
        response.raise_for_status()
        cookies = parse_cookie_string(headers[key])
        rotated = {c.name: c.value for c in response.cookies if cookies.get(c.name) != c.value}
        if not rotated:
            return
        cookie = cookie_header({**cookies, **rotated})
        with self._client_lock:
            # logout race: never restore the file
            if not self._authenticated:
                return
            headers[key] = cookie
            secure_store.write_secret_json(self._auth_file, headers)
            for client in (self._ytm, self._ytm_browse):
                auth = getattr(client, "_auth_headers", None)
                if auth is not None and "cookie" in auth:
                    auth["cookie"] = cookie
        log.info("Session cookies rotated: %s", ", ".join(sorted(rotated)))

    def verify_session(self) -> None:
        client = self._require_auth()
        try:
            self.rotate_cookies()
        except Exception:  # noqa: BLE001
            log.warning("Cookie rotation failed", exc_info=True)
        try:
            client.get_library_playlists(limit=1)
        except Exception as exc:  # noqa: BLE001
            if looks_like_auth_failure(exc):
                raise SessionRejected(str(exc)) from exc
            raise

    def mark_signed_out(self) -> None:
        with self._client_lock:
            self._authenticated = False

    def logout(self) -> None:
        from ytmusicapi import YTMusic

        with self._client_lock:
            try:
                if os.path.exists(self._auth_file):
                    os.remove(self._auth_file)
            except OSError as exc:
                raise GatewayError(str(exc)) from exc
            self._ytm = YTMusic()
            self._ytm_browse = None
            self._authenticated = False

    def _require_auth(self) -> Any:
        client = self._client()
        if not self._authenticated:
            raise AuthRequired("Se requiere iniciar sesión.")
        return client

    def search(self, query: str, filter: str | None = None, limit: int = 25, scope: str | None = None) -> list[dict]:
        client = self._client()
        try:
            return client.search(query, filter=filter, limit=limit, scope=scope)
        except KeyError:
            if scope != "library" or filter:
                raise
            log.info("Library search hit a shelf without contents; parsing it leniently")
            return lenient_library_search(client, query)

    def search_suggestions(self, query: str) -> list[str]:
        return self._client().get_search_suggestions(query)

    def get_home(self, limit: int) -> list[dict]:
        return self._browse_client().get_home(limit=limit)

    def get_watch_playlist(self, video_id: str, limit: int) -> dict:
        return self._client().get_watch_playlist(videoId=video_id, limit=limit)

    def get_playlist(self, playlist_id: str, limit: int | None = None) -> dict:
        return self._client().get_playlist(playlist_id, limit=limit)

    def get_playlist_page(self, playlist_id: str, limit: int | None = None) -> dict:
        return self._browse_client().get_playlist(playlist_id, limit=limit)

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

    def get_user(self, channel_id: str) -> dict:
        return self._browse_client().get_user(channel_id)

    def get_user_videos(self, channel_id: str, params: str) -> list[dict]:
        return self._browse_client().get_user_videos(channel_id, params)

    def get_album(self, browse_id: str) -> dict:
        return self._browse_client().get_album(browse_id)

    def get_watch_playlist_for(self, playlist_id: str, limit: int) -> dict:
        return self._client().get_watch_playlist(playlistId=playlist_id, limit=limit)

    def get_lyrics(self, browse_id: str) -> dict:
        return self._client().get_lyrics(browseId=browse_id)

    # timed lyrics use the mobile client, which rejects account headers (http 400)
    def get_timed_lyrics(self, browse_id: str) -> dict:
        with self._client_lock:
            if self._ytm_public is None:
                from ytmusicapi import YTMusic

                self._ytm_public = YTMusic()
            public = self._ytm_public
        return public.get_lyrics(browseId=browse_id, timestamps=True)

    def get_lyrics_browse_id(self, video_id: str) -> str | None:
        return self._client().get_watch_playlist(videoId=video_id, limit=1).get("lyrics")

    def get_liked_songs(self, limit: int = 100) -> list[dict]:
        return self._require_auth().get_liked_songs(limit=limit).get("tracks") or []

    def get_like_status(self, video_id: str) -> str | None:
        tracks = self._require_auth().get_watch_playlist(videoId=video_id, limit=1).get("tracks") or []
        return tracks[0].get("likeStatus") if tracks else None

    def rate_song(self, video_id: str, status: str) -> None:
        self._require_auth().rate_song(video_id, status)

    def get_library_playlists(self, limit: int = 50) -> list[dict]:
        return self._require_auth().get_library_playlists(limit=limit)

    def get_library_songs(self, limit: int = 50) -> list[dict]:
        return self._require_auth().get_library_songs(limit=limit)

    def get_library_artists(self, limit: int = 50) -> list[dict]:
        return self._require_auth().get_library_artists(limit=limit)

    def get_account_info(self) -> dict:
        return self._require_auth().get_account_info()

    def get_history(self) -> list[dict]:
        return self._require_auth().get_history()

    def add_playlist_items(self, playlist_id: str, video_ids: list[str]) -> bool:
        response = self._require_auth().add_playlist_items(playlist_id, video_ids, duplicates=False)
        return "SUCCEEDED" in str((response or {}).get("status", ""))

    def create_playlist(self, title: str, description: str, video_ids: list[str]) -> str:
        return self._require_auth().create_playlist(
            title=title, description=description, privacy_status="PRIVATE", video_ids=video_ids
        )
