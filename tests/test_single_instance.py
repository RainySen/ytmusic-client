import os
import subprocess
import sys
import uuid

from core.single_instance import SingleInstance

CHILD = """
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, sys.argv[2])
from PySide6.QtWidgets import QApplication
app = QApplication([])
from core.single_instance import SingleInstance
print('claimed' if SingleInstance(sys.argv[1]).claim() else 'yielded', flush=True)
os._exit(0)
"""


def test_second_process_wakes_the_first_and_yields(qapp, wait_until):
    key = f"ytmusic-test-{uuid.uuid4().hex}"
    first = SingleInstance(key)
    woken = []
    first.activated.connect(lambda: woken.append(1))
    assert first.claim() is True
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    child = subprocess.Popen([sys.executable, "-c", CHILD, key, root], stdout=subprocess.PIPE, text=True)
    assert wait_until(lambda: woken and child.poll() is not None, timeout_ms=15000)
    assert child.stdout.read().strip() == "yielded"
    first.release()


def test_instance_can_be_claimed_again_after_release(qapp):
    key = f"ytmusic-test-{uuid.uuid4().hex}"
    first = SingleInstance(key)
    assert first.claim() is True
    first.release()
    again = SingleInstance(key)
    assert again.claim() is True
    again.release()


def test_each_key_is_independent(qapp):
    one, two = SingleInstance(f"ytmusic-a-{uuid.uuid4().hex}"), SingleInstance(f"ytmusic-b-{uuid.uuid4().hex}")
    assert one.claim() is True and two.claim() is True
    one.release()
    two.release()
