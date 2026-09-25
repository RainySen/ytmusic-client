from presenters.playlist_presenter import PlaylistPresenter
from services.collection_actions import CollectionActions
from services.notifier import Notifier
from ui.main_window import MainWindow


# acciones colecciones
class CollectionPresenter:
    def __init__(self, window: MainWindow, actions: CollectionActions, playlists: PlaylistPresenter,
                 notifier: Notifier):
        self._window = window
        self._actions = actions
        self._playlists = playlists
        self._notifier = notifier
        window.collection_action_requested.connect(self.on_action)

    def on_action(self, action: str, item: dict) -> None:
        if action == "playlist":
            self._actions.tracks_of(item, self._playlists.save_tracks)
        elif action == "share":
            self._window.copy_text(self._actions.share_url(item))
            self._notifier.info("Enlace copiado al portapapeles.")
        else:
            self._actions.perform(action, item)
