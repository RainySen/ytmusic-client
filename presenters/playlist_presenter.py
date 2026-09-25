from domain.models import normalize_track
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.library_service import LibraryService, extract_playlist_id
from services.notifier import Notifier
from services.playback_service import PlaybackService
from ui.main_window import MainWindow


# playlists guardar importar
class PlaylistPresenter:
    def __init__(self, window: MainWindow, catalog: CatalogService, library: LibraryService,
                 playback: PlaybackService, auth: AuthService, notifier: Notifier):
        self._window = window
        self._catalog = catalog
        self._library = library
        self._playback = playback
        self._auth = auth
        self._notifier = notifier

        window.import_url_submitted.connect(self.import_url)
        window.queue_save_requested.connect(self.save_queue)
        window.save_to_playlist_requested.connect(self.save_song)

    def import_url(self, url: str) -> None:
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            self._notifier.error("URL inválida. Formato esperado: https://music.youtube.com/playlist?list=PL…")
            return
        self._notifier.info("Importando playlist…")
        self._catalog.playlist(playlist_id, self._on_imported, self._on_import_error)

    def _on_imported(self, data) -> None:
        if not data:
            self._notifier.error("La playlist está vacía, es privada o no existe.")
            return
        title, tracks = data["title"], data["tracks"]
        self._playback.play_collection(tracks)
        target = self._window.ask_save_target(title, self._auth.is_authenticated)
        if target:
            self._library.save_imported(
                title, tracks, cloud=target == "cloud",
                on_done=lambda result: self._report(title, *result),
            )

    def _on_import_error(self, exc: Exception) -> None:
        self._notifier.error("No se pudo acceder a la playlist. Verifica la URL y tu conexión.")

    def save_queue(self, title: str) -> None:
        tracks = [s for s in self._playback.queue.snapshot() if s.get("videoId")]
        if not tracks:
            self._notifier.warning("La cola está vacía.")
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
            self._notifier.warning("Esto no se puede agregar a una playlist.")
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
        return f"«{tracks[0]['title']}»" if len(tracks) == 1 else f"{len(tracks)} canciones"

    def _report_added(self, playlist_title: str, tracks: list[dict], outcome: str) -> None:
        what = self._what(tracks)
        if outcome == "added":
            self._notifier.info(f"{what} agregada a «{playlist_title}»." if len(tracks) == 1
                                else f"{what} agregadas a «{playlist_title}».")
        elif outcome == "duplicate":
            self._notifier.info(f"{what} ya estaba en «{playlist_title}»." if len(tracks) == 1
                                else f"Esas canciones ya estaban en «{playlist_title}».")
        else:
            self._notifier.error(f"No se pudo agregar a «{playlist_title}». Puede que no sea tuya o que ya la tenga.")

    def _report_created(self, title: str, tracks: list[dict], wanted_cloud: bool, local_ok: bool,
                        cloud_ok: bool) -> None:
        if not (local_ok or cloud_ok):
            self._notifier.error(f"No se pudo crear «{title}».")
        elif wanted_cloud and not cloud_ok:
            self._notifier.warning(f"«{title}» se creó localmente, pero falló en YouTube Music.")
        else:
            what = self._what(tracks)
            self._notifier.info(f"{what} agregada a la nueva playlist «{title}»." if len(tracks) == 1
                                else f"{what} agregadas a la nueva playlist «{title}».")

    def _report(self, title: str, where: str, ok: bool) -> None:
        if ok:
            self._notifier.info(f"«{title}» guardada en {where}.")
        else:
            self._notifier.error(f"No se pudo guardar «{title}».")

    def _report_queue(self, title: str, wanted_cloud: bool, local_ok: bool, cloud_ok: bool) -> None:
        if not (local_ok or cloud_ok):
            self._notifier.error(f"No se pudo guardar «{title}».")
        elif wanted_cloud and not cloud_ok:
            self._notifier.warning(f"«{title}» se guardó localmente, pero falló en YouTube Music.")
        else:
            self._notifier.info(f"«{title}» guardada en {'local + YouTube Music' if cloud_ok else 'local'}.")
