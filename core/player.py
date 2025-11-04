import vlc
import yt_dlp
from PySide6.QtCore import QTimer, QObject, Signal, QThread
import traceback
from datetime import datetime, timedelta


class StreamFetcher(QThread):
    """Thread separado para obtener URLs de stream sin bloquear la UI"""
    finished = Signal(str, str, str)  # video_id, stream_url, title
    error = Signal(str, str)  # video_id, error_message

    def __init__(self, video_id, url):
        super().__init__()
        self.video_id = video_id
        self.url = url

    def run(self):
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                stream_url = info["url"]
                title = info["title"]
                self.finished.emit(self.video_id, stream_url, title)
        except Exception as e:
            print(f"[ERROR] Error al obtener stream para {self.video_id}: {e}")
            self.error.emit(self.video_id, str(e))


class Player(QObject):
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    song_finished = Signal()
    stream_ready = Signal(str, str)  # video_id, title
    stream_error = Signal(str)  # error_message

    def __init__(self):
        super().__init__()
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.is_playing = False

        # Caché de URLs de stream con timestamps
        self.stream_cache = {}  # {video_id: {'url': str, 'title': str, 'timestamp': datetime}}
        self.cache_duration = timedelta(hours=3)  # Las URLs son válidas por ~6 horas

        # Thread de precarga
        self.fetcher_thread = None
        self.pending_video_id = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_position)
        self.timer.start(500)

        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    def _is_cache_valid(self, video_id):
        """Verifica si el caché para un video_id es válido"""
        if video_id not in self.stream_cache:
            return False

        cached_time = self.stream_cache[video_id]['timestamp']
        return datetime.now() - cached_time < self.cache_duration

    def _get_cached_stream(self, video_id):
        """Obtiene el stream del caché si es válido"""
        if self._is_cache_valid(video_id):
            cache_entry = self.stream_cache[video_id]
            print(f"[CACHE HIT] Usando URL cacheada para {video_id}")
            return cache_entry['url'], cache_entry['title']
        return None, None

    def _cache_stream(self, video_id, stream_url, title):
        """Guarda el stream en el caché"""
        self.stream_cache[video_id] = {
            'url': stream_url,
            'title': title,
            'timestamp': datetime.now()
        }
        print(f"[CACHE SAVE] Stream guardado en caché para {video_id}")

    def _on_stream_fetched(self, video_id, stream_url, title):
        """Callback cuando se obtiene un stream en background"""
        self._cache_stream(video_id, stream_url, title)

        # Si este es el video que estamos esperando reproducir
        if video_id == self.pending_video_id:
            print(f"[STREAM READY] Reproduciendo {title}")
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True
            self.stream_ready.emit(video_id, title)
            self.pending_video_id = None

    def _on_stream_error(self, video_id, error_msg):
        """Callback cuando hay un error al obtener el stream"""
        if video_id == self.pending_video_id:
            print(f"[ERROR] No se pudo obtener stream para {video_id}: {error_msg}")
            self.stream_error.emit(error_msg)
            self.pending_video_id = None

    def preload_stream(self, video_id, url):
        """Precarga un stream en background sin bloqueear la UI"""
        # Si ya está en caché y es válido, no hacer nada
        if self._is_cache_valid(video_id):
            print(f"[PRELOAD] Ya existe en caché: {video_id}")
            return

        # Si ya hay un thread corriendo, esperar
        if self.fetcher_thread and self.fetcher_thread.isRunning():
            print(f"[PRELOAD] Esperando thread anterior...")
            return

        print(f"[PRELOAD] Precargando stream para: {video_id}")
        self.fetcher_thread = StreamFetcher(video_id, url)
        self.fetcher_thread.finished.connect(self._on_stream_fetched)
        self.fetcher_thread.error.connect(self._on_stream_error)
        self.fetcher_thread.start()

    def play(self, video_id, url):
        """
        Reproduce una canción. Si está en caché, es instantáneo.
        Si no, la obtiene en background.
        """
        stream_url, title = self._get_cached_stream(video_id)

        if stream_url:
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True
            return title

        print(f"[FETCH] Obteniendo stream para {video_id}...")
        self.pending_video_id = video_id

        if self.fetcher_thread and self.fetcher_thread.isRunning():
            self.fetcher_thread.terminate()
            self.fetcher_thread.wait()

        self.fetcher_thread = StreamFetcher(video_id, url)
        self.fetcher_thread.finished.connect(self._on_stream_fetched)
        self.fetcher_thread.error.connect(self._on_stream_error)
        self.fetcher_thread.start()

        return None

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
            position = self.player.get_position()
            current_time = self.player.get_time() // 1000
            total_time = self.player.get_length() // 1000

            if position >= 0 and total_time > 0:
                self.position_changed.emit(position)
                self.time_changed.emit(current_time, total_time)

    def _on_end_reached(self, event):
        self.is_playing = False
        self.song_finished.emit()

    def clear_cache(self):
        self.stream_cache.clear()
        print("[CACHE] Caché limpiado")

    def get_cache_size(self):
        return len(self.stream_cache)