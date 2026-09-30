from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from core.config import NETWORK_CACHING_MS, STREAM_EXPIRY_MARGIN_S, AppPaths
from domain.play_queue import PlayQueue
from domain.settings import Settings
from domain.stream_cache import StreamCache
from infra.audio_backend import VlcAudioBackend
from infra.autostart import Autostart
from infra.cache_store import CacheStore
from infra.concurrency import TaskRunner
from infra.lyrics_providers import BetterLyricsProvider, LrcLibProvider, YouTubeMusicProvider
from infra.lyrics_settings import load_lyrics_settings
from infra.media_keys import MediaKeys
from infra.listen_again_pins import ListenAgainPins
from infra.pinned_playlists import PinnedPlaylists
from infra.playlist_repository import LocalPlaylistRepository
from infra.recent_playlists import RecentPlaylists
from infra.romanization import UnisonRomanizer
from infra.stream_resolver import YtDlpStreamResolver
from infra.settings_repository import SettingsRepository
from infra.thumbnail_cache import ThumbnailCache
from infra.ytmusic_gateway import YTMusicGateway
from presenters.auth_presenter import AuthPresenter
from presenters.collection_presenter import CollectionPresenter
from presenters.explore_presenter import ExplorePresenter
from presenters.home_presenter import HomePresenter
from presenters.library_presenter import LibraryPresenter
from presenters.lyrics_presenter import LyricsPresenter
from presenters.memory_presenter import MemoryPresenter
from presenters.mini_player_presenter import MiniPlayerPresenter
from presenters.player_presenter import PlayerPresenter
from presenters.playlist_presenter import PlaylistPresenter
from presenters.playlist_rail_presenter import PlaylistRailPresenter
from presenters.profile_presenter import ProfilePresenter
from presenters.search_presenter import SearchPresenter
from presenters.settings_presenter import SettingsPresenter
from presenters.system_presenter import SystemPresenter
from presenters.similar_presenter import SimilarPresenter
from presenters.song_menu_presenter import SongMenuPresenter
from services.auth_service import AuthService
from services.catalog_service import CatalogService
from services.collection_actions import CollectionActions
from services.item_opener import ItemOpener
from services.library_service import LibraryService
from services.lyrics_service import LyricsService
from services.navigation import Navigator
from services.notifier import Notifier
from services.playback_service import PlaybackService
from services.search_history_service import SearchHistoryService
from services.session_service import SessionService
from services.settings_service import SettingsService
from services.stream_service import StreamService
from ui import imaging
from ui.login_window import LoginWindow
from ui.components.track_actions import song_hub
from ui.main_window import MainWindow

LIBRARY_PREFETCH_MS = 4000

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
    settings: SettingsService
    history: SearchHistoryService
    runners: list[TaskRunner]
    warmup_runner: TaskRunner

    def warm_up(self) -> None:
        notify = self.notifier
        self.warmup_runner.submit(self.gateway.warm_up)
        self.warmup_runner.submit(self.streams.warm_up)
        self.warmup_runner.submit(
            self.audio.warm_up, None,
            lambda exc: notify.error(f"No se pudo iniciar el audio (¿VLC instalado?): {exc}"),
        )

    def shutdown(self) -> bool:
        self.session.save(wait=True)
        self.audio.stop()
        idle = True
        for runner in self.runners:
            idle = runner.shutdown() and idle
        return not idle


def build_lyrics_providers(settings: Settings, gateway: YTMusicGateway, environ: dict | None = None) -> list:
    environ = os.environ if environ is None else environ
    key = environ.get("BETTER_LYRICS_API_KEY") or settings.better_lyrics_key
    available = {
        "betterlyrics": lambda: BetterLyricsProvider(key),
        "lrclib": LrcLibProvider,
        "youtube": lambda: YouTubeMusicProvider(gateway),
    }
    return [available[name]() for name in settings.lyrics_providers if name in available]


# separate factory so tests can mock it
def build_romanizer() -> UnisonRomanizer:
    return UnisonRomanizer()


def migrate_lyrics_file(paths: AppPaths, settings: SettingsService) -> None:
    legacy = paths.lyrics_settings_file
    if not os.path.exists(legacy):
        return
    old = load_lyrics_settings(legacy, {})
    clean = Settings.from_dict({"lyrics_providers": list(old.providers), "better_lyrics_key": old.better_lyrics_api_key})
    settings.update(lyrics_providers=clean.lyrics_providers, better_lyrics_key=clean.better_lyrics_key)
    try:
        os.replace(legacy, legacy + ".migrated")
    except OSError:
        pass


def build_services(paths: AppPaths) -> Services:
    paths.ensure_dirs()
    notifier = Notifier()

    browse_runner = TaskRunner("browse", 5)
    auth_runner = TaskRunner("auth", 4)
    play_runner = TaskRunner("stream-play", 2)
    prefetch_runner = TaskRunner("stream-prefetch", 2)
    warmup_runner = TaskRunner("warmup", 2)

    settings_is_new = not os.path.exists(paths.settings_file)
    settings = SettingsService(SettingsRepository(paths.settings_file))
    if settings_is_new:
        recommended = imaging.recommended_thumbnail_quality()
        if recommended != settings.settings.thumbnail_quality:
            settings.update(thumbnail_quality=recommended)
    migrate_lyrics_file(paths, settings)
    gateway = YTMusicGateway(paths.auth_file, settings.settings.content_language)
    resolver = YtDlpStreamResolver(paths.ytdlp_cache_dir)
    audio = VlcAudioBackend(NETWORK_CACHING_MS)
    queue = PlayQueue(settings.settings.radio_size or None)
    streams = StreamService(resolver, StreamCache(margin=STREAM_EXPIRY_MARGIN_S), play_runner, prefetch_runner)
    catalog = CatalogService(gateway, browse_runner, paths.home_cache_file)
    library = LibraryService(gateway, LocalPlaylistRepository(paths.playlists_file), catalog, browse_runner,
                             RecentPlaylists(paths.recent_playlists_file), PinnedPlaylists(paths.pinned_playlists_file))
    playback = PlaybackService(queue, streams, audio, catalog, notifier, radio_size=lambda: settings.settings.radio_size,
                              auto_queue=lambda: settings.settings.auto_queue)
    navigator = Navigator()
    lyrics = LyricsService(build_lyrics_providers(settings.settings, gateway), browse_runner,
                           romanizer=build_romanizer(), romanize=settings.settings.romanized_lyrics)
    lyrics_state = {"key": (settings.settings.lyrics_providers, settings.settings.better_lyrics_key),
                    "romanize": settings.settings.romanized_lyrics}

    def refresh_lyrics(current: Settings) -> None:
        key = (current.lyrics_providers, current.better_lyrics_key)
        if key != lyrics_state["key"]:
            lyrics_state["key"] = key
            lyrics.set_providers(build_lyrics_providers(current, gateway))
        if current.romanized_lyrics != lyrics_state["romanize"]:
            lyrics_state["romanize"] = current.romanized_lyrics
            lyrics.set_romanize(current.romanized_lyrics)

    settings.changed.connect(refresh_lyrics)
    auto_state = {"on": settings.settings.auto_queue}

    def refresh_auto_queue(current: Settings) -> None:
        if current.auto_queue != auto_state["on"]:
            auto_state["on"] = current.auto_queue
            playback.set_auto_queue(current.auto_queue)

    settings.changed.connect(refresh_auto_queue)

    return Services(
        paths=paths, notifier=notifier, gateway=gateway, resolver=resolver, audio=audio, queue=queue,
        streams=streams, catalog=catalog, library=library,
        lyrics=lyrics,
        auth=AuthService(gateway, auth_runner),
        playback=playback,
        session=SessionService(paths.session_file, queue, streams, runner=browse_runner),
        opener=ItemOpener(catalog, playback, notifier, navigator),
        navigator=navigator,
        collections=CollectionActions(catalog, playback, notifier),
        settings=settings,
        history=SearchHistoryService(paths.search_history_file),
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
    memory: MemoryPresenter
    preferences: SettingsPresenter
    mini: MiniPlayerPresenter
    system: SystemPresenter
    playlist_rail: PlaylistRailPresenter
    song_menu: SongMenuPresenter

    def start(self, services: Services) -> None:
        services.session.restore(load=services.settings.settings.restore_queue)
        self.preferences.start()
        self.system.start()
        self.player.start()
        self.account.start()
        self.home.start()
        services.session.enable_autosave()
        # prefetch playlists so the library opens instantly
        QTimer.singleShot(LIBRARY_PREFETCH_MS, self.window, lambda: services.library.playlists(lambda _items: None))


def build_ui(services: Services, app_icon, login_window_factory: Callable[[], QWidget] | None = None) -> UserInterface:
    thumbnails = ThumbnailCache(services.paths.thumbnail_cache_dir)
    window = MainWindow(thumbnails, app_icon)
    services.notifier.message.connect(window.show_toast)

    make_login = login_window_factory or (lambda: LoginWindow(services.auth, app_icon))
    window.channel_requested.connect(services.navigator.channel_requested)
    pins = ListenAgainPins(services.paths.listen_again_file)
    home = HomePresenter(window, services.catalog, services.playback, services.opener, services.notifier,
                         pins=pins)
    explore = ExplorePresenter(window, services.catalog, services.playback, services.opener, services.notifier)
    playlists = PlaylistPresenter(window, services.catalog, services.library, services.playback,
                                  services.auth, services.notifier)
    memory = MemoryPresenter(window, home, explore, settings=services.settings)
    paths = services.paths
    autostart = Autostart()
    cache = CacheStore(thumbnails, [paths.ytdlp_cache_dir], [paths.home_cache_file])

    def change_language(language: str) -> None:
        services.catalog.change_language(language)
        home.refresh(force=True)
        explore.invalidate()

    interface = UserInterface(
        window=window,
        thumbnails=thumbnails,
        player=PlayerPresenter(window, services.playback, services.navigator, services.library, services.notifier,
                              settings=services.settings),
        home=home,
        explore=explore,
        search=SearchPresenter(window, services.catalog, services.playback, services.opener, services.notifier,
                               services.history),
        library=LibraryPresenter(window, services.library, services.playback, services.opener, services.notifier,
                                 services.navigator),
        lyrics=LyricsPresenter(window, services.playback, services.lyrics),
        similar=SimilarPresenter(window, services.catalog, services.playback, services.opener),
        profiles=ProfilePresenter(window, services.catalog, services.playback, services.opener,
                                  services.navigator, services.notifier, library=services.library),
        playlists=playlists,
        collections=CollectionPresenter(window, services.collections, playlists, services.notifier),
        account=AuthPresenter(window, services.auth, services.catalog, home, make_login, services.notifier),
        memory=memory,
        preferences=SettingsPresenter(window, services.settings, free_now=memory.free_now, cache=cache,
                                      on_language=change_language, autostart_available=autostart.available,
                                      thumbnails=thumbnails),
        mini=MiniPlayerPresenter(window, services.playback, services.settings),
        system=SystemPresenter(window, services.playback, services.settings, MediaKeys(), autostart),
        playlist_rail=PlaylistRailPresenter(window, services.library, services.playback, services.notifier),
        song_menu=SongMenuPresenter(song_hub, services.navigator, pins, services.notifier, home, auth=services.auth),
    )
    memory.on_restore("library", interface.library.reload)
    memory.on_restore("album", interface.profiles.reload)
    memory.on_restore("artist", interface.profiles.reload)
    return interface
