from PySide6.QtCore import QObject, Signal


class QueueManager(QObject):
    queue_updated = Signal()
    current_changed = Signal(int)
    loop_mode_changed = Signal(int)
    autoplay_mode_changed = Signal(bool)  # Nueva señal

    LOOP_OFF = 0
    LOOP_QUEUE = 1
    LOOP_SONG = 2

    def __init__(self):
        super().__init__()
        self.queue = []
        self.current_index = -1
        self.loop_mode = self.LOOP_OFF
        self.autoplay_enabled = False  # Nueva propiedad

    def toggle_autoplay(self):
        """Activa o desactiva el modo de reproducción automática"""
        self.autoplay_enabled = not self.autoplay_enabled

        # Si se activa autoplay y hay un modo de loop activo, desactiva el loop
        if self.autoplay_enabled and self.loop_mode != self.LOOP_OFF:
            self.loop_mode = self.LOOP_OFF
            self.loop_mode_changed.emit(self.loop_mode)
            print("[LOOP] Desactivado automáticamente (autoplay activado)")

        print(f"[AUTOPLAY] Modo {'activado' if self.autoplay_enabled else 'desactivado'}")
        self.autoplay_mode_changed.emit(self.autoplay_enabled)

    def is_autoplay_enabled(self):
        return self.autoplay_enabled

    def should_autoplay(self):
        if not self.autoplay_enabled:
            return False

        # Si hay modo de repetición activo, no usa autoplay
        if self.loop_mode != self.LOOP_OFF:
            return False

        # Verificar si estamos en la última canción
        return self.current_index >= len(self.queue) - 1

    def toggle_loop_mode(self):
        if self.loop_mode == self.LOOP_OFF:
            self.loop_mode = self.LOOP_QUEUE
            # Desactivar autoplay cuando se activa el loop
            if self.autoplay_enabled:
                self.autoplay_enabled = False
                self.autoplay_mode_changed.emit(self.autoplay_enabled)
                print("[AUTOPLAY] Desactivado automáticamente (loop activado)")
        elif self.loop_mode == self.LOOP_QUEUE:
            self.loop_mode = self.LOOP_SONG
        else:
            self.loop_mode = self.LOOP_OFF

        print(f"[LOOP] Modo cambiado a: {self.loop_mode}")
        self.loop_mode_changed.emit(self.loop_mode)

    def get_loop_mode(self):
        return self.loop_mode

    def set_queue_state(self, queue, current_index):
        """
        Restaura el estado completo de la cola.
        """
        if not queue:
            print("[QUEUE] Cola guardada vacía, no se restaura nada")
            self.queue = []
            self.current_index = -1
            return

        try:
            self.queue = queue
            self.current_index = current_index

            # Validar que el índice esté en rango
            if self.current_index >= len(self.queue):
                print(f"[QUEUE] Índice fuera de rango ({self.current_index} >= {len(self.queue)}), ajustando a -1")
                self.current_index = -1
            elif self.current_index < -1:
                print(f"[QUEUE] Índice inválido ({self.current_index}), ajustando a -1")
                self.current_index = -1

            print(f"[QUEUE] Estado restaurado: {len(self.queue)} canciones, índice {self.current_index}")

            # Emitir señales para actualizar la UI
            self.queue_updated.emit()
            if self.current_index >= 0:
                self.current_changed.emit(self.current_index)

        except Exception as e:
            print(f"[QUEUE] Error restaurando estado: {e}")
            self.queue = []
            self.current_index = -1

    def add_song(self, song_data):
        self.queue.append(song_data)
        self.queue_updated.emit()

        if len(self.queue) == 1 and self.current_index == -1:
            self.current_index = 0
            self.current_changed.emit(self.current_index)
            return song_data

        return None

    def play_now(self, song_data):
        if self.current_index >= len(self.queue):
            self.current_index = len(self.queue) - 1

        if self.current_index >= 0:
            self.queue.insert(self.current_index + 1, song_data)
            self.current_index += 1
        else:
            self.queue.append(song_data)
            self.current_index = 0

        self.queue_updated.emit()
        self.current_changed.emit(self.current_index)

        if 0 <= self.current_index < len(self.queue):
            return self.queue[self.current_index]
        return None

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

    def add_next(self, song_data):
        # Validación de seguridad
        if self.current_index >= len(self.queue):
            self.current_index = len(self.queue) - 1

        if self.current_index == -1:
            return self.add_song(song_data)
        else:
            self.queue.insert(self.current_index + 1, song_data)
            self.queue_updated.emit()
            print(f"[QUEUE] '{song_data['title']}' añadida como siguiente.")
            return None

    def previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.current_changed.emit(self.current_index)
            return self.queue[self.current_index]

        return None

    def remove_at(self, index):
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

            if index < self.current_index:
                self.current_index -= 1
            elif index == self.current_index:
                # --- CORRECCIÓN DE BUG ---
                # Si borramos la canción actual y era la última o la única,
                # el índice queda fuera de rango. Debemos ajustarlo.
                if self.current_index >= len(self.queue):
                    self.current_index = len(self.queue) - 1

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

        song_to_move = self.queue.pop(source_index)

        final_dest_index = dest_index
        if source_index < final_dest_index:
            final_dest_index -= 1

        self.queue.insert(final_dest_index, song_to_move)

        if self.current_index == source_index:
            self.current_index = final_dest_index
        elif source_index < self.current_index <= final_dest_index:
            self.current_index -= 1
        elif source_index > self.current_index >= final_dest_index:
            self.current_index += 1

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