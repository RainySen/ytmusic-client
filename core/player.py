import vlc
import yt_dlp
from PySide6.QtCore import QTimer, QObject, Signal
import traceback  # Importar para imprimir errores detallados


class Player(QObject):
    position_changed = Signal(float)
    time_changed = Signal(int, int)
    song_finished = Signal()

    def __init__(self):
        super().__init__()
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.is_playing = False

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_position)
        self.timer.start(500)

        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    def get_audio_url(self, url):
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
        }

        # --- INICIO DE CAMBIO PARA DEPURACIÓN ---
        # Envolvemos la llamada a yt-dlp en un try-except para capturar el error exacto.
        try:
            print(f"[DEBUG] Obteniendo URL de stream para: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                print("[DEBUG] yt-dlp obtuvo la información correctamente.")
                return info["url"], info["title"]
        except Exception as e:
            print("\n" + "="*50)
            print("[ERROR] yt-dlp no pudo obtener la URL del stream.")
            print(f"      URL solicitada: {url}")
            print(f"      Error: {e}")
            traceback.print_exc()  # Imprime el error completo y detallado
            print("="*50 + "\n")
            return None, None  # Devolvemos None para que la reproducción falle de forma controlada
        # --- FIN DE CAMBIO PARA DEPURACIÓN ---

    def play(self, url):
        stream_url, title = self.get_audio_url(url)

        # Si get_audio_url falló, stream_url será None
        if not stream_url:
            print("[ERROR] No se pudo iniciar la reproducción porque no se obtuvo una URL de stream válida.")
            return None  # Devolvemos None para indicar el fallo

        media = self.instance.media_new(stream_url)
        self.player.set_media(media)
        self.player.play()
        self.is_playing = True
        return title

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