from __future__ import annotations

import random
from typing import Any

WEIRD_STRINGS = (
    "", " ", "   ", "a", "A" * 400, "palabra" * 700, "Ünïcödé Çañón", "日本語のタイトル", "한국어 제목", "مرحبا بالعالم",
    "\u202eRTL override", "zero\u200bwidth\u200bspace", "🎵🎶🔥 emoji 💿", "line1\nline2\r\nline3", "\ttabbed\t",
    "<b>html</b> & <script>alert(1)</script>", "%s %d {0} {name} %(x)s", "\x00null\x00byte", "'; DROP TABLE songs; --",
    "https://example.com/" + "x" * 300, "C:\\Users\\rainy\\Desktop\\con", "../../etc/passwd", "𝕌𝕟𝕚𝕔𝕠𝕕𝕖 𝔽𝕒𝕟𝕔𝕪", "1e309", "-1", "NaN",
)

WEIRD_VALUES: tuple[Any, ...] = (None, "", 0, -1, 10 ** 12, 3.14, True, False, [], {}, [None], [{}], {"x": 1}, "0:00", "abc")


class Factory:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self._counter = 0

    def _id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}{self._counter:06d}{self.rng.randrange(10 ** 4):04d}"

    def text(self, base: str = "Título") -> str:
        if self.rng.random() < 0.15:
            return self.rng.choice(WEIRD_STRINGS)
        return f"{base} {self.rng.randrange(1000)}"

    def thumbnails(self) -> list[dict]:
        if self.rng.random() < 0.1:
            return []
        size = self.rng.choice((60, 120, 226, 544))
        url = f"https://lh3.googleusercontent.com/{self._id('img')}=w{size}-h{size}-l90-rj"
        return [{"url": url, "width": size, "height": size}, {"url": url.replace(f"w{size}", "w60"), "width": 60, "height": 60}]

    def artists(self) -> list[dict]:
        count = self.rng.choice((0, 1, 1, 1, 2, 3))
        return [{"name": self.text("Artista"), "id": self._id("UC")} for _ in range(count)]

    def duration(self) -> dict:
        seconds = self.rng.choice((0, 5, 61, 185, 240, 3600, 7325))
        text = f"{seconds // 60}:{seconds % 60:02d}"
        return {"duration": text, "duration_seconds": seconds}

    def song(self) -> dict:
        return {"videoId": self._id("v"), "title": self.text("Canción"), "artists": self.artists(),
                "album": {"name": self.text("Álbum"), "id": self._id("MPREb_")} if self.rng.random() < 0.7 else None,
                "thumbnails": self.thumbnails(), "views": self.rng.choice(("1.2M views", "340 plays", None, "")),
                "resultType": "song", "category": None, **self.duration()}

    def video(self) -> dict:
        return {**self.song(), "resultType": "video", "views": self.rng.choice(("12M views", "5K", None))}

    def album_card(self) -> dict:
        return {"browseId": self._id("MPREb_"), "title": self.text("Disco"), "type": self.rng.choice(("Album", "Single", "EP", None)),
                "year": self.rng.choice(("2019", "2024", None, "")), "artists": self.artists(), "thumbnails": self.thumbnails(),
                "resultType": "album"}

    def playlist_card(self) -> dict:
        return {"playlistId": self._id("PL"), "browseId": "VL" + self._id("PL"), "title": self.text("Playlist"),
                "thumbnails": self.thumbnails(), "author": self.text("Autor"), "itemCount": str(self.rng.randrange(1, 90)),
                "resultType": "playlist"}

    def artist_card(self) -> dict:
        return {"browseId": self._id("UC"), "title": self.text("Artista"), "artist": self.text("Artista"),
                "subscribers": self.rng.choice(("1.2M", "340K", None, "")), "thumbnails": self.thumbnails(), "resultType": "artist"}

    def home_item(self) -> dict | None:
        kind = self.rng.choice(("song", "song", "playlist", "album", "artist", "none"))
        if kind == "none":
            return None
        if kind == "song":
            return self.song()
        if kind == "playlist":
            return self.playlist_card()
        if kind == "artist":
            return {"browseId": self._id("UC"), "title": self.text("Artista"), "subscribers": "1M", "thumbnails": self.thumbnails()}
        return {"browseId": self._id("MPREb_"), "title": self.text("Disco"), "thumbnails": self.thumbnails()}

    def home(self, sections: int | None = None) -> list[dict]:
        count = self.rng.randrange(0, 14) if sections is None else sections
        return [{"title": self.text("Sección"), "contents": [self.home_item() for _ in range(self.rng.randrange(0, 14))]}
                for _ in range(count)]

    def charts(self) -> dict:
        return {"artists": [self.artist_card() for _ in range(self.rng.randrange(0, 20))],
                "videos": [self.playlist_card() for _ in range(self.rng.randrange(0, 10))]}

    def explore(self) -> dict:
        return {"new_releases": [self.album_card() for _ in range(self.rng.randrange(0, 12))],
                "trending": {"items": [self.song() for _ in range(self.rng.randrange(0, 20))]},
                "moods_and_genres": [{"title": self.text("Mood"), "params": self._id("ggM")} for _ in range(self.rng.randrange(0, 20))],
                "new_videos": [self.video() for _ in range(self.rng.randrange(0, 12))]}

    def search(self) -> list[dict]:
        results = []
        for _ in range(self.rng.randrange(0, 30)):
            kind = self.rng.choice(("song", "song", "video", "album", "artist", "playlist"))
            item = {"song": self.song, "video": self.video, "album": self.album_card, "artist": self.artist_card,
                    "playlist": self.playlist_card}[kind]()
            item["category"] = self.rng.choice(("Top result", "Songs", "Albums", "Videos", None))
            results.append(item)
        return results

    def tracks(self, count: int | None = None) -> list[dict]:
        return [self.song() for _ in range(self.rng.randrange(0, 40) if count is None else count)]

    def watch(self) -> dict:
        return {"tracks": self.tracks(), "lyrics": self.rng.choice((None, self._id("MPLY")))
                if self.rng.random() < 0.7 else None, "related": self.rng.choice((None, self._id("MPTR")))}

    def playlist(self) -> dict:
        return {"id": self._id("PL"), "title": self.text("Playlist"), "tracks": self.tracks(),
                "author": self.rng.choice((None, {"name": self.text("Autor"), "id": self._id("UC")}, [{"name": "x", "id": "y"}], [])),
                "year": self.rng.choice((None, 2024, "2023")), "trackCount": self.rng.choice((None, 12, "12")),
                "duration": self.rng.choice((None, "1 hour", "")), "thumbnails": self.thumbnails(),
                "description": self.rng.choice((None, "", self.text("Descripción")))}

    def related(self) -> list[dict]:
        shelves = [{"title": "Songs", "contents": self.tracks(self.rng.randrange(0, 25))},
                   {"title": "Playlists", "contents": [self.playlist_card() for _ in range(self.rng.randrange(0, 8))]},
                   {"title": "Artists", "contents": [self.artist_card() for _ in range(self.rng.randrange(0, 8))]}]
        self.rng.shuffle(shelves)
        return shelves

    def artist(self) -> dict:
        def shelf(make):
            return {"results": [make() for _ in range(self.rng.randrange(0, 12))], "browseId": self._id("MP")}
        return {"name": self.text("Artista"), "subscribers": self.rng.choice(("1M", None)), "description": self.text("Bio"),
                "thumbnails": self.thumbnails(), "songs": shelf(self.song), "albums": shelf(self.album_card),
                "singles": shelf(self.album_card), "videos": shelf(self.video), "related": shelf(self.artist_card),
                "shuffleId": self.rng.choice((None, self._id("RDAO"))), "radioId": self.rng.choice((None, self._id("RDEM")))}

    def album(self) -> dict:
        return {"title": self.text("Disco"), "type": self.rng.choice(("Album", "Single", "EP", None)), "year": "2024",
                "artists": self.artists(), "thumbnails": self.thumbnails(), "trackCount": self.rng.choice((None, 9)),
                "duration": "35 min", "tracks": self.tracks(self.rng.randrange(0, 20)),
                "related_recommendations": [self.album_card() for _ in range(self.rng.randrange(0, 6))]}

    def lyrics(self) -> dict | None:
        if self.rng.random() < 0.3:
            return None
        if self.rng.random() < 0.5:
            return {"lyrics": "\n".join(self.text("Verso") for _ in range(self.rng.randrange(0, 60))), "source": "x"}
        return {"lines": [{"text": self.text("Verso"), "time": self.rng.choice((0, 1200, "0:12", None))}
                          for _ in range(self.rng.randrange(0, 60))]}

    def library_playlists(self) -> list[dict]:
        return [self.playlist_card() for _ in range(self.rng.randrange(0, 15))]

    def library_songs(self) -> list[dict]:
        return self.tracks(self.rng.randrange(0, 80))

    def library_artists(self) -> list[dict]:
        return [self.artist_card() for _ in range(self.rng.randrange(0, 20))]


def mutate(value: Any, rng: random.Random, rate: float = 0.06, depth: int = 0, wild: bool = False) -> Any:
    if depth > 8:
        return value
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            roll = rng.random()
            if roll < rate * 0.4:
                continue
            if roll < rate:
                result[key] = _replacement(item, rng, wild)
                continue
            result[key] = mutate(item, rng, rate, depth + 1, wild)
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            roll = rng.random()
            if roll < rate * 0.3:
                continue
            if roll < rate * 0.6:
                result.append(None if not wild else rng.choice(WEIRD_VALUES))
            result.append(mutate(item, rng, rate, depth + 1, wild))
        return result
    if isinstance(value, str) and rng.random() < rate:
        return rng.choice(WEIRD_STRINGS)
    return value


def _replacement(item: Any, rng: random.Random, wild: bool) -> Any:
    if wild:
        return rng.choice(WEIRD_VALUES) if rng.random() < 0.6 else rng.choice(WEIRD_STRINGS)
    if isinstance(item, str):
        return rng.choice((None, "", rng.choice(WEIRD_STRINGS)))
    if isinstance(item, list):
        return rng.choice((None, []))
    if isinstance(item, dict):
        return rng.choice((None, {}))
    return None
