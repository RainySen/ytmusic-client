from PySide6.QtCore import QObject, Signal


# avisos toast
class Notifier(QObject):
    message = Signal(str, str)

    def info(self, text: str) -> None:
        self.message.emit("info", text)

    def warning(self, text: str) -> None:
        self.message.emit("warning", text)

    def error(self, text: str) -> None:
        self.message.emit("error", text)
