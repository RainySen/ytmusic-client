from infra.listen_again_pins import ListenAgainPins
from presenters.home_presenter import HomePresenter
from presenters.player_presenter import artist_id_of
from services.navigation import Navigator
from services.notifier import Notifier
from ui.components.track_actions import SongMenuHub


class SongMenuPresenter:
    def __init__(self, hub: SongMenuHub, navigator: Navigator, pins: ListenAgainPins, notifier: Notifier,
                 home: HomePresenter, auth=None):
        self._navigator = navigator
        self._pins = pins
        self._notifier = notifier
        self._home = home
        hub.is_pinned = lambda song: pins.is_pinned(song.get("videoId", ""))
        hub.artist_requested.connect(self.open_artist)
        hub.pin_toggled.connect(self.toggle_pin)
        if auth is not None:
            auth.logged_out.connect(self.clear_pins)

    # pins belong to the account user
    def clear_pins(self) -> None:
        self._pins.clear()
        self._home.refresh_pins()

    def open_artist(self, song: dict) -> None:
        artist_id = artist_id_of(song)
        if artist_id:
            self._navigator.artist_requested.emit(artist_id)
        else:
            self._notifier.warning("No se encontró el artista de esta canción.")

    def toggle_pin(self, song: dict) -> None:
        title = song.get("title", "")
        if self._pins.toggle(song):
            self._notifier.info(f"«{title}» fijada en Volver a escucharlo.")
        else:
            self._notifier.info(f"«{title}» ya no está fijada.")
        self._home.refresh_pins()
