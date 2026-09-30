from typing import Callable

# fetch(limit, done) -> done(items | None, total | None), items from the start
Fetch = Callable[[int, Callable[..., None]], None]
# deliver(new_items | None, has_more, append)
Deliver = Callable[[list | None, bool, bool], None]


# no cursor in ytmusicapi: ask for shown + step and prefetch the next page
class Pager:
    def __init__(self, fetch: Fetch, deliver: Deliver, step: int, cap: int):
        self._fetch = fetch
        self._deliver = deliver
        self._step = step
        self._cap = cap
        self._generation = 0
        self._shown = 0
        self._ready: tuple | None = None
        self._wanted = False
        self._busy = False
        self._done = True

    def start(self, first: int) -> None:
        self._reset()
        self._done = False
        self._wanted = True
        self._request(first)

    def resume(self, shown: int, has_more: bool) -> None:
        self._reset()
        self._shown = shown
        self._done = not has_more
        if has_more:
            self._request(shown + self._step)

    def stop(self) -> None:
        self._reset()

    def more(self) -> None:
        if self._done:
            self._deliver([], False, True)
        elif self._ready is not None:
            self._show(*self._ready)
        else:
            self._wanted = True
            if not self._busy:
                self._request(self._shown + self._step)

    def _reset(self) -> None:
        self._generation += 1
        self._shown = 0
        self._ready = None
        self._wanted = False
        self._busy = False
        self._done = True

    def _request(self, limit: int) -> None:
        generation = self._generation
        self._busy = True

        def done(items, total=None):
            if generation != self._generation:
                return
            self._busy = False
            if self._wanted:
                self._show(items, total)
            else:
                self._ready = (items, total)

        self._fetch(limit, done)

    def _show(self, items, total) -> None:
        self._wanted = False
        self._ready = None
        append = self._shown > 0
        if items is None:
            self._done = True
            self._deliver([] if append else None, False, append)
            return
        new = items[self._shown:self._cap]
        grew = len(items) > self._shown
        self._shown = max(self._shown, min(len(items), self._cap))
        has_more = grew and self._shown < self._cap and (total is None or self._shown < total)
        self._done = not has_more
        self._deliver(new, has_more, append)
        if has_more:
            self._request(self._shown + self._step)
