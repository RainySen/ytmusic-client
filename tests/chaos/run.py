from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from tests.chaos.monkey import Monkey, drain
from tests.chaos.world import World


def run_seed(seed: int, steps: int, only: str = "", **world_options) -> dict[str, str]:
    tmp = tempfile.mkdtemp(prefix=f"chaos-{seed}-")
    world = World(tmp, seed, **world_options)
    try:
        world.start()
        monkey = Monkey(world, seed, only=only)
        monkey.run(steps)
        stats = dict(plays=len(world.services.audio.urls), queue=len(world.services.queue), actions=monkey.counts)
        print('  stats', stats, flush=True)
        drain(world)
    except Exception as exc:
        import traceback
        world.recorder.report("run exception", "".join(traceback.format_exception(exc)))
    finally:
        problems = dict(world.recorder.problems)
        world.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--first", type=int, default=1)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--failure", type=float, default=0.08)
    parser.add_argument("--mutation", type=float, default=0.06)
    parser.add_argument("--anonymous", action="store_true")
    parser.add_argument("--only", default="")
    parser.add_argument("--wild", action="store_true")
    parser.add_argument("--latency", type=float, default=0.01)
    args = parser.parse_args()

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    seen: dict[str, str] = {}
    for seed in range(args.first, args.first + args.seeds):
        problems = run_seed(seed, args.steps, args.only, latency=args.latency, wild=args.wild, failure_rate=args.failure, mutation_rate=args.mutation,
                            authenticated=not args.anonymous)
        new = {k: v for k, v in problems.items() if k not in seen}
        seen.update(new)
        print(f"seed {seed}: {len(problems)} problems ({len(new)} new)", flush=True)
        for signature, detail in new.items():
            print(f"\n===== seed {seed} :: {signature}\n{detail}\n", flush=True)
    print(f"\n{len(seen)} distinct problems", flush=True)
    return 1 if seen else 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
