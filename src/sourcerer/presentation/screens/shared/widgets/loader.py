from itertools import cycle

from textual.app import RenderResult
from textual.widgets import Static


class Loader(Static):
    stops = cycle("⣷⣯⣟⡿⢿⣻⣽⣾")

    DEFAULT_CSS = """
    Loader {
        color: #9E53E0;
    }
    """

    def render(self) -> RenderResult:
        return next(self.stops)

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 10
