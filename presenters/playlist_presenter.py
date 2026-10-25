from core.i18n import t
from domain.models import normalize_track
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.library_service import LibraryService
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow


class PlaylistPresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, library: LibraryService,
                 playback: PlaybackService, auth: AuthService, notifier: Notifier):
        self._window = window
        self._catalog = catalog
        self._library = library
        self._playback = playback
        self._auth = auth
        self._notifier = notifier

        window.queue_save_requested.connect(self.save_queue)
        window.save_to_playlist_requested.connect(self.save_song)

    def save_queue(self, title: str) -> None:
        tracks = [s for s in self._playback.queue.snapshot() if s.get("videoId")]
        if not tracks:
            self._notifier.warning(t("playlist.queue_empty"))
            return
        cloud = self._auth.is_authenticated
        self._library.save_playlist(
            title, tracks, cloud=cloud,
            on_done=lambda result: self._report_queue(title, cloud, *result),
        )

    def save_song(self, song: dict) -> None:
        self.save_tracks([song])

    def save_tracks(self, songs: list[dict]) -> None:
        tracks = [t for t in (normalize_track(s) for s in songs) if t]
        if not tracks:
            self._notifier.warning(t("playlist.add.invalid"))
            return
        self._library.save_targets(lambda targets: self._on_targets(tracks, targets))

    def _on_targets(self, tracks: list[dict], targets: dict) -> None:
        choice = self._window.choose_playlist(targets)
        if not choice:
            return
        kind, value = choice
        if kind == "new":
            cloud = self._auth.is_authenticated
            self._library.save_playlist(
                value, tracks, cloud=cloud,
                on_done=lambda result: self._report_created(value, tracks, cloud, *result),
            )
        else:
            self._library.add_to_playlist(
                value, tracks, lambda outcome: self._report_added(value["title"], tracks, outcome))

    @staticmethod
    def _what(tracks: list[dict]) -> str:
        return f"«{tracks[0]['title']}»" if len(tracks) == 1 else t("playlist.what.many", count=len(tracks))

    def _report_added(self, playlist_title: str, tracks: list[dict], outcome: str) -> None:
        what = self._what(tracks)
        if outcome == "added":
            self._notifier.info(t("playlist.added.one", what=what, playlist_title=playlist_title) if len(tracks) == 1
                                else t("playlist.added.many", what=what, playlist_title=playlist_title))
        elif outcome == "duplicate":
            self._notifier.info(t("playlist.duplicate.one", what=what, playlist_title=playlist_title) if len(tracks) == 1
                                else t("playlist.duplicate.many", playlist_title=playlist_title))
        else:
            self._notifier.error(t("playlist.add.failed", playlist_title=playlist_title))

    def _report_created(self, title: str, tracks: list[dict], wanted_cloud: bool, local_ok: bool,
                        cloud_ok: bool) -> None:
        if not (local_ok or cloud_ok):
            self._notifier.error(t("playlist.create.failed", title=title))
        elif wanted_cloud and not cloud_ok:
            self._notifier.warning(t("playlist.create.local_only", title=title))
        else:
            what = self._what(tracks)
            self._notifier.info(t("playlist.created.one", what=what, title=title) if len(tracks) == 1
                                else t("playlist.created.many", what=what, title=title))

    def _report(self, title: str, where: str, ok: bool) -> None:
        if ok:
            self._notifier.info(t("playlist.saved", title=title, where=where))
        else:
            self._notifier.error(t("playlist.save.failed", title=title))

    def _report_queue(self, title: str, wanted_cloud: bool, local_ok: bool, cloud_ok: bool) -> None:
        if not (local_ok or cloud_ok):
            self._notifier.error(t("playlist.save.failed", title=title))
        elif wanted_cloud and not cloud_ok:
            self._notifier.warning(t("playlist.queue.local_only", title=title))
        else:
            self._notifier.info(t("playlist.saved", title=title,
                                  where="local + YouTube Music" if cloud_ok else "local"))
