import vlc
from PySide6.QtCore import QTimer, QObject, Signal, QThread
import traceback
from datetime import datetime, timedelta


class StreamFetcher(QThread):
    finished = Signal(str, str, str)  # video_id, stream_url, title
    error = Signal(str, str)  # video_id, error_message

    def __init__(self, video_id, ytmusic_service):
        super().__init__()
        self.video_id = video_id
        self.ytmusic_service = ytmusic_service

    def run(self):
        try:
            result = self.ytmusic_service.get_song_stream_info(self.video_id)
            if result:
                stream_url, title = result
                self.finished.emit(self.video_id, stream_url, title)
            else:
                self.error.emit(self.video_id, "No se pudo obtener el stream")
        except Exception as e:
            print(f"[ERROR] Error al obtener stream para {self.video_id}: {e}")
            traceback.print_exc()
            self.error.emit(self.video_id, str(e))


class Player(QObject):
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    current_time_ms = Signal(int)
    song_finished = Signal()
    stream_ready = Signal(str, str)
    stream_error = Signal(str)

    def __init__(self, ytmusic_service):
        super().__init__()
        self.ytmusic_service = ytmusic_service

        from platform_utils import get_vlc_instance_args
        vlc_args = get_vlc_instance_args()

        try:
            self.instance = vlc.Instance(*vlc_args)
            self.player = self.instance.media_player_new()
        except Exception as e:
            print(f"[VLC] Error al inicializar VLC: {e}")
            print(f"[VLC] Intentando inicialización básica...")
            self.instance = vlc.Instance()
            self.player = self.instance.media_player_new()

        self.is_playing = False

        self.stream_cache = {}
        self.cache_duration = timedelta(hours=2)

        self.fetcher_threads = []
        self.max_concurrent_fetchers = 5
        self.pending_video_id = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_position)
        self.timer.start(100)

        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    def set_stream_cache(self, cache_data):
        if not cache_data:
            print("[CACHE] No hay caché para restaurar")
            return
        try:
            restored_count = 0
            expired_count = 0
            now = datetime.now()

            for video_id, entry in cache_data.items():
                try:
                    if isinstance(entry.get('timestamp'), str):
                        entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])

                    cache_age = now - entry['timestamp']
                    if cache_age < self.cache_duration:
                        self.stream_cache[video_id] = entry
                        restored_count += 1
                    else:
                        expired_count += 1
                        print(f"[CACHE] Stream expirado descartado: {entry.get('title', video_id)}")

                except Exception as e:
                    print(f"[CACHE] Error restaurando entrada {video_id}: {e}")
                    continue

            print(f"[CACHE] Caché restaurado: {restored_count} válidos, {expired_count} expirados")

        except Exception as e:
            print(f"[CACHE] Error restaurando caché: {e}")
            self.stream_cache = {}

    def get_stream_cache_for_saving(self):
        cache_to_save = {}
        try:
            now = datetime.now()
            saved_count = 0

            for video_id, entry in self.stream_cache.items():
                try:
                    cache_age = now - entry['timestamp']
                    if cache_age < self.cache_duration:
                        cache_to_save[video_id] = {
                            'url': entry['url'],
                            'title': entry['title'],
                            'timestamp': entry['timestamp'].isoformat()
                        }
                        saved_count += 1
                except Exception as e:
                    continue

            print(f"[CACHE] Guardando {saved_count} streams válidos")
            return cache_to_save

        except Exception as e:
            print(f"[CACHE] Error preparando caché para guardar: {e}")
            return {}

    def _is_cache_valid(self, video_id):
        if video_id not in self.stream_cache:
            return False
        cached_time = self.stream_cache[video_id]['timestamp']
        age = datetime.now() - cached_time

        # Log cuando el caché expira
        if age >= self.cache_duration:
            print(f"[CACHE] Caché expirado para {self.stream_cache[video_id].get('title', video_id)} (edad: {age})")
            return False

        return True

    def _get_cached_stream(self, video_id):
        if self._is_cache_valid(video_id):
            cache_entry = self.stream_cache[video_id]
            return cache_entry['url'], cache_entry['title']
        return None, None

    def _cache_stream(self, video_id, stream_url, title):
        self.stream_cache[video_id] = {
            'url': stream_url,
            'title': title,
            'timestamp': datetime.now()
        }
        print(f"[CACHE] Stream cacheado: {title}")

    def _on_stream_fetched(self, video_id, stream_url, title):
        self._cache_stream(video_id, stream_url, title)
        if video_id == self.pending_video_id:
            print(f"[STREAM READY] Reproduciendo: {title}")
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True
            self.stream_ready.emit(video_id, title)
            self.pending_video_id = None

    def _on_stream_error(self, video_id, error_msg):
        if video_id == self.pending_video_id:
            print(f"[ERROR] No se pudo obtener stream para {video_id}: {error_msg}")
            self.stream_error.emit(error_msg)
            self.pending_video_id = None

    def preload_stream(self, video_id):
        if self._is_cache_valid(video_id):
            return
        self.fetcher_threads = [t for t in self.fetcher_threads if t.isRunning()]
        if len(self.fetcher_threads) >= self.max_concurrent_fetchers:
            return
        for thread in self.fetcher_threads:
            if thread.video_id == video_id:
                return
        fetcher = StreamFetcher(video_id, self.ytmusic_service)
        fetcher.finished.connect(self._on_stream_fetched)
        fetcher.error.connect(self._on_stream_error)
        fetcher.start()
        self.fetcher_threads.append(fetcher)

    def play(self, video_id):
        stream_url, title = self._get_cached_stream(video_id)
        if stream_url:
            print(f"[PLAY] Usando caché: {title}")
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True

            import time
            time.sleep(0.3)
            state = self.player.get_state()

            if state == vlc.State.Error:
                print(f"[ERROR] VLC reportó error, el stream probablemente expiró")
                print(f"[CACHE] Descartando caché y obteniendo nuevo stream...")
                # Eliminar de caché y reintentar
                del self.stream_cache[video_id]
                return self.play(video_id)

            return title

        self.pending_video_id = video_id
        self.fetcher_threads = [t for t in self.fetcher_threads if t.isRunning()]
        for thread in self.fetcher_threads:
            if thread.video_id == video_id and thread.isRunning():
                return None

        low_priority_count = 0
        for thread in self.fetcher_threads[:]:
            if thread.video_id != video_id and thread.isRunning():
                low_priority_count += 1
                if low_priority_count > 2:
                    thread.terminate()
                    thread.wait()
                    self.fetcher_threads.remove(thread)

        fetcher = StreamFetcher(video_id, self.ytmusic_service)
        fetcher.finished.connect(self._on_stream_fetched)
        fetcher.error.connect(self._on_stream_error)
        fetcher.start()
        self.fetcher_threads.insert(0, fetcher)
        return None

    def has_media_loaded(self):
        return self.player.get_media() is not None

    def toggle_play(self):
        self.player.pause()
        self.is_playing = not self.is_playing

    def set_volume(self, volume):
        self.player.audio_set_volume(volume)

    def seek(self, position):
        if self.player.get_media():
            self.player.set_position(position)

    def _update_position(self):
        if self.player.get_media() and self.is_playing:
            current_time_ms = self.player.get_time()
            position = self.player.get_position()
            current_seconds = current_time_ms // 1000
            total_time = self.player.get_length() // 1000

            if position >= 0 and total_time > 0:
                self.position_changed.emit(position)
                self.time_changed.emit(current_seconds, total_time)
                self.current_time_ms.emit(current_time_ms)

    def _on_end_reached(self, event):
        self.is_playing = False
        self.song_finished.emit()

    def clear_cache(self):
        count = len(self.stream_cache)
        self.stream_cache.clear()
        print(f"[CACHE] Caché limpiado ({count} streams eliminados)")

    def get_cache_size(self):
        return len(self.stream_cache)