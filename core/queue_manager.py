from PySide6.QtCore import QObject, Signal


class QueueManager(QObject):
    queue_updated = Signal()
    current_changed = Signal(int)
    loop_mode_changed = Signal(int)

    LOOP_OFF = 0
    LOOP_QUEUE = 1
    LOOP_SONG = 2

    def __init__(self):
        super().__init__()
        self.queue = []
        self.current_index = -1
        self.loop_mode = self.LOOP_OFF

    def toggle_loop_mode(self):
        if self.loop_mode == self.LOOP_OFF:
            self.loop_mode = self.LOOP_QUEUE
        elif self.loop_mode == self.LOOP_QUEUE:
            self.loop_mode = self.LOOP_SONG
        else:
            self.loop_mode = self.LOOP_OFF

        print(f"[LOOP] Modo cambiado a: {self.loop_mode}")
        self.loop_mode_changed.emit(self.loop_mode)

    def get_loop_mode(self):
        return self.loop_mode

    def add_song(self, song_data):
        self.queue.append(song_data)
        self.queue_updated.emit()

        if len(self.queue) == 1 and self.current_index == -1:
            self.current_index = 0
            self.current_changed.emit(self.current_index)
            return song_data

        return None

    def play_now(self, song_data):
        if self.current_index >= 0:
            self.queue.insert(self.current_index + 1, song_data)
            self.current_index += 1
        else:
            self.queue.append(song_data)
            self.current_index = 0

        self.queue_updated.emit()
        self.current_changed.emit(self.current_index)
        return self.queue[self.current_index]

    def next(self):
        if self.current_index < len(self.queue) - 1:
            self.current_index += 1
            self.current_changed.emit(self.current_index)
            return self.queue[self.current_index]

        elif self.loop_mode == self.LOOP_QUEUE and len(self.queue) > 0:
            print("[LOOP] Repitiendo cola, volviendo al inicio.")
            self.current_index = 0
            self.current_changed.emit(self.current_index)
            return self.queue[self.current_index]

        return None

    def previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.current_changed.emit(self.current_index)
            return self.queue[self.current_index]

        # elif self.loop_mode == self.LOOP_QUEUE and len(self.queue) > 0:
        #     print("[LOOP] Repitiendo cola (hacia atrás), yendo al final.")
        #     self.current_index = len(self.queue) - 1
        #     self.current_changed.emit(self.current_index)
        #     return self.queue[self.current_index]

        return None

    def remove_at(self, index):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index:
                pass

            self.queue_updated.emit()

    def clear(self):
        current_song = self.get_current()

        if current_song:
            self.queue = [current_song]
            self.current_index = 0
        else:
            self.queue.clear()
            self.current_index = -1

        self.queue_updated.emit()

    def move_song(self, source_index, dest_index):
        if not (0 <= source_index < len(self.queue)):
            print(f"[QUEUE] Error: source_index {source_index} fuera de límites")
            return

        if not (0 <= dest_index <= len(self.queue)):
            print(f"[QUEUE] Error: dest_index {dest_index} fuera de límites")
            return

        # Sacar la canción de la lista
        song_to_move = self.queue.pop(source_index)

        # Si el destino estaba *después* de la fuente, su índice bajó en 1
        final_dest_index = dest_index
        if source_index < final_dest_index:
            final_dest_index -= 1

        # Insertar la canción en la nueva posición
        self.queue.insert(final_dest_index, song_to_move)

        # Si movimos la canción que ESTÁ SONANDO
        if self.current_index == source_index:
            self.current_index = final_dest_index

        # Si movimos algo de ANTES a DESPUÉS de la canción actual
        # (El índice actual debe bajar 1)
        elif source_index < self.current_index <= final_dest_index:
            self.current_index -= 1

        # Si movimos algo de DESPUÉS a ANTES de la canción actual
        # (El índice actual debe subir 1)
        elif source_index > self.current_index >= final_dest_index:
            self.current_index += 1

        # Esto llama a 'on_queue_updated' en app.py, que actualiza la UI
        self.queue_updated.emit()

    def get_current(self):

        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

    def get_queue(self):

        return self.queue

    def get_current_index(self):

        return self.current_index

    def jump_to(self, index):
        if 0 <= index < len(self.queue):
            self.current_index = index
            self.current_changed.emit(self.current_index)
            return self.queue[self.current_index]
        return None

    def has_next(self):
        return self.current_index < len(self.queue) - 1

    def has_previous(self):
        return self.current_index > 0