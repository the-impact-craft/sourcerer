from itertools import cycle

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class Loader(Container):
    stops = cycle("⣷⣯⣟⡿⢿⣻⣽⣾")

    DEFAULT_CSS = """
    Loader {
        color: #9E53E0;
    }
    """

    def __init__(self, *args, **kwargs):
        self.label = Static(next(self.stops))
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield self.label

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 10

    def automatic_refresh(self):
        self.label.update(next(self.stops))
