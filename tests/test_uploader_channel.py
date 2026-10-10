import pytest

from infra.concurrency import TaskRunner
from services.catalog_service import UPLOADER_SHOWN_VIDEOS, CatalogService

CHANNEL = "UCOTR1tcOAhjgi6YukrPpZxg"


def video(n):
    return {"title": f"cover {n}", "videoId": f"v{n}", "thumbnails": [], "views": "1M"}


class ChannelGateway:
    def __init__(self):
        self.video_calls = []

    def get_artist(self, browse_id):
        raise KeyError("musicImmersiveHeaderRenderer")

    def get_user(self, channel_id):
        return {"name": "まふまふちゃんねる",
                "videos": {"results": [video(n) for n in range(10)], "params": "more"},
                "playlists": {"results": [{"title": "歌ってみた", "playlistId": "PL1", "thumbnails": []}]}}

    def get_user_videos(self, channel_id, params):
        self.video_calls.append((channel_id, params))
        return [video(n) for n in range(30)]


@pytest.fixture
def catalog(qapp):
    runner = TaskRunner("uploader", 1)
    gateway = ChannelGateway()
    yield CatalogService(gateway, runner), gateway
    runner.shutdown()


def test_plain_youtube_channels_load_as_a_channel_page_with_all_their_videos(catalog):
    service, gateway = catalog
    profile = service._build_artist_profile(CHANNEL)
    assert profile["uploader"] and profile["name"] == "まふまふちゃんねる"
    assert gateway.video_calls == [(CHANNEL, "more")]
    assert len(profile["top_songs"]) == UPLOADER_SHOWN_VIDEOS and len(profile["all_songs"]) == 30
    assert profile["all_songs"][0]["artists"] == [{"name": "まふまふちゃんねる", "id": CHANNEL}]
    assert [title for title, _ in profile["sections"]] == ["Playlists"]


def test_non_channel_ids_still_report_the_failure(catalog):
    service, _ = catalog
    with pytest.raises(KeyError):
        service._build_artist_profile("MPLAUCfoo")
