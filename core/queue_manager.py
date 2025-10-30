from PySide6.QtCore import QObject, Signal


class QueueManager(QObject):
    queue_updated = Signal()
    current_changed = Signal(int)

    def __init__(self):
        super().__init__()
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
                pass

            self.queue_updated.emit()

    def clear(self):

        self.queue.clear()
        self.current_index = -1
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