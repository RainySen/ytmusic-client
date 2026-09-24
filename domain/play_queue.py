from __future__ import annotations

import random

from PySide6.QtCore import QObject, Signal

from domain.models import Track

LOOP_OFF = 0
LOOP_QUEUE = 1
LOOP_SONG = 2


# cola reproduccion
class PlayQueue(QObject):
    changed = Signal()
    loop_mode_changed = Signal(int)

    LOOP_OFF = LOOP_OFF
    LOOP_QUEUE = LOOP_QUEUE
    LOOP_SONG = LOOP_SONG

    def __init__(self, radio_limit: int = 6, parent: QObject | None = None):
        super().__init__(parent)
        self._songs: list[Track] = []
        self._index = -1
        self._detached = False
        self._loop_mode = LOOP_OFF
        self._radio_limit = radio_limit
        self._radio_seed: str | None = None

    def __len__(self) -> int:
        return len(self._songs)

    def snapshot(self) -> list[Track]:
        return list(self._songs)

    @property
    def current(self) -> Track | None:
        if self._detached or not (0 <= self._index < len(self._songs)):
            return None
        return self._songs[self._index]

    @property
    def current_index(self) -> int:
        return -1 if self._detached else self._index

    @property
    def loop_mode(self) -> int:
        return self._loop_mode

    @property
    def radio_seed(self) -> str | None:
        return self._radio_seed

    @property
    def last(self) -> Track | None:
        return self._songs[-1] if self._songs else None

    def remaining_after_current(self) -> int:
        return max(0, len(self._songs) - self._index - 1)

    def upcoming(self, count: int) -> list[Track]:
        start = self._index + 1
        return self._songs[start:start + count]

    def contains(self, video_id: str) -> bool:
        return any(s.get("videoId") == video_id for s in self._songs)

    def video_ids(self) -> set[str]:
        return {s.get("videoId") for s in self._songs if s.get("videoId")}

    # cola avanzar
    def next(self) -> Track | None:
        if self._index < len(self._songs) - 1:
            self._index += 1
        elif self._loop_mode == LOOP_QUEUE and self._songs:
            self._index = 0
        else:
            return None
        self._detached = False
        self.changed.emit()
        return self._songs[self._index]

    def previous(self) -> Track | None:
        target = self._index if self._detached else self._index - 1
        if not (0 <= target < len(self._songs)):
            return None
        self._index = target
        self._detached = False
        self.changed.emit()
        return self._songs[self._index]

    def jump_to(self, index: int) -> Track | None:
        if not (0 <= index < len(self._songs)):
            return None
        self._index = index
        self._detached = False
        self.changed.emit()
        return self._songs[index]

    # cola reemplazar
    def replace(self, songs: list[Track], index: int = 0, radio_seed: str | None = None) -> Track | None:
        self._songs = list(songs)
        self._radio_seed = radio_seed
        self._detached = False
        self._index = index if 0 <= index < len(self._songs) else (0 if self._songs else -1)
        self.changed.emit()
        return self.current

    def restore(self, songs: list[Track], index: int) -> None:
        songs = [s for s in songs if isinstance(s, dict) and s.get("videoId")]
        self._songs = songs
        self._radio_seed = None
        self._detached = False
        self._index = index if 0 <= index < len(songs) else -1
        self.changed.emit()

    def append(self, song: Track) -> bool:
        self._songs.append(song)
        became_current = len(self._songs) == 1 and self._index == -1
        if became_current:
            self._index = 0
            self._detached = False
        self.changed.emit()
        return became_current

    # cola siguiente
    def insert_next(self, song: Track) -> bool:
        if self._index == -1 and not self._songs:
            return self.append(song)
        self._songs.insert(self._index + 1, song)
        self.changed.emit()
        return False

    def append_many(self, songs: list[Track]) -> bool:
        if not songs:
            return False
        was_empty = not self._songs and self._index == -1
        self._songs.extend(songs)
        if was_empty:
            self._index = 0
            self._detached = False
        self.changed.emit()
        return was_empty

    def insert_next_many(self, songs: list[Track]) -> bool:
        if not songs:
            return False
        if self._index == -1 and not self._songs:
            return self.append_many(songs)
        self._songs[self._index + 1:self._index + 1] = songs
        self.changed.emit()
        return False

    def play_now(self, song: Track) -> Track:
        self._songs.insert(self._index + 1, song)
        self._index += 1
        self._detached = False
        self._radio_seed = None
        self.changed.emit()
        return song

    def remove_at(self, index: int) -> None:
        if not (0 <= index < len(self._songs)):
            return
        self._songs.pop(index)
        if index < self._index or (self._detached and index == self._index):
            self._index -= 1
        elif index == self._index:
            self._index -= 1
            self._detached = True
        if not self._songs:
            self._index = -1
            self._detached = False
        self.changed.emit()

    def move(self, source: int, destination: int) -> None:
        n = len(self._songs)
        if not (0 <= source < n and 0 <= destination <= n):
            return
        song = self._songs.pop(source)
        final = destination - 1 if source < destination else destination
        self._songs.insert(final, song)
        if not self._detached:
            if self._index == source:
                self._index = final
            elif source < self._index <= final:
                self._index -= 1
            elif final <= self._index < source:
                self._index += 1
        self.changed.emit()

    def clear_except_current(self) -> None:
        current = self.current
        self._radio_seed = None
        self._songs = [current] if current else []
        self._index = 0 if current else -1
        self._detached = False
        self.changed.emit()

    # cola aleatorio
    def shuffle_upcoming(self, rng: random.Random | None = None) -> None:
        start = self._index + 1
        upcoming = self._songs[start:]
        if len(upcoming) < 2:
            return
        (rng or random).shuffle(upcoming)
        self._songs[start:] = upcoming
        self.changed.emit()

    def trim_played(self, keep: int) -> int:
        excess = self._index - keep
        if excess <= 0:
            return 0
        del self._songs[:excess]
        self._index -= excess
        self.changed.emit()
        return excess

    # cola extender
    def extend_unique(self, songs: list[Track], limit: int | None = None) -> int:
        seen = self.video_ids()
        added = 0
        for song in songs:
            vid = song.get("videoId") if isinstance(song, dict) else None
            if not vid or vid in seen:
                continue
            if limit is not None and len(self._songs) >= limit:
                break
            self._songs.append(song)
            seen.add(vid)
            added += 1
        if added:
            if self._index == -1:
                self._index = 0
            self.changed.emit()
        return added

    # cola radio
    def start_radio(self, seed: Track) -> Track | None:
        return self.replace([seed], 0, radio_seed=seed.get("videoId"))

    def add_radio_tail(self, seed_video_id: str, recommendations: list[Track]) -> int:
        if self._radio_seed != seed_video_id:
            return 0
        return self.extend_unique(recommendations, limit=self._radio_limit)

    def toggle_loop(self) -> int:
        self._loop_mode = (self._loop_mode + 1) % 3
        self.loop_mode_changed.emit(self._loop_mode)
        return self._loop_mode
