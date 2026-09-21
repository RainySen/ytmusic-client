class MusicController:
    def __init__(self, app_controller):
        self.app = app_controller

    def preload_next_songs(self, count=5):
        q = self.app.queue_manager.get_queue()
        curr = self.app.queue_manager.get_current_index()
        for i in range(1, count + 1):
            if curr + i < len(q):
                self.app.player.preload_stream(q[curr + i].get("videoId"))

    def play_song(self, song_data):
        if not song_data or "videoId" not in song_data:
            self.app.window.update_song_info("Error canción")
            return

        self.app.current_lyrics_lines = []
        self.app.lyrics_active = False
        self.app.last_highlighted_index = -1

        self.app.window.set_lyrics_message("...", switch_focus=False)

        video_id = song_data["videoId"]
        artist = song_data.get('artists', [{}])[0].get('name', 'Desconocido')
        self.app.window.update_play_button_icon(True)
        self.app.window.update_song_info(f"Cargando: {song_data['title']} - {artist}")

        if self.app.player.play(video_id):
            self.app.window.update_song_info(f"{song_data['title']} - {artist}")

    def on_stream_ready(self, video_id, title):
        s = self.app.queue_manager.get_current()
        if s and s.get("videoId") == video_id:
            artist = s.get('artists', [{}])[0].get('name', 'Desconocido')
            self.app.window.update_song_info(f"{title} - {artist}")
            self.app.window.update_play_button_icon(True)

    def on_stream_error(self, msg):
        self.app.window.update_song_info(f"Error: {msg}")
        self.app.window.update_play_button_icon(False)

    def handle_toggle_play(self):
        if not self.app.player.has_media_loaded() and not self.app.player.is_playing:
            s = self.app.queue_manager.get_current()
            if s:
                self.play_song(s)
        else:
            self.app.player.toggle_play()
            self.app.window.update_play_button_icon(self.app.player.is_playing)

    def handle_volume_change(self, val):
        self.app.player.set_volume(val)

    def handle_seek(self, pos):
        self.app.player.seek(pos)

    def handle_next(self):
        s = self.app.queue_manager.next()
        if s:
            self.play_song(s)
            self.preload_next_songs(5)

    def handle_previous(self):
        s = self.app.queue_manager.previous()
        if s:
            self.play_song(s)

    def handle_remove_from_queue(self, idx):
        self.app.queue_manager.remove_at(idx)

    def handle_queue_item_selected(self, idx):
        s = self.app.queue_manager.jump_to(idx)
        if s:
            self.play_song(s)
            self.preload_next_songs(5)

    def handle_show_lyrics(self):
        s = self.app.queue_manager.get_current()
        if not s:
            self.app.window.set_lyrics_message("Sin canción", switch_focus=False)
            return

        self.app.window.set_lyrics_message(f"Buscando letra de:\n{s['title']}...", switch_focus=True)
        lyrics_data = self.app.service.get_song_lyrics(s.get("videoId"))

        if s != self.app.queue_manager.get_current():
            return

        if lyrics_data:
            if 'lines' in lyrics_data and lyrics_data['lines']:
                raw_lines = lyrics_data['lines']
                processed_lines = []
                has_timing = False

                for line in raw_lines:
                    text = line.get('text', '')
                    t_str = line.get('time', '0:00')
                    t_ms = self.time_str_to_ms(t_str)
                    if t_ms > 0:
                        has_timing = True
                    processed_lines.append({'text': text, 'time_ms': t_ms})

                self.app.current_lyrics_lines = processed_lines
                self.app.lyrics_active = has_timing
                self.app.last_highlighted_index = -1
                self.app.window.set_lyrics_lines([l['text'] for l in processed_lines])
            elif lyrics_data.get('lyrics'):
                self.app.current_lyrics_lines = []
                self.app.lyrics_active = False
                self.app.window.set_lyrics_lines(lyrics_data['lyrics'].split('\n'))
            else:
                self.app.window.set_lyrics_message("Formato desconocido.", switch_focus=True)
        else:
            self.app.window.set_lyrics_message("Letra no encontrada.", switch_focus=True)

    @staticmethod
    def time_str_to_ms(time_str):
        if not time_str:
            return 0
        try:
            parts = time_str.split(':')
            seconds = 0
            if len(parts) == 2:
                seconds = int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            else:
                seconds = float(time_str)
            return int(seconds * 1000)
        except Exception:
            return 0

    def on_time_ms_updated(self, current_ms):
        if not self.app.lyrics_active or not self.app.current_lyrics_lines:
            return

        active_index = -1
        start = max(0, self.app.last_highlighted_index)

        for i in range(start, len(self.app.current_lyrics_lines)):
            line_time = self.app.current_lyrics_lines[i]['time_ms']
            if current_ms >= line_time:
                active_index = i
            else:
                break

        if active_index != -1 and active_index != self.app.last_highlighted_index:
            self.app.window.highlight_lyric_index(active_index)
            self.app.last_highlighted_index = active_index
