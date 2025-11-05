import vlc
from PySide6.QtCore import QTimer, QObject, Signal, QThread
import traceback
from datetime import datetime, timedelta
import json
import os
import time


class StreamFetcher(QThread):
    """Thread separado para obtener URLs de stream sin bloquear la UI"""
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
    song_finished = Signal()
    stream_ready = Signal(str, str)  # video_id, title
    stream_error = Signal(str)  # error_message

    def __init__(self, ytmusic_service):
        super().__init__()
        self.ytmusic_service = ytmusic_service
        self.instance = vlc.Instance('--no-video', '--network-caching=2000')
        self.player = self.instance.media_player_new()
        self.is_playing = False

        self.cache_file = 'stream_cache.json'
        self.stream_cache = self._load_cache()
        self.cache_duration = timedelta(hours=4)

        self.fetcher_threads = []
        self.max_concurrent_fetchers = 5
        self.pending_video_id = None
        self.fetch_start_time = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_position)
        self.timer.start(500)

        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for video_id, entry in data.items():
                        entry['timestamp'] = datetime.fromisoformat(entry['timestamp'])
                    print(f"[CACHE] Cargado caché con {len(data)} entradas")
                    return data
            except Exception as e:
                print(f"[CACHE] Error cargando caché: {e}")
                return {}
        return {}

    def _save_cache(self):
        try:
            cache_to_save = {}
            for video_id, entry in self.stream_cache.items():
                cache_to_save[video_id] = {
                    'url': entry['url'],
                    'title': entry['title'],
                    'timestamp': entry['timestamp'].isoformat()
                }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_to_save, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CACHE] Error guardando caché: {e}")

    def _is_cache_valid(self, video_id):
        if video_id not in self.stream_cache:
            return False

        cached_time = self.stream_cache[video_id]['timestamp']
        return datetime.now() - cached_time < self.cache_duration

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

    def _on_stream_fetched(self, video_id, stream_url, title):
        """Callback cuando se obtiene un stream en background"""
        self._cache_stream(video_id, stream_url, title)

        # Si este es el video que estamos esperando reproducir
        if video_id == self.pending_video_id:
            print(f"[STREAM READY] ▶ Reproduciendo: {title}")
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
            media = self.instance.media_new(stream_url)
            self.player.set_media(media)
            self.player.play()
            self.is_playing = True
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