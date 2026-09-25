import json
import os

from infra.json_store import read_json, write_json_atomic
from infra.playlist_repository import LocalPlaylistRepository


def test_atomic_write_and_read(tmp_path):
    path = str(tmp_path / "x.json")
    assert write_json_atomic(path, {"a": [1, 2]})
    assert read_json(path) == {"a": [1, 2]}
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


def test_read_missing_and_corrupt(tmp_path):
    assert read_json(str(tmp_path / "nope.json"), "dflt") == "dflt"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert read_json(str(bad), []) == []


def test_write_failure_returns_false_and_cleans_up(tmp_path):
    path = str(tmp_path / "x.json")
    assert write_json_atomic(path, {"bad": object()}) is False
    assert os.listdir(tmp_path) == []


def test_playlist_ids_are_unique(tmp_path):
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    ids = {repo.add("t", [{"videoId": "v"}]) for _ in range(50)}
    assert len(ids) == 50 and None not in ids


def test_playlist_persistence_roundtrip(tmp_path):
    path = str(tmp_path / "p.json")
    repo = LocalPlaylistRepository(path)
    pid = repo.add("Mix", [{"videoId": "v"}], "user_created")
    reloaded = LocalPlaylistRepository(path)
    assert reloaded.get(pid)["title"] == "Mix"
    assert reloaded.get(pid)["track_count"] == 1


def test_playlist_rename_and_delete(tmp_path):
    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    pid = repo.add("A", [])
    assert repo.rename(pid, "B") and repo.get(pid)["title"] == "B"
    assert repo.delete(pid) and repo.get(pid) is None
    assert repo.delete(pid) is False


def test_loads_legacy_file_with_old_style_ids(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps([{"playlistId": "local_1700000000000", "title": "Old", "tracks": []}]))
    repo = LocalPlaylistRepository(str(path))
    assert repo.get("local_1700000000000")["title"] == "Old"


def test_session_save_is_a_noop_until_restored(qapp, tmp_path):
    from domain.play_queue import PlayQueue
    from domain.stream_cache import StreamCache
    from infra.concurrency import TaskRunner
    from services.session_service import SessionService
    from services.stream_service import StreamService

    path = tmp_path / "session.json"
    path.write_text(json.dumps({"queue": [{"videoId": "keep"}], "current_index": 0}))
    queue = PlayQueue()
    streams = StreamService(object(), StreamCache(), TaskRunner("a", 1), TaskRunner("b", 1))
    session = SessionService(str(path), queue, streams)

    session.save()
    assert json.loads(path.read_text())["queue"][0]["videoId"] == "keep"

    session.restore()
    queue.append({"videoId": "new"})
    session.save()
    assert [s["videoId"] for s in json.loads(path.read_text())["queue"]] == ["keep", "new"]


def test_session_restores_old_format_files(qapp, tmp_path):
    from domain.play_queue import PlayQueue
    from domain.stream_cache import StreamCache
    from infra.concurrency import TaskRunner
    from services.session_service import SessionService
    from services.stream_service import StreamService

    path = tmp_path / "session.json"
    path.write_text(json.dumps({
        "queue": [{"videoId": "a", "title": "A"}, {"videoId": "b", "title": "B"}],
        "current_index": 1,
        "stream_cache": {"a": {"url": "u", "title": "A", "timestamp": "2025-01-01T00:00:00"}},
    }))
    queue = PlayQueue()
    streams = StreamService(object(), StreamCache(), TaskRunner("a", 1), TaskRunner("b", 1))
    SessionService(str(path), queue, streams).restore()
    assert queue.current["videoId"] == "b" and len(queue) == 2


def test_add_tracks_appends_only_new_songs_and_persists(tmp_path):
    path = str(tmp_path / "p.json")
    repo = LocalPlaylistRepository(path)
    pid = repo.add("Mix", [{"videoId": "a"}], "user_created")
    assert repo.add_tracks(pid, [{"videoId": "a"}, {"videoId": "b"}, {"videoId": "b"}, {"title": "no id"}]) == 1
    assert repo.add_tracks(pid, [{"videoId": "b"}]) == 0
    assert repo.add_tracks("missing", [{"videoId": "z"}]) is None
    reloaded = LocalPlaylistRepository(path).get(pid)
    assert [t["videoId"] for t in reloaded["tracks"]] == ["a", "b"] and reloaded["track_count"] == 2


def test_add_tracks_rolls_back_when_the_write_fails(tmp_path, monkeypatch):
    import infra.playlist_repository as module

    repo = LocalPlaylistRepository(str(tmp_path / "p.json"))
    pid = repo.add("Mix", [{"videoId": "a"}])
    monkeypatch.setattr(module, "write_json_atomic", lambda *a, **k: False)
    assert repo.add_tracks(pid, [{"videoId": "b"}]) is None
    assert [t["videoId"] for t in repo.get(pid)["tracks"]] == ["a"] and repo.get(pid)["track_count"] == 1


def test_recent_playlists_are_newest_first_bounded_and_persisted(tmp_path):
    from infra.recent_playlists import RecentPlaylists

    path = str(tmp_path / "recent.json")
    recents = RecentPlaylists(path, limit=3)
    assert recents.ids() == []
    for pid in ("a", "b", "c", "a", "d"):
        recents.touch(pid)
    assert recents.ids() == ["d", "a", "c"]
    assert RecentPlaylists(path, limit=3).ids() == ["d", "a", "c"]
    (tmp_path / "recent.json").write_text("not json")
    assert RecentPlaylists(path).ids() == []
