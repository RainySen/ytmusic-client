import threading
import time

from infra.concurrency import TaskRunner


def test_callback_runs_on_main_thread(qapp, wait_until):
    runner = TaskRunner("t", 2)
    seen = {}

    def work():
        seen["worker"] = threading.get_ident()
        return 42

    runner.submit(work, lambda r: seen.update(result=r, main=threading.get_ident()))
    assert wait_until(lambda: "result" in seen)
    assert seen["result"] == 42
    assert seen["main"] == threading.get_ident() != seen["worker"]
    runner.shutdown()


def test_errors_reach_on_error(qapp, wait_until):
    runner = TaskRunner("t", 2)
    errors = []

    def boom():
        raise ValueError("bad")

    runner.submit(boom, on_error=errors.append)
    assert wait_until(lambda: errors)
    assert isinstance(errors[0], ValueError)
    runner.shutdown()


def test_latest_wins_per_key(qapp, wait_until):
    runner = TaskRunner("t", 1)
    got = []
    gate = threading.Event()

    runner.submit(lambda: (gate.wait(1), "old")[1], got.append, key="k")
    runner.submit(lambda: "new", got.append, key="k")
    gate.set()
    assert wait_until(lambda: got)
    time.sleep(0.05)
    wait_until(lambda: False, 100)
    assert got == ["new"]
    runner.shutdown()


def test_running_task_result_dropped_when_superseded(qapp, wait_until):
    runner = TaskRunner("t", 4)
    got = []
    started = threading.Event()
    release = threading.Event()

    def slow():
        started.set()
        release.wait(2)
        return "stale"

    runner.submit(slow, got.append, key="k")
    assert started.wait(2)
    runner.submit(lambda: "fresh", got.append, key="k")
    assert wait_until(lambda: got)
    release.set()
    wait_until(lambda: False, 150)
    assert got == ["fresh"]
    runner.shutdown()


def test_cancel_queued_task(qapp, wait_until):
    runner = TaskRunner("t", 1)
    got = []
    gate = threading.Event()
    runner.submit(lambda: gate.wait(1), None)
    handle = runner.submit(lambda: "x", got.append)
    assert handle.cancel() is True
    gate.set()
    wait_until(lambda: False, 150)
    assert got == []
    runner.shutdown()


def test_cancel_if_queued_leaves_running_task(qapp, wait_until):
    runner = TaskRunner("t", 2)
    got = []
    started = threading.Event()
    release = threading.Event()

    def slow():
        started.set()
        release.wait(2)
        return "done"

    handle = runner.submit(slow, got.append)
    assert started.wait(2)
    assert handle.cancel_if_queued() is False
    release.set()
    assert wait_until(lambda: got)
    assert got == ["done"]
    runner.shutdown()


def test_gather_collects_results_and_exceptions(qapp, wait_until):
    runner = TaskRunner("t", 3)
    out = []

    def bad():
        raise RuntimeError("x")

    runner.gather([lambda: 1, bad, lambda: 3], out.append)
    assert wait_until(lambda: out)
    results = out[0]
    assert results[0] == 1 and results[2] == 3
    assert isinstance(results[1], RuntimeError)
    runner.shutdown()


def test_gather_latest_wins(qapp, wait_until):
    runner = TaskRunner("t", 4)
    out = []
    gate = threading.Event()
    runner.gather([lambda: (gate.wait(1), "a")[1]], out.append, key="g")
    runner.gather([lambda: "b"], out.append, key="g")
    assert wait_until(lambda: out)
    gate.set()
    wait_until(lambda: False, 150)
    assert out == [["b"]]
    runner.shutdown()


def test_callback_exception_does_not_break_runner(qapp, wait_until):
    runner = TaskRunner("t", 2)
    got = []

    def bad_callback(_):
        raise RuntimeError("callback bug")

    runner.submit(lambda: 1, bad_callback)
    runner.submit(lambda: 2, got.append)
    assert wait_until(lambda: got)
    runner.shutdown()
