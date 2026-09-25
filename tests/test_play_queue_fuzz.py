import random

import pytest

from domain.play_queue import PlayQueue


def track(n):
    return {"videoId": f"v{n}", "title": f"T{n}"}


OPS = ("next", "previous", "jump", "replace", "restore", "append", "insert_next", "append_many", "insert_next_many",
       "play_now", "remove", "move", "clear", "shuffle", "trim", "extend", "radio", "loop")


def apply(queue, op, rng, counter):
    n = len(queue)
    pick = lambda: rng.choice((-2, -1, 0, 1, max(n - 1, 0), n, n + 2, rng.randrange(max(n, 1))))
    songs = lambda: [track(next(counter)) for _ in range(rng.randrange(0, 5))]
    if op == "next":
        queue.next()
    elif op == "previous":
        queue.previous()
    elif op == "jump":
        queue.jump_to(pick())
    elif op == "replace":
        queue.replace(songs(), pick(), radio_seed=rng.choice((None, "v1")))
    elif op == "restore":
        queue.restore(songs() + [None, {"x": 1}, 5], pick())
    elif op == "append":
        queue.append(track(next(counter)))
    elif op == "insert_next":
        queue.insert_next(track(next(counter)))
    elif op == "append_many":
        queue.append_many(songs())
    elif op == "insert_next_many":
        queue.insert_next_many(songs())
    elif op == "play_now":
        queue.play_now(track(next(counter)))
    elif op == "remove":
        queue.remove_at(pick())
    elif op == "move":
        queue.move(pick(), pick())
    elif op == "clear":
        queue.clear_except_current()
    elif op == "shuffle":
        queue.shuffle_upcoming(rng)
    elif op == "trim":
        queue.trim_played(rng.choice((0, 1, 3, 50)))
    elif op == "extend":
        queue.extend_unique(songs() + [None, {"videoId": None}], limit=rng.choice((None, 3, 10)))
    elif op == "radio":
        queue.add_radio_tail("v1", songs())
    else:
        queue.toggle_loop()


def check(queue):
    size = len(queue)
    index = queue.current_index
    assert -1 <= index < size or (index == -1), (index, size)
    if size == 0:
        assert queue.current is None and queue.current_index == -1
    if queue.current is not None:
        assert 0 <= index < size
    assert queue.remaining_after_current() >= 0
    assert all(isinstance(s, dict) for s in queue.snapshot())


@pytest.mark.parametrize("seed", range(150))
def test_random_queue_operations_keep_the_queue_consistent(seed):
    rng = random.Random(seed)
    queue = PlayQueue(radio_limit=rng.choice((3, 6)))
    counter = iter(range(10 ** 6))
    for _ in range(120):
        op = rng.choice(OPS)
        try:
            apply(queue, op, rng, counter)
            check(queue)
        except Exception as exc:
            raise AssertionError(f"seed {seed} op {op}: {exc!r}") from exc
