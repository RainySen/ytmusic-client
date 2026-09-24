from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtWidgets import QWidget

from config import NETWORK_CACHING_MS, RADIO_QUEUE_LIMIT, STREAM_EXPIRY_MARGIN_S, AppPaths
from domain.play_queue import PlayQueue
from domain.stream_cache import StreamCache
from infra.audio_backend import VlcAudioBackend
from infra.concurrency import TaskRunner
from infra.lyrics_providers import BetterLyricsProvider, LrcLibProvider, YouTubeMusicProvider
from infra.lyrics_settings import load_lyrics_settings
from infra.playlist_repository import LocalPlaylistRepository
from infra.recent_playlists import RecentPlaylists
from infra.stream_resolver import YtDlpStreamResolver
from infra.thumbnail_cache import ThumbnailCache
from infra.ytmusic_gateway import YTMusicGateway
from presenters.auth_presenter import AuthPresenter
from presenters.collection_presenter import CollectionPresenter
from presenters.explore_presenter import ExplorePresenter
from presenters.home_presenter import HomePresenter
from presenters.library_presenter import LibraryPresenter
from presenters.lyrics_presenter import LyricsPresenter
from presenters.player_presenter import PlayerPresenter
from presenters.playlist_presenter import PlaylistPresenter
from presenters.profile_presenter import ProfilePresenter
from presenters.search_presenter import SearchPresenter
from presenters.similar_presenter import SimilarPresenter
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.collection_actions import CollectionActions
from services.item_opener import ItemOpener
from services.library_service import LibraryService
from services.lyrics_service import LyricsService
from services.navigation import Navigator
from services.notifier import Notifier
from services.playback_service import PlaybackService
from services.session_service import SessionService
from services.stream_service import StreamService
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


@dataclass
class Services:
    paths: AppPaths
    notifier: Notifier
    gateway: YTMusicGateway
    resolver: YtDlpStreamResolver
    audio: VlcAudioBackend
    queue: PlayQueue
    streams: StreamService
    catalog: CatalogService
    library: LibraryService
    lyrics: LyricsService
    auth: AuthService
    playback: PlaybackService
    session: SessionService
    opener: ItemOpener
    navigator: Navigator
    collections: CollectionActions
    runners: list[TaskRunner]
    warmup_runner: TaskRunner

    # precalentar hilos
    def warm_up(self) -> None:
        notify = self.notifier
        self.warmup_runner.submit(self.gateway.warm_up)
        self.warmup_runner.submit(self.streams.warm_up)
        self.warmup_runner.submit(
            self.audio.warm_up, None,
            lambda exc: notify.error(f"No se pudo iniciar el audio (¿VLC instalado?): {exc}"),
        )

    # cierre guardar sesion
    def shutdown(self) -> bool:
        self.session.save()
        self.audio.stop()
        idle = True
        for runner in self.runners:
            idle = runner.shutdown() and idle
        return not idle


# letras proveedores orden
def build_lyrics_providers(paths: AppPaths, gateway: YTMusicGateway) -> list:
    settings = load_lyrics_settings(paths.lyrics_settings_file)
    available = {
        "betterlyrics": lambda: BetterLyricsProvider(settings.better_lyrics_api_key),
        "lrclib": LrcLibProvider,
        "youtube": lambda: YouTubeMusicProvider(gateway),
    }
    return [available[name]() for name in settings.providers if name in available]


# composicion servicios hilos
def build_services(paths: AppPaths) -> Services:
    paths.ensure_dirs()
    notifier = Notifier()

    browse_runner = TaskRunner("browse", 5)
    auth_runner = TaskRunner("auth", 4)
    play_runner = TaskRunner("stream-play", 2)
    prefetch_runner = TaskRunner("stream-prefetch", 2)
    warmup_runner = TaskRunner("warmup", 2)

    gateway = YTMusicGateway(paths.auth_file)
    resolver = YtDlpStreamResolver(paths.ytdlp_cache_dir)
    audio = VlcAudioBackend(NETWORK_CACHING_MS)
    queue = PlayQueue(RADIO_QUEUE_LIMIT)
    streams = StreamService(resolver, StreamCache(margin=STREAM_EXPIRY_MARGIN_S), play_runner, prefetch_runner)
    catalog = CatalogService(gateway, browse_runner, paths.home_cache_file)
    library = LibraryService(gateway, LocalPlaylistRepository(paths.playlists_file), catalog, browse_runner,
                             RecentPlaylists(paths.recent_playlists_file))
    playback = PlaybackService(queue, streams, audio, catalog, notifier)
    navigator = Navigator()

    return Services(
        paths=paths, notifier=notifier, gateway=gateway, resolver=resolver, audio=audio, queue=queue,
        streams=streams, catalog=catalog, library=library,
        lyrics=LyricsService(build_lyrics_providers(paths, gateway), browse_runner),
        auth=AuthService(gateway, auth_runner),
        playback=playback,
        session=SessionService(paths.session_file, queue, streams),
        opener=ItemOpener(catalog, playback, notifier, navigator),
        navigator=navigator,
        collections=CollectionActions(catalog, playback, notifier),
        runners=[browse_runner, auth_runner, play_runner, prefetch_runner, warmup_runner],
        warmup_runner=warmup_runner,
    )


@dataclass
class UserInterface:
    window: MainWindow
    thumbnails: ThumbnailCache
    player: PlayerPresenter
    home: HomePresenter
    explore: ExplorePresenter
    search: SearchPresenter
    library: LibraryPresenter
    lyrics: LyricsPresenter
    similar: SimilarPresenter
    profiles: ProfilePresenter
    playlists: PlaylistPresenter
    collections: CollectionPresenter
    account: AuthPresenter

    # arranque restaurar sesion
    def start(self, services: Services) -> None:
        services.session.restore()
        self.player.start()
        self.account.start()
        self.home.start()
        services.session.enable_autosave()


# composicion presenters ventana
def build_ui(services: Services, app_icon, login_window_factory: Callable[[], QWidget] | None = None) -> UserInterface:
    thumbnails = ThumbnailCache(services.paths.thumbnail_cache_dir)
    window = MainWindow(thumbnails, app_icon)
    services.notifier.message.connect(window.show_toast)

    make_login = login_window_factory or (lambda: LoginWindow(services.auth, app_icon))
    home = HomePresenter(window, services.catalog, services.playback, services.opener, services.notifier)
    playlists = PlaylistPresenter(window, services.catalog, services.library, services.playback,
                                  services.auth, services.notifier)
    return UserInterface(
        window=window,
        thumbnails=thumbnails,
        player=PlayerPresenter(window, services.playback),
        home=home,
        explore=ExplorePresenter(window, services.catalog, services.playback, services.opener, services.notifier),
        search=SearchPresenter(window, services.catalog, services.playback, services.opener, services.notifier),
        library=LibraryPresenter(window, services.library, services.playback, services.opener, services.notifier),
        lyrics=LyricsPresenter(window, services.playback, services.lyrics),
        similar=SimilarPresenter(window, services.catalog, services.playback, services.opener),
        profiles=ProfilePresenter(window, services.catalog, services.playback, services.opener,
                                  services.navigator, services.notifier),
        playlists=playlists,
        collections=CollectionPresenter(window, services.collections, playlists, services.notifier),
        account=AuthPresenter(window, services.auth, services.catalog, home, make_login, services.notifier),
    )
