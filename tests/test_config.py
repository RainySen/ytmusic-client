import os

from core.config import AppPaths


def test_everything_the_app_writes_lives_under_data(tmp_path):
    paths = AppPaths(str(tmp_path))
    data = os.path.join(str(tmp_path), "data")
    assert paths.data_dir == data
    for path in (paths.auth_file, paths.session_file, paths.playlists_file, paths.lyrics_settings_file,
                 paths.cache_dir, paths.thumbnail_cache_dir, paths.home_cache_file, paths.recent_playlists_file,
                 paths.ytdlp_cache_dir, paths.log_file):
        assert path.startswith(data + os.sep)


def test_detect_points_at_the_project_root():
    root = AppPaths.detect().base_dir
    assert os.path.exists(os.path.join(root, "app.py")) and os.path.isdir(os.path.join(root, "core"))


def test_ensure_dirs_creates_the_data_layout(tmp_path):
    paths = AppPaths(str(tmp_path))
    paths.ensure_dirs()
    assert os.path.isdir(paths.thumbnail_cache_dir) and os.path.isdir(paths.ytdlp_cache_dir)


def test_files_from_the_old_layout_move_into_data_once(tmp_path):
    (tmp_path / "oauth.json").write_text("old-session")
    (tmp_path / "local_playlists.json").write_text("[]")
    (tmp_path / "ytmusic-client.log").write_text("log")
    (tmp_path / "ytmusic-client.log.1").write_text("older log")
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "home.json").write_text("home")
    paths = AppPaths(str(tmp_path))
    paths.ensure_dirs()
    assert open(paths.auth_file).read() == "old-session" and open(paths.playlists_file).read() == "[]"
    assert open(paths.home_cache_file).read() == "home" and os.path.exists(paths.log_file + ".1")
    assert not (tmp_path / "oauth.json").exists() and not (tmp_path / "cache").exists()
    paths.ensure_dirs()
    assert open(paths.auth_file).read() == "old-session"


def test_migration_never_overwrites_newer_data(tmp_path):
    paths = AppPaths(str(tmp_path))
    os.makedirs(paths.data_dir)
    with open(paths.auth_file, "w") as fh:
        fh.write("new")
    (tmp_path / "oauth.json").write_text("old")
    paths.ensure_dirs()
    assert open(paths.auth_file).read() == "new" and (tmp_path / "oauth.json").exists()
